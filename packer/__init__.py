from json import loads, JSONDecodeError
from re import findall
from typing import List

from jsonpath2 import Path
from lxml import etree
from requests import get

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://packershoes.com/collections/new-arrivals/sneakers?page=1'
        self.interval: float = 1

    def index(self) -> IndexType:
        return api.IInterval(self.name, 1)

    def targets(self) -> List[TargetType]:
        return [
                   api.TInterval(element.get('href').split('/')[4],
                                 self.name, 'https://packershoes.com' + element.get('href'), self.interval)
                   for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': 'Pinterest/0.2 (+https://www.pinterest.com/bot'
                                       '.html)Mozilla/5.0 (compatible; '
                                       'Pinterestbot/1.0; '
                                       '+https://www.pinterest.com/bot.html)Mozilla/5'
                                       '.0 (Linux; Android 6.0.1; Nexus 5X '
                                       'Build/MMB29P) AppleWebKit/537.36 (KHTML, '
                                       'like Gecko) Chrome/41.0.2272.96 Mobile '
                                       'Safari/537.36 (compatible; Pinterestbot/1.0; '
                                       '+https://www.pinterest.com/bot.html)'}
            ).text).xpath('//a[@class="grid-product__meta"]')
                   if 'nike' in element.get('href').split('/')[4] or
                      'jordan' in element.get('href').split('/')[4] or
                      'yeezy' in element.get('href').split('/')[4] or
                      'force' in element.get('href').split('/')[4]
               ][0:5:]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                get_content = get(target.data, headers={'user-agent': 'Pinterest/0.2 (+https://www.pinterest.com/bot'
                                                                      '.html)Mozilla/5.0 (compatible; '
                                                                      'Pinterestbot/1.0; '
                                                                      '+https://www.pinterest.com/bot.html)Mozilla/5'
                                                                      '.0 (Linux; Android 6.0.1; Nexus 5X '
                                                                      'Build/MMB29P) AppleWebKit/537.36 (KHTML, '
                                                                      'like Gecko) Chrome/41.0.2272.96 Mobile '
                                                                      'Safari/537.36 (compatible; Pinterestbot/1.0; '
                                                                      '+https://www.pinterest.com/bot.html)'}).text
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
