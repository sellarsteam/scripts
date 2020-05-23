from json import loads, JSONDecodeError
from re import findall
from typing import List

from jsonpath2 import Path
from lxml import etree

from source import api
from source.api import IndexType, TargetType, StatusType
from source.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider, storage):
        super().__init__(name, log, provider, storage)
        self.catalog: str = 'https://extrabutterny.com/collections/footwear/Mens'
        self.interval: int = 1
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot.html)Mozilla/5.0 ' \
                          '(compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html)' \
                          'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 ' \
                          '(KHTML, like Gecko) Chrome/41.0.2272.96 Mobile Safari/537.36 ' \
                          '(compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html)'

    def index(self) -> IndexType:
        return api.IInterval(self.name, 3)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element[0].get('href').split('/')[4],
                          self.name, 'https://extrabutterny.com' + element[0].get('href'), self.interval)
            for element in etree.HTML(self.provider.get(self.catalog,
                                                        headers={'user-agent': self.user_agent}, proxy=True
                                                        )).xpath('//div[@class="GridItem-imageContainer"]')
            if
            'nike' in element[0].get('href') or 'jordan' in element[0].get('href') or 'yeezy' in element[0].get('href')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                get_content = self.provider.get(target.data, headers={'user-agent': self.user_agent}, proxy=True)
                content: etree.Element = etree.HTML(get_content)
                available_sizes = tuple(
                    i.current_value['sku'].split('-')[-1] for i in Path.parse_str('$.offers.*').match(
                        loads(content.xpath('//script[@type="application/ld+json"]')[0].text)) if
                    i.current_value['availability'] == 'https://schema.org/InStock')

                if content.xpath('//strong')[0].text.replace(' ', '').replace('\t', '').replace('\n', '') != 'SoldOut':
                    available = True
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
                            ) for size_data in sizes_data if size_data.current_value['public_title'] in available_sizes
                        ),
                        (
                            ('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                            ('Cart', 'https://extrabutterny.com/cart'),
                            ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                        )
                    )
                )
            except JSONDecodeError:
                return api.SFail(self.name, 'Exception JSONDecodeError')
        else:  # TODO return info, that target is sold out
            return api.SSuccess(
                self.name,
                api.Result(
                    'Sold out',
                    target.data,
                    'tech',
                    content.xpath('//meta[@property="og:image"]')[0].get('content'),
                    '',
                    (
                        api.currencies['USD'],
                        float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content'))
                    ),
                    {},
                    tuple(),
                    (('StockX', 'https://stockx.com/search/sneakers?s='),
                     ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
                )
            )
