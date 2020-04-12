from json import loads, JSONDecodeError
from re import findall
from typing import List

from jsonpath2 import Path
from lxml import etree
from requests import get
from user_agent import generate_user_agent

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger
from scripts.proxy import get_proxy

class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://packershoes.com/collections/new-arrivals/sneakers?page=1'
        self.interval: float = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 3)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[4],
                          self.name, 'https://packershoes.com' + element.get('href'), self.interval)
            for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': self.user_agent}, proxies=get_proxy()
            ).text).xpath('//a[@class="grid-product__meta"]')
            if 'nike' in element.get('href').split('/')[4] or
               'jordan' in element.get('href').split('/')[4] or
               'yeezy' in element.get('href').split('/')[4] or
               'force' in element.get('href').split('/')[4]
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                get_content = get(target.data, headers={'user-agent': generate_user_agent()},
                                  proxies=get_proxy()).text
                content: etree.Element = etree.HTML(get_content)
            else:
                return api.SFail(self.name, 'Unknown target type')
            sizes_data = Path.parse_str('$.product.variants.*').match(
                loads(findall(r'var meta = {.*}', get_content)[0]
                      .replace('var meta = ', '')))
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')
        name = content.xpath('//meta[@property="og:title"]')[0].get('content')
        return api.SSuccess(
            self.name,
            api.Result(
                name,
                target.data,
                'shopify-filtered',
                content.xpath('//meta[@property="og:image"]')[0].get('content').split('?')[0],
                '',
                (
                    api.currencies['USD'],
                    float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content').replace(',', ''))
                ),
                {},
                tuple(
                    (
                        str(size_data.current_value['public_title']).split(' /')[0] + ' US',
                        'https://packershoes.com/cart/' + str(size_data.current_value['id']) + ':1'
                    ) for size_data in sizes_data
                ),
                (
                    ('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                    ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                )
            )
        )
