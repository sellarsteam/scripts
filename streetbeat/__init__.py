from json import loads, JSONDecodeError
from typing import List

from lxml import etree
from requests import get

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://street-beat.ru/cat/man/adidas-originals/?sort=create&order=desc'
        self.interval: int = 1
        self.user_agent = 'APIs-Google (+https://developers.google.com/webmasters/APIs-Google.html)'

    def index(self) -> IndexType:
        return api.IInterval(self.name, 1)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element[0].xpath('a[@class="link link--no-color catalog-item__title ddl_product_link"]')[0]
                          .get('href').split('/')[2],
                          self.name, 'https://street-beat.ru' +
                          element[0].xpath('a[@class="link link--no-color catalog-item__title ddl_product_link"]')[0]
                          .get('href'),
                          self.interval)
            for element in etree.HTML(get(
                url=self.catalog, headers={'user-agent': self.user_agent}
            ).text).xpath('//div[@class="col-xl-3 col-md-4 col-xs-6 view-type_"]')
            if 'Yeezy' in element[0].xpath('a[@class="link link--no-color catalog-item__title '
                                           'ddl_product_link"]/span')[0].text
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                content: etree.Element = etree.HTML(
                    get(url=target.data, headers={'user-agent': self.user_agent}).text)
                json_content = loads(content.xpath('//script[@type="application/ld+json"]')[1].text)
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')
        available_sizes = list()
        for size in content.xpath('//ul[@class="sizes__table current"]//li'):
            if size.get('class') == 'last':
                available_sizes.append(f'{str(size.xpath("label")[0].text)} RU [LAST]')
            elif size.get('class') == 'missing':
                continue
            else:
                available_sizes.append(f'{str(size.xpath("label")[0].text)} RU')
        sizes = tuple(available_sizes)
        name = content.xpath('//h1[@class="product-heading"]')[0].xpath('span')[0].text.split('кроссовки ')[-1]
        if json_content['offers']['availability'] == 'http://schema.org/InStock':
            return api.SSuccess(
                self.name,
                api.Result(
                    name,
                    target.data,
                    'russian-retailers',
                    json_content['image'],
                    '',
                    (api.currencies['RUB'], float(json_content['offers']['price'])),
                    {},
                    sizes,
                    (('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                     ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
                )
            )
        else:  # TODO Fix when item is sold out
            return api.SSuccess(
                self.name,
                api.Result(
                    f'Sold Out {name}',
                    target.data,
                    'tech',
                    '',
                    '',
                    (api.currencies['EUR'], 1.0),
                    {},
                    tuple(),
                    (('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                     ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
                )
            )
