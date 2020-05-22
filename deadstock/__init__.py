from json import loads
from re import findall
from typing import List

from jsonpath2 import Path
from lxml import etree

from source import api
from source.api import IndexType, TargetType, StatusType
from source.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider):
        super().__init__(name, log, provider)
        self.catalog: str = 'https://www.deadstock.ca/collections/new-arrivals?sort_by=created-descending'
        self.interval: int = 1
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot.html)Mozilla/5.0 ' \
                          '(compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html)' \
                          'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 ' \
                          '(KHTML, like Gecko) Chrome/41.0.2272.96 Mobile Safari/537.36 (compatible; ' \
                          'Pinterestbot/1.0; +https://www.pinterest.com/bot.html)'

    def index(self) -> IndexType:
        return api.IInterval(self.name, 3)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[4],
                          self.name, 'https://www.deadstock.ca' + element.get('href'), self.interval)
            for element in etree.HTML(self.provider.get(
                self.catalog, headers={
                    'user-agent': self.user_agent
                }, proxy=True
            )).xpath('//a[@class=" grid-product__meta"]')
            if 'air' in element.get('href') or 'yeezy' in element.get('href') or 'jordan' in element.get('href')
               or 'sacai' in element.get('href') or 'dunk' in element.get('href')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                get_content = self.provider.get(url=target.data, headers={
                    'headers': self.user_agent
                }, proxy=True)
                content: etree.Element = etree.HTML(get_content)
                available_sizes = tuple(
                    size.get('for').split('-')[-1] for size in
                    content.xpath('//fieldset[@id="ProductSelect-option-0"]')[0].xpath('label[@class=""]')
                )
                if len(available_sizes) > 0:
                    available = True
                sizes_data = Path.parse_str('$.product.variants.*').match(
                    loads(findall(r'var meta = {.*}', get_content)[0].replace('var meta = ', '')))
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        if available:
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
                        api.currencies['USD'],
                        float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content'))
                    ),
                    {},
                    tuple(
                        (
                            str(size_data.current_value['public_title']) + ' US',
                            'https://www.deadstock.ca/cart/' + str(size_data.current_value['id']) + ':1'
                        ) for size_data in sizes_data if size_data.current_value['public_title'] in available_sizes
                    ),
                    (('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                     ('Cart', 'https://www.deadstock.ca/cart'),
                     ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
                )
            )
        else:  # TODO return info, that target is sold out
            return api.SSuccess(
                self.name,
                api.Result(
                    'Sold out',
                    target.data,
                    'tech',
                    content.xpath('//meta[@property="og:image"]')[2].get('content'),
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
