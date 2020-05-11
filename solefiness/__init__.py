from json import loads, JSONDecodeError
from re import findall
from typing import List

from jsonpath2 import Path
from lxml import etree
from requests import get

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


def return_sold_out(data):
    return api.SSuccess(
        'solefiness',
        api.Result(
            'Sold out',
            data,
            'tech',
            '',
            '',
            (api.currencies['USD'], 1),
            {},
            tuple(),
            (('StockX', 'https://stockx.com/search/sneakers?s='),
             ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
        )
    )


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.solefiness.com/collections/new-arrivals'
        self.interval: int = 1
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot.html)Mozilla/5.0 ' \
                          '(compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html)' \
                          'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 ' \
                          '(KHTML, like Gecko) Chrome/41.0.2272.96 Mobile Safari/537.36 (compatible; ' \
                          'Pinterestbot/1.0; +https://www.pinterest.com/bot.html)'

    def index(self) -> IndexType:
        return api.IInterval(self.name, 1)

    def targets(self) -> List[TargetType]:
        links = list()
        counter = 0
        for element in etree.HTML(get(self.catalog,
                                      headers={'user-agent': self.user_agent}).text) \
                .xpath('//div[@class="product-item-details"]/a'):
            if counter == 5:
                break
            if 'yeezy' in element.get('href') or 'air' in element.get('href') or 'sacai' in element.get('href') \
                    or 'dunk' in element.get('href') or 'retro' in element.get('href'):
                links.append(element.get('href'))
                counter += 1
        return [
            api.TInterval(element.split('/')[-1],
                          self.name, 'https://www.solefiness.com' + element, self.interval)
            for element in links
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                get_content = get(target.data, headers={'user-agent': self.user_agent}).text
                content: etree.Element = etree.HTML(get_content)
                if content.xpath('//link[@itemprop="availability"]')[0].get('href') == 'http://schema.org/InStock':
                    available = True
                else:
                    return return_sold_out(target.data)
                sizes_data = Path.parse_str('$.product.variants.*').match(
                    loads(findall(r'var meta = {.*}', get_content)[0]
                          .replace('var meta = ', '')))
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')
        except IndexError:
            return return_sold_out(target.data)
        if available:
            try:
                available_sizes = tuple(element.text.split(' ')[0]
                                        for element in content.xpath('//select[@id="productSelect"]/option')
                                        if element.get('disabled') is None)
                name = content.xpath('//meta[@property="og:title"]')[0].get('content')
                return api.SSuccess(
                    self.name,
                    api.Result(
                        name,
                        target.data,
                        'shopify-filtered',
                        content.xpath('//meta[@property="og:image"]')[0].get('content'),
                        '',
                        (
                            api.currencies['AUD'],
                            float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content'))
                        ),
                        {'Site': 'Sole Finess'},
                        tuple(
                            (
                                str(size_data.current_value['public_title'].split(' ')[-1]) + ' US',
                                'https://www.solefiness.com/cart/' + str(size_data.current_value['id']) + ':1'
                            ) for size_data in sizes_data if
                            size_data.current_value['public_title'].split(' ')[-1] in available_sizes
                        ),
                        (
                            ('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                            ('Cart', 'https://www.solefiness.com/cart'),
                            ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                        )
                    )
                )
            except JSONDecodeError:
                return api.SFail(self.name, 'Exception JSONDecodeError')
        else:
            return return_sold_out(target.data)
