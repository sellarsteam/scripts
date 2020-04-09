from json import loads, JSONDecodeError
from typing import List

from jsonpath2 import Path
from requests import get
from scripts.proxy import get_proxy

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

    def index(self) -> IndexType:
        return api.IInterval(self.name, 10)


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
                available: bool = loads(get(f'https://www.yeezysupply.com/api/products/{target.name}/availability',
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
            sizes_json = Path.parse_str('$.variation_list.*').match(loads(
                      get(f'https://www.yeezysupply.com/api/products/{target.name}/availability',
            headers=headers, proxies=get_proxy()).text))
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
                    tuple(size.current_value['size'] + ' US' + ' [' + str(size.current_value['availability']) + ']' for size in sizes_json
                          if size.current_value['availability'] > 0),
                    ()
                )
            )
        else:
            return api.SWaiting(target)

if __name__ == '__main__':
    content: dict = loads(get('https://www.yeezysupply.com/api/products/FV6125/availability', headers=headers, proxies=get_proxy()).text)
    sizes_json = Path.parse_str('$.variation_list.*').match(loads(
        get(f'https://www.yeezysupply.com/api/products/FV6125/availability',
            headers=headers, proxies=get_proxy()).text))
    print(tuple(size.current_value['size'] + ' US' + ' [' + str(size.current_value['availability']) + ']' for size in sizes_json
                           if size.current_value['availability'] > 0))
