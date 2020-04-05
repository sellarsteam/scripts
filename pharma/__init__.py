from json import loads, JSONDecodeError
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
        self.catalog: str = 'https://shop.pharmabergen.no/collections/new-arrivals/'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 10)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element[0].get('href').split('/')[4],
                          self.name, 'https://shop.pharmabergen.no' + element[0].get('href'), self.interval)
            for element in etree.HTML(get('https://shop.pharmabergen.no/collections/new-arrivals/',
                                          headers={'user-agent': generate_user_agent()}
                                          ).text).xpath('//div[@class="product-info-inner"]')
            if element[0].xpath('span[@class]')[0].text in ['NIKE', 'JORDAN'] or 'yeezy' in element[0].get('href')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                proxy = choice(proxies)
                content: etree.Element = etree.HTML(
                    get(target.data, headers={'user-agent': generate_user_agent()},
                        proxies={str(proxy.split(' ')[0]): str(proxy.split(' ')[1])}).text)
                if content.xpath('//input[@type="submit"]')[0].get('value').replace('\n', '') == 'Add to Cart':
                    available = True
                else:
                    return api.SWaiting(target)
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        except IndexError:
            return api.SWaiting(target)
        if available:
            try:
                sizes_data = Path.parse_str('$.variants.*').match(
                    loads(content.xpath('//form[@action="/cart/add"]')[0].get('data-product')))
                name = content.xpath('//meta[@property="og:title"]')[0].get('content')
                return api.SSuccess(
                    self.name,
                    api.Result(
                        name,
                        target.data,
                        'shopify-filtered',
                        content.xpath('//meta[@property="og:image:secure_url"]')[0].get('content'),
                        '',
                        (
                            api.currencies['NOK'],
                            float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content')
                                  .replace('.', '').replace(',', '.'))
                        ),
                        {},
                        tuple(
                            (
                                size_data.current_value['option1'],
                                'https://shop.pharmabergen.no/cart/' + str(size_data.current_value['id']) + ':1'
                            ) for size_data in sizes_data
                        ),
                        (
                            ('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                            ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                        )
                    )
                )
            except JSONDecodeError:
                return api.SFail(self.name, 'Exception JSONDecodeError')
        else:
            return api.SWaiting(target)
