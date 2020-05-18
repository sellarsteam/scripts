from json import loads, JSONDecodeError
from re import findall
from typing import List

from jsonpath2 import Path
from lxml import etree
from requests import get

from source import api
from source.api import IndexType, TargetType, StatusType
from source.logger import Logger
from scripts.proxy import get_proxy


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://kith.com/collections/mens-footwear'
        self.interval: float = 1
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot.html)Mozilla/5.0 ' \
                          '(compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html)' \
                          'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 ' \
                          '(KHTML, like Gecko) Chrome/41.0.2272.96 Mobile Safari/537.36 ' \
                          '(compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html)'

    def index(self) -> IndexType:
        return api.IInterval(self.name, 3)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.xpath('a')[0].get('href').split('/')[2],
                          self.name, 'https://kith.com/' + element.xpath('a')[0].get('href'), self.interval)
            for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': self.user_agent}, proxies=get_proxy()
            ).text).xpath('//div[@class="product-card__information"]')
            if 'Nike' in element[0].xpath('h1[@class="product-card__title"]')[0].text
               or 'Yeezy' in element[0].xpath('h1[@class="product-card__title"]')[0].text
               or 'Jordan' in element[0].xpath('h1[@class="product-card__title"]')[0].text
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
        except IndexError:  # TODO return info, that target is sold out
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

        name = content.xpath('//meta[@property="og:title"]')[0].get('content').split(' -')[0]
        available_sizes = tuple(
            (element.get('data-value')) for element in content.xpath('//div[@class="swatch clearfix"]')[0].xpath('div'))
        return api.SSuccess(
            self.name,
            api.Result(
                name,
                target.data,
                'kith',
                content.xpath('//meta[@property="og:image"]')[0].get('content'),
                '',
                (
                    api.currencies['USD'],
                    float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content').replace(',', ''))
                ),
                {},
                tuple(
                    (
                        str(size_data.current_value['public_title']) + ' US',
                        'https://kith.com/cart/' + str(size_data.current_value['id']) + ':1'
                    ) for size_data in sizes_data if size_data.current_value['public_title'] in available_sizes
                ),
                (
                    ('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                    ('Cart', 'https://kith.com/cart'),
                    ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                )
            )
        )
