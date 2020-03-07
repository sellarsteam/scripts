from io import BytesIO
from os import getenv

import telegram
import telegram.utils
from dotenv import load_dotenv
from requests import get

from core import __copyright__, __version__
from core import api
from core.api import SSuccess, SFail
from .constructor import build


# TODO: Check for None


class EventsExecutor(api.EventsExecutor):
    def __init__(self):
        load_dotenv()
        if getenv('TELEGRAM_PROXY'):
            self.bot = telegram.Bot(
                getenv('TELEGRAM_BOT_TOKEN'),
                request=telegram.utils.request.Request(proxy_url=getenv('TELEGRAM_PROXY'))
            )
        else:
            self.bot = telegram.Bot(getenv('TELEGRAM_BOT_TOKEN'))

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
                BytesIO(get(status.result.image).content),
                build(status.result), parse_mode='HTML'
            )
        else:
            self.bot.send_message(getenv('TELEGRAM_CHAT_ID'), build(status.result), parse_mode='HTML')

    def e_fail_status(self, status: SFail) -> None:
        self.bot.send_message(
            getenv('TELEGRAM_CHAT_ID'),
            f'<b>Alert [WARN]</b>\n<u>Target Lost</u>\nMessage: {status.message}\nScript: {status.script}',
            parse_mode='HTML'
        )
