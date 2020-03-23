import queue
import time
import inspect
import os
import threading

import telegram
import telegram.ext
from dotenv import load_dotenv

from core import __copyright__, __version__
from core import api
from core import library
from core.api import SSuccess, SFail
from core.logger import Logger
from .constructor import build


# TODO: Check for None


class EventsExecutor(api.EventsExecutor):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)

        load_dotenv()
        request_kwargs = {}
        proxy = os.getenv('TELEGRAM_PROXY')
        if proxy:
            if proxy.split('://')[0] == 'https':
                request_kwargs['proxy_url'] = proxy
            elif proxy.split('://')[0] == 'socks5':
                request_kwargs['proxy_url'] = proxy
                if os.getenv('PROXY_USER') and os.getenv('PROXY_PASS'):
                    request_kwargs['urllib3_proxy_kwargs'] = {
                        'username': os.getenv('PROXY_USER'),
                        'password': os.getenv('PROXY_PASS')
                    }
            elif proxy.split('://')[0] == 'http':
                raise api.EventsExecutorError('HTTP proxy is not supported')
            else:
                raise api.EventsExecutorError('Unknown proxy')

        self.bot = telegram.ext.Updater(
            token=os.getenv('TELEGRAM_BOT_TOKEN'),
            request_kwargs=request_kwargs,
            use_context=True
        ).bot

        self.state = 1
        self.chat = os.getenv('TELEGRAM_CHAT_ID')
        self.messages = queue.PriorityQueue(2048)
        self.thread = threading.Thread(name='Telegram-Bot', target=self.loop, daemon=True)
        self.thread.start()
        self.log.info('Thread started')

    def loop(self):
        errors = 0
        while True:
            start: float = time.time()
            if self.state >= 1:
                try:
                    msg = self.messages.get_nowait().content
                    try:
                        msg()
                    except (telegram.error.TimedOut, telegram.error.NetworkError) as e:
                        if self.state == 2:
                            self.log.error(f'{e.__class__.__name__} ({e.__str__()}) while sending message'
                                           f' ({inspect.getsource(msg)})')
                            errors += 1
                        else:
                            self.log.error(f'{e.__class__.__name__} ({e.__str__()}) while sending message')
                        self.messages.put(library.PrioritizedItem(1, msg), timeout=16)
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
            time.sleep(.3 - delta if delta <= .3 else 0)

    def e_monitor_turning_on(self) -> None:
        self.messages.put(
            library.PrioritizedItem(
                5,
                lambda: self.bot.send_message(
                    self.chat,
                    f'INFO\nMonitor turning on\nMonitor {__version__} ({__copyright__})',
                    parse_mode='HTML',
                    timeout=16
                )
            )
        )

    def e_monitor_turned_on(self) -> None:
        self.messages.put(
            library.PrioritizedItem(
                5,
                lambda: self.bot.send_message(self.chat, 'INFO\nMonitor online', parse_mode='HTML', timeout=16)
            )
        )

    def e_monitor_turning_off(self) -> None:
        self.messages.put(
            library.PrioritizedItem(
                5,
                lambda: self.bot.send_message(self.chat, 'INFO\nMonitor turning off', parse_mode='HTML', timeout=16)
            )
        )

    def e_monitor_turned_off(self) -> None:
        if self.thread.is_alive():
            self.messages.put(
                library.PrioritizedItem(
                    5,
                    lambda: self.bot.send_message(self.chat, 'INFO\nMonitor offline', timeout=16)
                )
            )
            self.log.info(f'Waiting for messages ({self.messages.unfinished_tasks}) to sent')
            self.state = 2
            self.messages.join()
            self.log.info('All messages sent') if self.state == 2 else None
            self.state = 0
            self.thread.join()
        else:
            self.log.warn('Bot offline (due to raised exception)')

    def e_error(self, message: str, thread: str) -> None:
        self.messages.put(
            library.PrioritizedItem(
                4,
                lambda: self.bot.send_message(
                    self.chat,
                    f'<u><b>Alert [ERROR]</b></u>\n{message}\nThread: {thread}',
                    parse_mode='HTML',
                    timeout=16
                )
            )
        )

    def e_fatal(self, e: Exception, thread: str) -> None:
        self.messages.put(
            library.PrioritizedItem(
                3,
                lambda: self.bot.send_message(
                    self.chat,
                    f'<u><b>Alert [FATAL]</b></u>\n{e.__class__.__name__}: {e.__str__()}\nThread: {thread}',
                    parse_mode='HTML',
                    timeout=16
                )
            )
        )

    def e_success_status(self, status: SSuccess) -> None:
        if status.result.image:
            self.messages.put(
                library.PrioritizedItem(
                    10,
                    lambda: self.bot.send_photo(
                        self.chat,
                        status.result.image,
                        build(status.result) + f'\n*Source: {status.script}\n*Date: {library.get_time()} UTC',
                        parse_mode='HTML',
                        timeout=16
                    )
                )
            )
        else:
            self.messages.put(
                library.PrioritizedItem(
                    10,
                    lambda: self.bot.send_message(self.chat, build(status.result), parse_mode='HTML', timeout=16)
                )
            )

    def e_fail_status(self, status: SFail) -> None:
        self.messages.put(
            library.PrioritizedItem(
                5,
                lambda: self.bot.send_message(
                    self.chat,
                    f'<b>Alert [WARN]</b>\n<u>Target Lost</u>\nMessage: {status.message}\nScript: {status.script}',
                    parse_mode='HTML',
                    timeout=16
                )
            )
        )
