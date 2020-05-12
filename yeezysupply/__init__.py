from json import loads, JSONDecodeError
from typing import List

from cfscrape import create_scraper
from jsonpath2 import Path

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger

headers = {
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/79.0.3945.130 Chrome/79.0.3945.130 Safari/537.36',
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
        self.interval: int = 5

    def index(self) -> IndexType:
        return api.IInterval(self.name, 30)

    def targets(self) -> List[TargetType]:
        try:
            data = [
                api.TInterval(
                    i.current_value['product_id'],
                    self.name,
                    'https://www.yeezysupply.com/api/products/' + i.current_value['product_id'],
                    self.interval
                )
                for i in Path.parse_str('$[*]').match(
                    loads(create_scraper().get(self.catalog, headers=headers).text)
                )
            ]
            return data
        except JSONDecodeError:
            return []

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                try:
                    availability_json = loads(
                        create_scraper().get(f'https://www.yeezysupply.com/api/products/{target.name}/availability',
                                             headers=headers).text)
                    available: bool = availability_json['availability_status'] == 'IN_STOCK'
                    version_json = 1
                    if availability_json['availability_status'] == 'PREVIEW':
                        return api.SWaiting(target)
                except JSONDecodeError:
                    availability_json = loads(create_scraper().get(
                        f'https://www.yeezysupply.com/hpl/content/availability-v2/yeezy-supply/US/{target.name}.json',
                        headers=headers).text)
                    available: bool = availability_json['availability'] == 'IN_STOCK'
                    version_json = 2
                    if availability_json['availability'] == 'PREVIEW':
                        return api.SWaiting(target)
                if not available:  # TODO Return soldout
                    return api.SSuccess(
                        self.name,
                        api.Result(
                            'yeezy',
                            'sold',
                            'tech',
                            '',
                            '',
                            (api.currencies['USD'], float(1)),
                            {'Site': 'Yeezy Supply'},
                            tuple(),
                            (
                                ('StockX',
                                 'https://stockx.com/search/sneakers?s='),
                                ('Cart', 'https://www.yeezysupply.com/cart'),
                                ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            )
                        )
                    )
                else:
                    available = True
                content: dict = loads(create_scraper().get(target.data, headers=headers).text)
            else:
                return api.SFail(self.name, 'Unknown target type')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')
        except KeyError:
            return api.SFail(self.name, 'Wrong scheme')
        if available:
            if version_json == 1:
                sizes_json = Path.parse_str('$.variation_list.*').match(availability_json)
                sizes = tuple(
                    size.current_value['size'] + ' US' + ' [' + str(size.current_value['availability']) + ']' for size
                    in sizes_json
                    if size.current_value['availability'] > 0)
            else:
                sizes_json = Path.parse_str('$.skus.*').match(availability_json)
                sizes = tuple(
                    size.current_value['displaySize'] + ' US' + ' [' + str(size.current_value['hypeAvailability']) + ']'
                    for size in sizes_json
                    if size.current_value['hypeAvailability'] > 0)
            return api.SSuccess(
                self.name,
                api.Result(
                    content['name'],
                    'https://www.yeezysupply.com/product/' + content['id'],
                    'yeezysupply',
                    content['view_list'][0]['image_url'],
                    content['meta_data']['description'],
                    (api.currencies['USD'], float(content['pricing_information']['standard_price'])),
                    {'Site': 'Yeezy Supply'},
                    sizes,
                    (
                        ('StockX', 'https://stockx.com/search/sneakers?s=' + content['name'].replace(' ', '%20')),
                        ('Cart', 'https://www.yeezysupply.com/cart'),
                        ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    )
                )
            )
        else:  # TODO Return soldout
            return api.SSuccess(
                self.name,
                api.Result(
                    'yeezy',
                    'sold',
                    'tech',
                    '',
                    '',
                    (api.currencies['USD'], float(1)),
                    {'Site': 'Yeezy Supply'},
                    tuple(),
                    (
                        ('StockX',
                         'https://stockx.com/search/sneakers?s='),
                        ('Cart', 'https://www.yeezysupply.com/cart'),
                        ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    )
                )
            )
