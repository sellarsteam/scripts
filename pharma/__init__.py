from json import loads, JSONDecodeError
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
        self.catalog: str = 'https://shop.pharmabergen.no/collections/new-arrivals/'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 3)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element[0].get('href').split('/')[4],
                          self.name, 'https://shop.pharmabergen.no' + element[0].get('href'), self.interval)
            for element in etree.HTML(get('https://shop.pharmabergen.no/collections/new-arrivals/',
                                          headers={'user-agent': generate_user_agent()}, proxies=get_proxy()
                                          ).text).xpath('//div[@class="product-info-inner"]')
            if element[0].xpath('span[@class]')[0].text in ['NIKE', 'JORDAN'] or 'yeezy' in element[0].get('href')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: etree.Element = etree.HTML(
                    get(target.data, headers={'user-agent': generate_user_agent()}, proxies=get_proxy()).text)
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
                                str(size_data.current_value['option1']) + ' EU',
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
