from os import getenv

import telegram
import telegram.ext
import telegram.utils
from dotenv import load_dotenv

from core import __copyright__, __version__
from core import api
from core.api import SSuccess, SFail
from core.logger import Logger
from .constructor import build


# TODO: Check for None


class EventsExecutor(api.EventsExecutor):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        load_dotenv()
        request_kwargs = {}
        proxy = getenv('TELEGRAM_PROXY')
        if proxy:
            if proxy.split('://')[0] == 'https':
                request_kwargs['proxy_url'] = proxy
            elif proxy.split('://')[0] == 'socks5':
                request_kwargs['proxy_url'] = proxy
                if getenv('PROXY_USER') and getenv('PROXY_PASS'):
                    request_kwargs['urllib3_proxy_kwargs'] = {
                        'username': getenv('PROXY_USER'),
                        'password': getenv('PROXY_PASS')
                    }
            elif proxy.split('://')[0] == 'http':
                raise api.EventsExecutorError('HTTP proxy is not supported')
            else:
                raise api.EventsExecutorError('Unknown proxy')
        self.bot = telegram.ext.Updater(
            token=getenv('TELEGRAM_BOT_TOKEN'),
            request_kwargs=request_kwargs,
            use_context=True
        ).bot

    def e_monitor_turning_on(self) -> None:
        self.bot.send_message(
            getenv('TELEGRAM_CHAT_ID'),
            f'INFO\nServer turning on\nMonitor {__version__} ({__copyright__})',
            parse_mode='HTML'
        )

    def e_monitor_turned_on(self) -> None:
        self.bot.send_message(getenv('TELEGRAM_CHAT_ID'), 'INFO\nServer online', parse_mode='HTML')

    def e_monitor_turning_off(self) -> None:
        self.bot.send_message(getenv('TELEGRAM_CHAT_ID'), 'INFO\nServer turning off', parse_mode='HTML')

    def e_error(self, message: str, thread: str) -> None:
        self.bot.send_message(
            getenv('TELEGRAM_CHAT_ID'),
            f'<u><b>Alert [ERROR]</b></u>\n{message}\nThread: {thread}',
            parse_mode='HTML'
        )

    def e_fatal(self, e: Exception, thread: str) -> None:
        self.bot.send_message(
            getenv('TELEGRAM_CHAT_ID'),
            f'<u><b>Alert [FATAL]</b></u>\n{e.__class__.__name__}: {e.__str__()}\nThread: {thread}',
            parse_mode='HTML'
        )

    def e_success_status(self, status: SSuccess) -> None:
        if status.result.image:
            self.bot.send_photo(
                getenv('TELEGRAM_CHAT_ID'),
                status.result.image,
                build(status.result),
                parse_mode='HTML'
            )
        else:
            self.bot.send_message(getenv('TELEGRAM_CHAT_ID'), build(status.result), parse_mode='HTML')

    def e_fail_status(self, status: SFail) -> None:
        self.bot.send_message(
            getenv('TELEGRAM_CHAT_ID'),
            f'<b>Alert [WARN]</b>\n<u>Target Lost</u>\nMessage: {status.message}\nScript: {status.script}',
            parse_mode='HTML'
        )
