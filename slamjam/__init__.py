from typing import List

from lxml import etree

from source import api
from source.api import IndexType, TargetType, StatusType
from source.logger import Logger


def return_sold_out(data):
    return api.SSuccess(
        'slamjam',
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
    def __init__(self, name: str, log: Logger, provider: api.SubProvider, storage):
        super().__init__(name, log, provider, storage)
        self.catalog: str = 'https://www.slamjam.com/en_RU/man/new-in/this-week'
        self.interval: int = 1
        self.user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'

    def index(self) -> IndexType:
        return api.IInterval(self.name, 3)

    def targets(self) -> List[TargetType]:
        links = list()
        counter = 0
        for element in etree.HTML(self.provider.get(self.catalog,
                                                    headers={'user-agent': self.user_agent}, proxy=True, mode=1)) \
                .xpath('//div[@class="product "]'):
            if counter == 5:
                break
            if 'air' in element.get('data-url') or 'yeezy' in element.get('data-url') or 'jordan' \
                    in element.get('data-url') or 'dunk' in element.get('data-url'):
                links.append(element.get('data-url'))
                counter += 1
        return [
            api.TInterval(element.split('/')[7],
                          self.name, 'https://www.slamjam.com' + element, self.interval)
            for element in links
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                content: etree.Element = etree.HTML(self.provider.get(target.data, mode=1, proxy=True,
                                                                      headers={'user-agent': self.user_agent}))
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        available_sizes = list(element.text + ' EU'
                               for element in content.xpath('//select[@id="select-prenotation"]/option') if
                               element.get('data-availability') == 'true')
        if len(available_sizes) > 0 and content.xpath('//a[@itemprop="availability"]')[0].get('href') == \
                'http://schema.org/InStock':
            name = content.xpath('//meta[@name="keywords"]')[0].get('content')
            return api.SSuccess(
                self.name,
                api.Result(
                    name,
                    target.data,
                    'shopify-filtered',
                    content.xpath('//div[@class="slider-data-large"]/div')[0].get('data-image-url'),
                    '',
                    (
                        api.currencies['RUB'],
                        float(content.xpath('//div[@itemprop="price"]')[0].text)
                    ),
                    {'Site': 'Slam Jam'},
                    tuple(available_sizes),
                    (
                        ('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                        ('Cart', 'https://www.slamjam.com/cart'),
                        ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    )
                )
            )
        else:
            return return_sold_out(target.data)

