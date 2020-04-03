import json
import os
import queue
import threading
import time
from dataclasses import dataclass, field

import requests
import yaml

from core import __version__, __copyright__
from core import api
from core import codes
from core.api import SSuccess, SFail
from core.logger import Logger
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
        self.thread = threading.Thread(name='Telegram-Bot', target=self.loop, daemon=True)
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

    def e_monitor_turning_on(self) -> None:
        self.messages.put(
            Message(
                5,
                'tech',
                {'content': f'[INFO]\nMonitor turning on\nMonitor {__version__} ({__copyright__})'}
            )
        )

    def e_monitor_turned_on(self) -> None:
        self.messages.put(
            Message(
                5,
                'tech',
                {'content': '[INFO]\nMonitor online'}
            )
        )

    def e_monitor_turning_off(self) -> None:
        self.messages.put(
            Message(
                5,
                'tech',
                {'content': '[INFO]\nMonitor turning off'}
            )
        )

    def e_monitor_turned_off(self) -> None:
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
                {'content': f'__Alert__\n{code.format()}\nThread: {thread}'}
            )
        )

    def e_success_status(self, status: SSuccess) -> None:
        self.messages.put(
            Message(
                10,
                status.result.channel,
                {'embeds': [build(status.result)]}
            )
        )

    def e_fail_status(self, status: SFail) -> None:
        self.messages.put(
            Message(
                5,
                'tech',
                {
                    'content': f'_Alert [WARN]_\n__Target Lost__\n'
                               f'Message: {status.message}\nScript: {status.script}'
                }
            )
        )
