import queue
import threading
from dataclasses import dataclass, field
from time import time, sleep
from typing import List, Dict, Optional

import requests
import yaml
from source import __version__, __copyright__
from source import api
from source import codes
from source.logger import Logger
from source.tools import ScriptStorage
from ujson import dumps

currencies: tuple = ('', '£', '$', '€', '₽', '¥', 'kr', '₴', 'Br', 'zł', '$(HKD)', '$(CAD)', '$(AUD)')
sizes_column_size = 5


@dataclass
class Group:
    __slots__ = ['tag', 'short']
    tag: str
    short: bool

    def __post_init__(self):
        if not isinstance(self.tag, str):
            raise TypeError('tag must be str')
        if not isinstance(self.short, bool):
            raise TypeError('short must bool')


@dataclass
class Chat:
    __slots__ = ['id', 'group', 'short']
    id: int
    group: Group
    short: bool

    def __post_init__(self):
        if not isinstance(self.id, int):
            raise TypeError('id must be int')
        if not isinstance(self.group, Group):
            raise TypeError('group must be Group')
        if not isinstance(self.short, bool):
            raise TypeError('short must bool')


@dataclass(order=True)
class Message:
    priority: int
    text: str = field(default='', compare=False)
    channel: str = field(default='', compare=False)
    item: Optional[api.ItemType] = field(default=None, compare=False)
    tries: int = field(default=5, repr=False, compare=False)

    def __post_init__(self):
        if not self.channel:
            if self.item:
                self.channel = self.item.channel
            else:
                self.channel = 'tech'

    def retry(self) -> bool:
        if self.tries == 0:
            return False
        else:
            self.tries -= 1
            return True

    @property
    def image(self) -> bool:
        if self.item and self.item.image:
            return True
        else:
            return False

    def build(self, chat: Chat) -> str:
        if self.item:
            msg = [f'''<a href="{self.item.url}">{"[ANNOUNCE] " if isinstance(self.item, api.IAnnounce) else
            "[RESTOCK] " if isinstance(self.item, api.IRestock) else ""}{self.item.name}</a>''']

            if self.item.description:
                msg.append(self.item.description)
            if self.item.price.current:
                msg.extend([
                    '\n<b>Price</b>',
                    f'<s>{self.item.price.old}</s> {self.item.price.current}{currencies[self.item.price.currency]}'
                    if self.item.price.old else f'{self.item.price.current}{currencies[self.item.price.currency]}'
                ])
            if self.item.sizes:
                msg.append('\n<b>Sizes</b>')
                msg.extend([f'<a href="{i.url}">{i.size}</a>' for i in self.item.sizes])
            if self.item.fields and not chat.short:
                for k, v in self.item.fields.items():
                    msg.extend([f'\n<b>{k}</b>', v])
            if self.item.footer:
                msg.append('\n<b>Links</b>')
                msg.append(
                    ' | '.join((f'<a href="{i.url}">{i.text}</a>' if i.url else i.text for i in self.item.footer)))
            msg.append(f'<b><u>{chat.group.tag}</u></b>')
            return '\n'.join(msg)
        elif self.text:
            return self.text


class EventsExecutor(api.EventsExecutor):
    _token: str
    active: bool

    channels: Dict[str, List[Chat]]
    groups: Dict[str, Group]

    def __init__(self, name: str, log: Logger, storage: ScriptStorage):
        super().__init__(name, log, storage)
        self._token = ''
        self.active = False

        self.channels = {}
        self.groups = {}
        self.config()

        self.state = 1
        self.messages = queue.PriorityQueue(1024)
        self.thread = threading.Thread(name='Telegram-Bot', target=self.loop, daemon=True)
        self.thread.start()
        self.log.info('Thread started')

    def config(self):
        if self.storage.check('secret.yaml'):
            raw = yaml.safe_load(self.storage.file('secret.yaml'))
            if isinstance(raw, dict):
                if 'token' in raw and isinstance(raw['token'], str):
                    self._token = raw['token']
                if 'groups' in raw and isinstance(raw['groups'], dict):
                    if 'list' in raw['groups'] and isinstance(raw['groups']['list'], dict):
                        for k, v in raw['groups']['list'].items():
                            if 'tag' in v and isinstance(v['tag'], str):
                                self.groups[k] = Group(v['tag'], v['short'] if 'short' in v else False)
                            else:
                                self.log.error(f'group "{k}" has no tag. skipping...')
                    else:
                        raise IndexError('groups must contain list (as object)')

                    if 'default' in raw['groups'] and isinstance(raw['groups']['default'], str):
                        if raw['groups']['default'] in self.groups:
                            default_group = self.groups[raw['groups']['default']]
                        else:
                            raise ReferenceError('default group does not exist')
                    else:
                        raise IndexError('groups must contain default (as string)')
                else:
                    raise IndexError('secret.yaml must contain groups (as object)')

                if 'channels' in raw and isinstance(raw['channels'], dict):
                    if 'tech' in raw['channels']:
                        for k, v in raw['channels'].items():
                            if isinstance(v, list):
                                chats = []
                                for i in v:
                                    if isinstance(i, list) and 3 > len(i) > 0:
                                        chats.append(Chat(
                                            i[0],
                                            (group := self.groups[i[1]] if len(i) > 1 else default_group),
                                            i[2] if len(i) > 2 else group.short
                                        ))
                                    else:
                                        self.log.error(f'chat (channel "{k}") must contain (id[, group])')
                                self.channels[k] = chats
                            else:
                                self.log.error(f'channel "{k}" must be array of chats')
                        else:
                            del chats
                    else:
                        raise IndexError('channels must contain channel named "tech"')
                else:
                    raise IndexError('secret.yaml must contain channels (as object)')

                self.active = True
                del raw
            else:
                raise TypeError('secret.yaml must contain object')
        else:
            raise FileNotFoundError('secret.yaml not found')

    def wait(self, delta: float) -> None:
        if self.messages.qsize() > 5:
            est = ((self.messages.qsize() - 5) * 1)
        else:
            est = .1

        sleep(est - delta if delta <= est else 0)

    def loop(self):
        errors = 0
        while True:
            start: float = time()
            if self.state >= 1:
                try:
                    msg: Message = self.messages.get_nowait()
                    try:
                        if msg.retry():
                            if msg.channel not in self.channels:
                                self.log.warn(f'Message\'s channel does not exist: {msg.channel}')
                                continue

                            for i in self.channels[msg.channel]:
                                resp = requests.post(
                                    f'https://api.telegram.org/bot{self._token}/sendMessage',
                                    data=dumps({'chat_id': i.id, 'text': msg.build(i), 'parse_mode': 'HTML'}),
                                    headers={'Content-Type': 'application/json'}
                                )

                                if resp.status_code in (400, 429, 500):
                                    self.log.error(f'Message lost: {resp.text}\n'
                                                   f'------------\n{dumps(msg.build(i))}\n------------')
                                    continue
                        else:
                            self.log.error(f'Max retries reached for message: {msg}')
                    except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
                        if self.state == 2:
                            self.log.error(f'{e.__class__.__name__} ({e.__str__()}) while sending message: {msg}')
                            errors += 1
                        else:
                            self.log.error(f'{e.__class__.__name__} ({e.__str__()}) while sending message')
                        msg.priority = 1
                        self.messages.put_nowait(msg)
                    finally:
                        self.messages.task_done()
                except queue.Empty:
                    pass
                if errors >= 3:
                    self.log.warn('Max retries reached. Turning off')
                    self.messages.unfinished_tasks = 1
                    self.messages.task_done()
                    self.state = 0
            else:
                self.log.info('Thread closed')
                break
            self.wait(time() - start)

    def e_monitor_starting(self) -> None:
        self.messages.put(Message(
            1, f'INFO\nMonitor starting\nMonitor {__version__} ({__copyright__})'))

    def e_monitor_started(self) -> None:
        self.messages.put(Message(1, 'INFO\nMonitor online'))

    def e_monitor_stopping(self) -> None:
        self.messages.put(Message(1, 'INFO\nMonitor stopping'))

    def e_monitor_stopped(self) -> None:
        if self.thread.is_alive():
            self.messages.put(Message(1, 'INFO\nMonitor offline'))
            self.log.info(f'Waiting for messages ({self.messages.unfinished_tasks}) to sent')
            self.state = 2
            self.messages.join()
            self.log.info('All messages sent') if self.state == 2 else None
            self.state = 0
            self.thread.join()
        else:
            self.log.warn('Script offline (due to raised exception)')

    def e_alert(self, code: codes.Code, thread: str) -> None:
        self.messages.put(Message(3 if str(code.code)[0] == '5' else 4,
                                  f'<b><u>Alert</u></b>\n{code.format()}\nThread: {thread}'))

    def e_item(self, item: api.ItemType) -> None:
        self.messages.put(Message(10, item=item))

    def e_target_end(self, target_end: api.TargetEndType) -> None:
        if isinstance(target_end, api.TEFail):
            text = "Target Fail"
        elif isinstance(target_end, api.TESoldOut):
            text = "Target SoldOut"
        else:
            text = "Target Success"

        self.messages.put(Message(
            5,
            f'<u>[TargetEnd]</u>\n*{text}*\n'
            f'\nDescription: {target_end.description}\nScript: {target_end.target.script}'
        ))

    def e_message(self, msg: api.MessageType) -> None:
        if isinstance(msg, api.MAlert):
            header = '<b><u>Alert Message</u></b>'
        else:
            header = '<b>Information Message</b>'

        self.messages.put(Message(3 if isinstance(msg, api.MAlert) else 15,
                                  f'{header}\n{msg.text}\n<b>Script: <u>{msg.script}</u></b>', msg.channel))
