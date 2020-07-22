import json
import os
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Union

import requests
import yaml

from source import __version__, __copyright__
from source import api
from source import codes
from source.api import TEFail, IAnnounce, IRelease, IRestock
from source.logger import Logger
from .constructor import build


@dataclass(order=True)
class Message:
    priority: int = field(repr=False)
    channel: str = field(compare=False)
    content: dict = field(compare=False)
    tries: int = field(default=5, repr=False)

    def retry(self) -> bool:
        if self.tries == 0:
            return False
        else:
            self.tries -= 1
            return True


class EventsExecutor(api.EventsExecutor):
    headers = {'Content-Type': 'application/json'}

    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.active = False
        if os.path.isfile(os.path.dirname(os.path.realpath(__file__)) + '/secret.yaml'):
            raw = yaml.safe_load(open(os.path.dirname(os.path.realpath(__file__)) + '/secret.yaml'))
            if isinstance(raw, dict):
                if 'channels' in raw and isinstance(raw['channels'], dict):
                    self.channels = raw['channels']
                    self.active = True
                else:
                    self.log.error('secret.yaml must contain channels')
            else:
                self.log.error('secret.yaml must contain dict')
        else:
            self.log.error('secret.yaml doesn\'t exist')

        self.state = 1
        self.messages = queue.PriorityQueue(1024)
        self.thread = threading.Thread(name='Discord-Bot', target=self.loop, daemon=True)
        self.thread.start()
        self.log.info('Thread started')

    def loop(self):
        errors = 0
        while True:
            start: float = time.time()
            if self.state >= 1:
                try:
                    msg: Message = self.messages.get_nowait()
                    try:
                        if msg.retry():
                            if msg.channel in self.channels:
                                response = requests.post(
                                    self.channels[msg.channel],
                                    data=json.dumps(msg.content),
                                    headers=self.headers
                                )
                                if response.status_code == 400:
                                    self.log.error(f'Message lost: {response.text}')
                                    print(json.dumps(msg.content))
                                    print(msg.content)
                            else:
                                self.log.warn(f'Message channel doesn\'t exist: {msg.channel}')
                        else:
                            self.log.warn(f'Max retries reached for message: {msg}')
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
        self.messages.put(
            Message(
                5,
                'tech',
                {'content': f'[INFO]\nMonitor starting\nMonitor {__version__} ({__copyright__})'}
            )
        )

    def e_monitor_started(self) -> None:
        self.messages.put(
            Message(
                5,
                'tech',
                {'content': '[INFO]\nMonitor online'}
            )
        )

    def e_monitor_stopping(self) -> None:
        self.messages.put(
            Message(
                5,
                'tech',
                {'content': '[INFO]\nMonitor stopping'}
            )
        )

    def e_monitor_stopped(self) -> None:
        if self.thread.is_alive():
            self.messages.put(
                Message(
                    5,
                    'tech',
                    {'content': '[INFO]\nMonitor offline'}
                )
            )
            self.log.info(f'Waiting for messages ({self.messages.unfinished_tasks}) to sent')
            self.state = 2
            self.messages.join()
            self.log.info('All messages sent') if self.state == 2 else None
            self.state = 0
            self.thread.join()
        else:
            self.log.warn('Script offline (due to raised exception)')

    def e_alert(self, code: codes.Code, thread: str) -> None:
        self.messages.put(
            Message(
                3 if str(code.code)[0] == '5' else 4,
                'tech',
                {'content': f'__**Alert**__\n{code.format()}\nThread: {thread}'}
            )
        )

    def e_item_announced(self, item: IAnnounce) -> None:
        self.item(item)

    def e_item_released(self, item: IRelease) -> None:
        self.item(item)

    def e_item_restock(self, item: IRestock) -> None:
        self.item(item)

    def item(self, item: Union[IAnnounce, IRelease, IRestock]):
        self.messages.put(
            Message(
                10,
                item.channel,
                {'embeds': [build(item)], 'username': 'Sellars Bot'}
            )
        )

    def e_target_end_fail(self, target_end: TEFail) -> None:
        self.messages.put(
            Message(
                5,
                'tech',
                {
                    'content': f'__**Alert**__ [**WARN**]\n**Target Fail**\n\nScript: {target_end.target.script}\n'
                               f'\nDescription: ```{target_end.description}```'
                }
            )
        )
