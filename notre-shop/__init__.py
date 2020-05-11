from typing import List

from lxml import etree
from requests import get
from re import findall
from jsonpath2 import Path
from json import loads, JSONDecodeError

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.notre-shop.com/collections/footwear/mens?page=1&sort_by=created-descending'
        self.interval: int = 1
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot.html)Mozilla/5.0 (compatible; ' \
                          'Pinterestbot/1.0; +https://www.pinterest.com/bot.html)Mozilla/5.0 (Linux; Android ' \
                          '6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                          'Chrome/41.0.2272.96 Mobile Safari/537.36 (compatible; ' \
                          'Pinterestbot/1.0; +https://www.pinterest.com/bot.html)'

    def index(self) -> IndexType:
        return api.IInterval(self.name, 3)

    def targets(self) -> List[TargetType]:
        links = list()
        counter = 0
        for element in etree.HTML(get(self.catalog,
                                      headers={'user-agent': self.user_agent}).text) \
                .xpath('//a[@class="collection__product-block"]'):
            if counter == 5:
                break
            if 'yeezy' in element.get('href') or 'air' in element.get('href') or 'dunk' in element.get('href') \
                    or 'dunk' in element.get('href') or 'retro' in element.get('href') \
                    or 'blazer' in element.get('href'):
                links.append(element.get('href'))
            counter += 1
        return [
            api.TInterval(element.split('/')[-1],
                          self.name, 'https://www.notre-shop.com' + element, self.interval)
            for element in links
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                get_content = get(target.data, headers={'user-agent': self.user_agent}).text
                content: etree.Element = etree.HTML(get_content)
                available_sizes = list(size.text.replace('\n', '').replace(' ', '')
                                       for size in content.xpath('//div[@class="product__sizes "]/div')
                                       if 'sold' not in size.get('class'))
                sizes = tuple(
                    (
                        str(size_data.current_value['public_title'].split(' ')[0]) + ' US',
                        'https://www.notre-shop.com/cart/' + str(size_data.current_value['id']) + ':1'
                    ) for size_data in Path.parse_str('$.product.variants.*').match(
                        loads(findall(r'var meta = {.*}', get_content)[0]
                              .replace('var meta = ', '')))
                    if size_data.current_value['public_title'].split(' ')[0] in available_sizes
                )
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')
        if len(available_sizes) > 0:
            name = content.xpath('//meta[@property="og:title"]')[0].get('content')
            return api.SSuccess(
                self.name,
                api.Result(
                    name,
                    target.data,
                    'shopify-filtered',
                    'http:' + content.xpath('//meta[@itemprop="image"]')[0].get('content'),
                    '',
                    (
                        api.currencies['USD'],
                        float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content'))
                    ),
                    {'Site': 'Notre Shop'},
                    sizes,
                    (
                        ('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                        ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    )
                )
            )
        else:  # TODO return info, that target is sold out
            return api.SSuccess(
                self.name,
                api.Result(
                    'Sold out',
                    target.data,
                    'tech',
                    '',
                    '',
                    (api.currencies['USD'],
                     float(1)),
                    {},
                    tuple(),
                    (('StockX', 'https://stockx.com/search/sneakers?s='),
                     ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
                )
            )