from json import loads, JSONDecodeError
from re import findall
from typing import List

from jsonpath2 import Path
from lxml import etree
from requests import get
from user_agent import generate_user_agent
from random import choice

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger

proxies = ['http 46.48.170.175:8080',
           'http 62.33.207.196:3128',
           'http 95.156.125.190:41870',
           'http 81.5.103.14:8081',
           'http 195.182.152.238:38178',
           'http 217.174.184.234:8081',
           'http 62.33.207.201:80',
           'http 193.106.94.106:8080',
           'http 62.33.207.201:3128',
           'http 109.195.194.79:57657',
           'http 62.33.207.196:80']

class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://packershoes.com/collections/new-arrivals/sneakers?page=1'
        self.interval: float = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 20)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[4],
                          self.name, 'https://packershoes.com' + element.get('href'), self.interval)
            for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': self.user_agent}
            ).text).xpath('//a[@class="grid-product__meta"]')
            if 'nike' in element.get('href').split('/')[4] or
               'jordan' in element.get('href').split('/')[4] or
               'yeezy' in element.get('href').split('/')[4] or
               'force' in element.get('href').split('/')[4]
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                proxy = choice(proxies)
                get_content = get(target.data, headers={'user-agent': generate_user_agent()},
                                  proxies = {str(proxy.split(' ')[0]): str(proxy.split(' ')[1])}).text
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
