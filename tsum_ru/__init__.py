from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from user_agent import generate_user_agent
from lxml import etree

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://www.tsum.ru/catalog/search/?q=yeezy'
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, self.time_gen(), 21, 5, 1.2)

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=0, microsecond=750000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            for element in etree.HTML(
                    self.provider.get(
                        self.link,
                        headers={'user-agent': self.user_agent}
                    )
            ).xpath('//a[@class="product__info"]'):
                try:
                    if HashStorage.check_target \
                                (api.Target('https://www.tsum.ru' + element.get('href'), self.name, 0).hash()):
                        page_content = etree.HTML(self.provider.get('https://www.tsum.ru' + element.get('href'),
                                                                    headers={'user-agent': self.user_agent}))
                        name = page_content.xpath('//span[@class="breadcrumbs__link ng-star-inserted"]')[0].get('title')
                        result.append(
                            IRelease(
                                'https://www.tsum.ru' + element.get('href'),
                                'tsum',
                                name,
                                page_content.xpath('//img[@class="photo-inspector__image"]')[0].get('src'),
                                '',
                                api.Price(
                                    api.CURRENCIES['RUB'],
                                    float(page_content.xpath('//meta[@property="og:price:amount"]')[0].get('content'))
                                ),
                                api.Sizes(api.SIZE_TYPES[''], [api.Size(size.text.split(' |')[0] + ' US')
                                                               for size in page_content.xpath('//span['
                                                                                              '@class="select__text"]')
                                                               if '|' in size.text and 'нет в наличии' not in size.text]
                                [1:]),
                                [
                                    FooterItem(
                                        'StockX',
                                        'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20').
                                        replace('"', '').replace('\n', '').replace(' ', '').replace('Кроссовки', '')
                                    ),
                                    FooterItem('Cart', 'https://www.tsum.ru/cart'),
                                    FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                ],
                                {'Site': 'TSUM'}
                            )
                        )
                except etree.XMLSyntaxError:
                    raise etree.XMLSyntaxError('XMLDecodeError')
            if result or content.expired:
                content.timestamp = self.time_gen()
                content.expired = False

            result.append(content)
        return result
