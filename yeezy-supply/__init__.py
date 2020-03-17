from json import loads, JSONDecodeError
from typing import List

from jsonpath2 import Path
from lxml import etree
from getpass import  getpass
import time
import cfscrape
from requests.exceptions import ReadTimeout
from requests import get
from user_agent import generate_user_agent


from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.yeezysupply.com/api/yeezysupply/products/bloom'
        self.user_agent = generate_user_agent()
        self.interval: float = 1

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:
        while True:
            try:
                return [
                    api.TInterval(i.current_value['product_name'],
                    self.name,
                    'https://www.yeezysupply.com/api/products/' + i.current_value['product_id'],
                    self.interval)
                    for i in Path.parse_str('$[*]').match(
                        loads(get(self.catalog, headers={'user-agent': self.user_agent,
                                                         'referer': 'https://www.yeezysupply.com',
                                                         'connection': 'keep-alive',
                                                         'cache-control': 'max-age=0', 'upgrade-insecure-requests': '1',
                                                         'sec-fetch-dest': 'document',
                                                         'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                                                         'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate', 'sec-fetch-user': '?1',
                                                         'accept-language': 'en-US,en;q=0.9',
                                                         }, timeout=3).text)
                    )
                ]
            except ReadTimeout:
                pass

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                while True:
                    try:
                        sizes_json = Path.parse_str('$.variation_list[*]').match(loads(
                            get(f'https://www.yeezysupply.com/api/products/{target.data.split("/")[5]}/availability',
                                headers={'user-agent': self.user_agent,
                                         'referer': f'https://www.yeezysupply.com/product/{target.data.split("/")[5]}',
                                         'connection': 'keep-alive', 'cache-control': 'max-age=0',
                                         'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                                         'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                                         'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                                         'sec-fetch-user': '?1',
                                         'accept-language': 'en-US,en;q=0.9'}, timeout=3).text))
                        break
                    except ReadTimeout:
                        pass

                available: bool = False
                while True:
                    try:
                        content: dict = loads(
                            get(
                                target.data,
                                headers={'user-agent': generate_user_agent(),
                                         'referer': 'https://www.yeezysupply.com',
                                         'connection': 'keep-alive', 'cache-control': 'max-age=0',
                                         'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                                         'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                                         'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                                         'sec-fetch-user': '?1',
                                         'accept-language': 'en-US,en;q=0.9'
                                         }, timeout=3
                            ).text
                        )
                        break
                    except ReadTimeout:
                        pass
                if tuple(size.current_value for size in sizes_json) != ():
                    available = True
            else:
                return api.SFail(self.name, 'Unknown target type')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')
        except KeyError:
            return api.SFail(self.name, 'Wrong scheme')
        if available:
            return api.SSuccess(
                self.name,
                api.Result(
                    content['name'],
                    'https://www.yeezysupply.com/product/' + content['id'],
                    'yeezy-supply',
                    content['view_list'][0]['image_url'],
                    content['meta_data']['description'],
                    (api.currencies['dollar'], float(content['pricing_information']['standard_price'])),
                    {},
                    tuple(size.current_value['size'] for size in sizes_json),
                    ()
                )
            )
        else:
            return api.SWaiting(target)