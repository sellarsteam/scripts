from json import loads, JSONDecodeError
from typing import List

from jsonpath2 import Path
from requests import get
from scripts.proxy import get_proxy
from cfscrape import create_scraper

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger

headers = {
    'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
    'referer': 'https://www.yeezysupply.com',
    'accept-encoding': 'gzip, deflate, br',
    'connection': 'keep-alive',
    'host': 'www.yeezysupply.com',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.5',
}


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.yeezysupply.com/api/yeezysupply/products/bloom'
        self.interval: int = 1
        self.scraper = create_scraper()

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
                loads(get(self.catalog, headers=headers, proxies=get_proxy()).text)
            )
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                try:
                    available: bool = loads(self.scraper.get(f'https://www.yeezysupply.com/hpl/content/availability-v2/yeezy-supply/US/{target.name}.json',
                                            headers=headers, proxies=get_proxy()).text)['availability'] == 'IN_STOCK'
                except JSONDecodeError:
                    available: bool = loads(self.scraper.get(f'https://www.yeezysupply.com/api/products/{target.name}/availability',
                                            headers=headers, proxies=get_proxy()).text)['availability_status'] == 'IN_STOCK'
                    
                if available == False:
                    return api.SWaiting(target)
                else:
                    available = True
                content: dict = loads(get(target.data, headers=headers, proxies=get_proxy()).text)
            else:
                return api.SFail(self.name, 'Unknown target type')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')
        except KeyError:
            return api.SFail(self.name, 'Wrong scheme')
        if available:
            try:
                sizes_json = Path.parse_str('$.skus.*').match(loads(
                          self.scraper.get(f'https://www.yeezysupply.com/hpl/content/availability-v2/yeezy-supply/US/{target.name}.json',
                headers=headers, proxies=get_proxy()).text))
                sizes = tuple(size.current_value['displaySize'] + ' US' + ' [' + str(size.current_value['hypeAvailability']) + ']' for size in sizes_json
                         if size.current_value['hypeAvailability'] > 0)
            except JSONDecodeError:
                sizes_json = Path.parse_str('$.skus.*').match(loads(
                          self.scraper.get(f'https://www.yeezysupply.com/api/products/{target.name}/availability',
                            headers=headers, proxies=get_proxy()).text))
                sizes = tuple(size.current_value['size'] + ' US' + ' [' + str(size.current_value['availability']) + ']' for size in sizes_json
                         if size.current_value['availability'] > 0)
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
                    sizes,
                    (
                        ('StockX', 'https://stockx.com/search/sneakers?s=' + content['name'].replace(' ', '%20')),
                        ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    )
                )
            )
        else:
            return api.SWaiting(target)

