from json import loads, JSONDecodeError
from re import findall
from typing import List

from jsonpath2 import Path
from lxml import etree
from requests import get

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger
from scripts.proxy import get_proxy


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://sneakerpolitics.com/collections/sneakers'
        self.interval: int = 1
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot.html)Mozilla/5.0 (compatible; ' \
                          'Pinterestbot/1.0; +https://www.pinterest.com/bot.html)Mozilla/5.0 (Linux; ' \
                          'Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                          'Chrome/41.0.2272.96 Mobile Safari/537.36 (compatible; Pinterestbot/1.0; ' \
                          '+https://www.pinterest.com/bot.html)'

    def index(self) -> IndexType:
        return api.IInterval(self.name, 3)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[-1],
                          self.name, 'https://sneakerpolitics.com' + element.get('href'), self.interval)
            for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': self.user_agent}, proxies=get_proxy()
            ).text).xpath(
                '//div[@class="four columns alpha thumbnail even" or @class="four columns omega thumbnail even"]/a')
            if 'yeezy' in element.get('href') or 'jordan' in element.get('href') or 'air' in element.get('href')
               or 'dunk' in element.get('href') or 'sacai' in element.get('href')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                get_content = get(target.data, headers={'user-agent': self.user_agent}, proxies=get_proxy()).text
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
        try:  # TODO return info, that target is sold out
            if content.xpath('//span[@class="sold_out"]')[0].text == 'Sold Out':
                return api.SSuccess(
                    self.name,
                    api.Result(
                        'Sold out',
                        target.data,
                        'tech',
                        '',
                        '',
                        (api.currencies['USD'], 1),
                        {},
                        tuple(),
                        (
                            ('StockX', 'https://stockx.com/search/sneakers?s='),
                            ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                        )
                    )
                )
        except IndexError:
            pass
        name = content.xpath('//meta[@property="og:title"]')[0].get('content')
        available_sizes = tuple(size.text.replace('c', '') for size in content.xpath('//select[@name="id"]/option'))
        if len(available_sizes) > 0:
            return api.SSuccess(
                self.name,
                api.Result(
                    name,
                    target.data,
                    'shopify-filtered',
                    content.xpath('//meta[@property="og:image"]')[0].get('content'),
                    '',
                    (
                        api.currencies['USD'],
                        float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content'))
                    ),
                    {'Site': 'Sneaker Politics'},
                    tuple(
                        (
                            str(size_data.current_value['public_title']).split('M')[-1] + ' US',
                            'https://sneakerpolitics.com/cart/' + str(size_data.current_value['id']) + ':1'
                        ) for size_data in sizes_data if
                        size_data.current_value['public_title'].split('M')[-1] in available_sizes
                    ),
                    (
                        ('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                        ('Cart', 'https://sneakerpolitics.com/cart'),
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
                    (api.currencies['USD'], 1),
                    {},
                    tuple(),
                    (('StockX', 'https://stockx.com/search/sneakers?s='),
                     ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
                )
            )
