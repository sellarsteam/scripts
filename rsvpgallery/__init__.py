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
        self.catalog: str = 'https://rsvpgallery.com/collections/footwear?sort_by=created-descending'
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
        for element in etree.HTML(self.provider.get(self.catalog,
                                                    headers={'user-agent': self.user_agent}, proxy=True)) \
                .xpath('//div[@class="product-details"]/a'):
            if counter == 5:
                break
            if 'slider' not in element.get('href') and ('yeezy' in element.get('href')
                                                        or 'air' in element.get('href')
                                                        or 'dunk' in element.get('href')
                                                        or 'dunk' in element.get('href')
                                                        or 'retro' in element.get('href')
                                                        or 'blazer' in element.get('href')
                                                        or 'off-white' in element.get('href')):
                links.append(element.get('href'))
                counter += 1
        return [
            api.TInterval(element.split('/')[-1],
                          self.name, 'https://rsvpgallery.com' + element, self.interval)
            for element in links
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                get_content = self.provider.get(target.data, headers={'user-agent': self.user_agent}, proxy=True)
                content: etree.Element = etree.HTML(get_content)
                available_sizes = tuple(
                    (str(size_data.current_value['public_title']) + ' EU',
                     'https://rsvpgallery.com/cart/' + str(size_data.current_value['id']) + ':1') for size_data in
                    Path.parse_str('$.variants.*').match(
                        loads(findall(r'product: {.*}', get_content)[0].replace('product: ', ''))) if
                    size_data.current_value['available'] is True)
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')
        if len(available_sizes) > 0:
            name = content.xpath('//h1[@class="desktop-12"]')[0].text
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
                        float(content.xpath('//div[@class="price-field"]/span')[0].text.split(' ')[1])
                    ),
                    {'Site': 'RSVP Gallery'},
                    available_sizes,
                    (
                        ('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                        ('Cart', 'https://rsvpgallery.com/cart'),
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
