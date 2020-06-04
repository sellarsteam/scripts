from typing import List

from lxml import etree
from user_agent import generate_user_agent

from source import api
from source.api import IndexType, TargetType, StatusType
from source.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider, storage):
        super().__init__(name, log, provider, storage)
        self.catalog: str = 'https://www.tsum.ru/catalog/search/?q=yeezy'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 3)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[2],
                          self.name, 'https://www.tsum.ru' + element.get('href'), self.interval)
            for element in etree.HTML(self.provider.get(
                self.catalog,
                headers={'user-agent': self.user_agent}
            )).xpath('//a[@class="product__info"]')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                content: etree.Element = etree.HTML(self.provider.get(
                    target.data,
                    headers={'user-agent': generate_user_agent(),
                             'connection': 'keep-alive', 'cache-control': 'max-age=0',
                             'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                             'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image'
                                       '/webp,image/apng,*/*;q=0.8',
                             'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                             'sec-fetch-user': '?1',
                             'accept-language': 'en-US,en;q=0.9',
                             'referer': self.catalog
                             }))
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        name = content.xpath('//span[@class="breadcrumbs__link ng-star-inserted"]')[0].get('title')
        return api.SSuccess(
            self.name,
            api.Result(
                name,
                target.data,
                'russian-retailers',
                content.xpath('//img[@class="photo-inspector__image"]')[0].get('src'),
                '',
                (
                    api.currencies['RUB'],
                    float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content'))
                ),
                {},
                tuple([size.text.split(' |')[0] + ' US' for size in content.xpath('//span[@class="select__text"]') if
                       '|' in size.text][1:]),
                (
                    ('StockX', 'https://stockx.com/search/sneakers?s=' +
                     name.replace(' ', '%20').replace('Кроссовки', '')),
                    ('Cart', 'https://www.tsum.ru/cart'),
                    ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                )
            )
        )
