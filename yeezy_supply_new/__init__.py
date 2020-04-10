from json import loads, JSONDecodeError
from typing import List

from jsonpath2 import Path
from requests import get
from scripts.proxy import get_proxy

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger

headers_for_catalog = {
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/79.0.3945.130 Chrome/79.0.3945.130 Safari/537.36',
    'upgrade-insecure-requests': '1',
    'sec-fetch-user': '?1',
    'sec-fetch-site': 'none',
    'sec-fetch-mode': 'navigate',
    'accept-encoding': 'gzip, deflate, br',
    'connection': 'keep-alive',
    'host': 'www.yeezysupply.com',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'scheme': 'https',
    'path': '/api/yeezysupply/products/bloom',
    'method': 'GET',
    'authority': 'www.yeezysupply.com',
    'accept-language': 'en-US,en;q=0.5',
    'cache-control': 'max-age=0',
    }

headers_for_content = {
    'authority': 'www.yeezysupply.com',
    'method': 'GET',
    'path': '/api/products/H67799',
    'scheme': 'https',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-user': '?1',
    'sec-fetch-site': 'none',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/79.0.3945.130 Chrome/79.0.3945.130 Safari/537.36',
    'accept-encoding': 'gzip, deflate, br',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'content-type': 'application/json',
    'accept-language': 'en-US,en;q=0.9',
    'referer': 'https://www.yeezysupply.com/product/H67799',
    }


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.yeezysupply.com/api/yeezysupply/products/bloom'
        self.interval: int = 1

    def index(self) -> IndexType:
        return api.IInterval(self.name, 5)


    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(
                i.current_value['product_id'],
                self.name,
                'https://www.yeezysupply.com/api/products/' + i.current_value['product_id'],
                self.interval
            )
            for i in Path.parse_str('$[*]').match(
                loads(get(self.catalog, headers=headers_for_catalog, proxies=get_proxy()).text)
            )
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                content: dict = loads(get(target.data, headers=headers_for_content, proxies=get_proxy()).text)
                available = content['attribute_list']['badge_text'] == 'Coming Soon'
                if available == False:
                    return api.SWaiting(target)
                else:
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
                    'yeezysupply',
                    content['view_list'][0]['image_url'],
                    content['meta_data']['description'],
                    (api.currencies['USD'], float(content['pricing_information']['standard_price'])),
                    {},
                    tuple(),
                    ()
                )
            )
        else:
            return api.SWaiting(target)

