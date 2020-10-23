import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Tuple, Optional

import requests
import yaml
from pytz import timezone
from ujson import dumps

from source import __version__, __copyright__
from source import api
from source import codes
from source.logger import Logger
from source.tools import ScriptStorage

currencies: tuple = ('', '£', '$', '€', '₽', '¥', 'kr', '₴', 'Br', 'zł', '$(HKD)', '$(CAD)', '$(AUD)')
sizes_column_size = 5


@dataclass
class Group:
    __slots__ = ['tag', 'bot', 'image', 'colors']
    tag: str
    bot: str
    image: str
    colors: Tuple[int, int, int]

    def __post_init__(self):
        if not isinstance(self.tag, str):
            raise TypeError('tag must be str')
        if not isinstance(self.bot, str):
            raise TypeError('bot must be str')
        if not isinstance(self.image, str):
            raise TypeError('image must be str')
        if isinstance(self.colors, tuple):
            if len(self.colors) != 3:
                raise ValueError('colors must contain 3 colors')
        else:
            raise TypeError('colors must be tuple')


@dataclass
class Hook:
    __slots__ = ['id', 'key', 'group']
    id: int
    key: str
    group: Group

    def __post_init__(self):
        if not isinstance(self.id, int):
            raise TypeError('id must be int')
        if not isinstance(self.key, str):
            raise TypeError('key must be str')
        if not isinstance(self.group, Group):
            raise TypeError('group must be Group')

    def build(self) -> str:
        return f'https://discord.com/api/webhooks/{self.id}/{self.key}'


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

    def build(self, group: Group) -> dict:
        result: dict = {'content': self.text} if self.text else {}

        if group.bot:
            result['username'] = group.bot

        if self.item:
            embed = {
                'footer': {'text': group.tag},
                'title': ('[ANNOUNCE] ' if isinstance(self.item, api.IAnnounce) else
                          '[RESTOCK] ' if isinstance(self.item, api.IRestock) else '') + self.item.name,
                'color': (int(group.colors[0]) if isinstance(self.item, api.IRelease) else
                          int(group.colors[2]) if isinstance(self.item, api.IRestock) else int(group.colors[1])),
                'timestamp': datetime.utcnow().replace(tzinfo=timezone('Europe/Moscow')).strftime(
                    '%Y-%m-%dT%H:%M:%S.%fZ'),
                'fields': [],
                'url': self.item.url
            }

            if group.image:
                embed['footer']['icon_url'] = group.image

            if self.item.description:
                embed['description'] = self.item.description
            if self.item.image:
                embed['thumbnail'] = {'url': self.item.image}
            if self.item.price.current:
                embed['fields'].append({
                    'name': 'Price',
                    'value': f'~~{self.item.price.old}~~ '
                             f'{self.item.price.current}{currencies[self.item.price.currency]}'
                    if self.item.price.old else f'{self.item.price.current}{currencies[self.item.price.currency]}'
                })
            if self.item.fields:
                for k, v in self.item.fields.items():
                    embed['fields'].append({
                        'name': k,
                        'value': v
                    })
            if self.item.sizes:
                columns: List[str] = []
                for i, v in enumerate(self.item.sizes):
                    if len(columns) < (i // sizes_column_size) + 1:
                        columns.append('')
                    if v.url:
                        columns[i // sizes_column_size] += f'[{v.size}]({v.url})\n'
                    else:
                        columns[i // sizes_column_size] += f'{v.size}\n'

                embed['fields'].append({
                    'name': 'Sizes',
                    'value': columns[0],
                    'inline': True
                })

                for i in columns[1:]:
                    embed['fields'].append({
                        'name': '\u200e',
                        'value': i,
                        'inline': True
                    })
            if self.item.footer:
                embed['fields'].append({
                    'name': 'Links',
                    'value': ' | '.join((f'[{i.text}]({i.url})' if i.url else i.text for i in self.item.footer))
                })

            result['embeds'] = [embed]
        return result


class EventsExecutor(api.EventsExecutor):
    active: bool

    channels: Dict[str, List[Hook]]
    groups: Dict[str, Group]

    def __init__(self, name: str, log: Logger, storage: ScriptStorage):
        super().__init__(name, log, storage)
        self.active = False

        self.channels = {}
        self.groups = {}
        self.config()

        self.state = 1
        self.messages = queue.PriorityQueue(1024)
        self.thread = threading.Thread(name='Discord-Bot', target=self.loop, daemon=True)
        self.thread.start()
        self.log.info('Thread started')

    def config(self):
        if self.storage.check('secret.yaml'):
            raw = yaml.safe_load(self.storage.file('secret.yaml'))
            if isinstance(raw, dict):
                if 'groups' in raw and isinstance(raw['groups'], dict):
                    if 'list' in raw['groups'] and isinstance(raw['groups']['list'], dict):
                        for k, v in raw['groups']['list'].items():
                            if 'tag' in v and isinstance(v['tag'], str):
                                self.groups[k] = Group(
                                    v['tag'],
                                    v['bot'] if 'bot' in v and isinstance(v['bot'], str) else '',
                                    v['image'] if 'image' in v and isinstance(v['image'], str) else '',
                                    tuple(v['colors']) if 'colors' in v and isinstance(v['colors'], list) and
                                                          len(v['colors']) == 3 else (0, 0, 0)
                                )
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
                            hooks = []
                            if isinstance(v, list):
                                for i in v:
                                    if isinstance(i, list) and 4 > len(i) > 1:
                                        hooks.append(
                                            Hook(i[0], i[1], self.groups[i[2]] if len(i) > 2 else default_group))
                                    else:
                                        self.log.error(f'hook (channel "{k}") must contain (id, key[, group])')
                            self.channels[k] = hooks
                        else:
                            del hooks
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

    def loop(self):
        errors = 0
        while True:
            start: float = time.time()
            if self.state >= 1:
                try:
                    msg: Message = self.messages.get_nowait()
                    try:
                        if msg.retry():
                            if msg.channel not in self.channels:
                                self.log.warn(f'Message\'s channel does not exist: {msg.channel}')
                                continue

                            for i in self.channels[msg.channel]:
                                response = requests.post(
                                    i.build(),
                                    data=dumps(msg.build(i.group)),
                                    headers={'Content-Type': 'application/json'}
                                )

                                if response.status_code == 400:
                                    self.log.error(f'Message lost: {response.text}\n\n '
                                                   f'{dumps(msg.build(i.group))}\n------------')
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
            delta: float = time.time() - start
            time.sleep(.1 - delta if delta <= .1 else 0)

    def e_monitor_starting(self) -> None:
        self.messages.put(Message(1, f'[INFO]\nMonitor starting\nMonitor {__version__} ({__copyright__})'))

    def e_monitor_started(self) -> None:
        self.messages.put(Message(1, '[INFO]\nMonitor online'))

    def e_monitor_stopping(self) -> None:
        self.messages.put(Message(1, '[INFO]\nMonitor stopping'))

    def e_monitor_stopped(self) -> None:
        if self.thread.is_alive():
            self.messages.put(Message(1, '[INFO]\nMonitor offline'))
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
                                  f'__**Alert**__\n{code.format()}\nThread: {thread}'))

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
            f'__[TargetEnd]__\n**{text}**\n'
            f'\nDescription: {target_end.description}\nScript: {target_end.target.script}'
        ))

    def e_message(self, msg: api.MessageType) -> None:
        if isinstance(msg, api.MAlert):
            header = '__**Alert Message**__'
        else:
            header = '**Information Message*'

        self.messages.put(Message(3 if isinstance(msg, api.MAlert) else 15,
                                  f'{header}\n{msg.text}\n**Script: __{msg.script}__**', msg.channel))
