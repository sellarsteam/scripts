from json import loads, JSONDecodeError
from re import findall
from typing import List

from jsonpath2 import Path
from lxml import etree
from requests import get
from user_agent import generate_user_agent
from random import choice
from scripts.proxy import get_proxy

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger

class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://extrabutterny.com/collections/footwear/Mens'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 2)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element[0].get('href').split('/')[4],
                          self.name, 'https://extrabutterny.com' + element[0].get('href'), self.interval)
            for element in etree.HTML(get(self.catalog,
                                          headers={'user-agent': generate_user_agent()}
                                          ).text).xpath('//div[@class="GridItem-imageContainer"]')
            if
            'nike' in element[0].get('href') or 'jordan' in element[0].get('href') or 'yeezy' in element[0].get('href')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                get_content = get(target.data, headers={'user-agent': generate_user_agent()},
                                  proxies = get_proxy()).text
                content: etree.Element = etree.HTML(get_content)
                if content.xpath('//strong')[0].text.replace(' ', '').replace('\t', '').replace('\n', '') != 'SoldOut':
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
                sizes_data = Path.parse_str('$.product.variants.*').match(
                    loads(findall(r'var meta = {.*}', get_content)[0]
                          .replace('var meta = ', '')))
                name = content.xpath('//title')[0].text.split(' [')[0]
                return api.SSuccess(
                    self.name,
                    api.Result(
                        name,
                        target.data,
                        'shopify-filtered',
                        content.xpath('//meta[@property="og:image:secure_url"]')[0].get('content'),
                        '',
                        (
                            api.currencies['USD'],
                            float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content'))
                        ),
                        {},
                        tuple(
                            (
                                str(size_data.current_value['public_title']) + ' US',
                                'https://extrabutterny.com/cart/' + str(size_data.current_value['id']) + ':1'
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
