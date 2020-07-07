from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://beliefmoscow.com/collection/frontpage?order=&q='
        self.interval: int = 1
        self.user_agent = 'Mozilla/5.0 (compatible; YandexAccessibilityBot/3.0; +http://yandex.com/bots)'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 2, 10))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=2, microsecond=250000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            links = []
            for element in etree.HTML(self.provider.request(self.link, headers={'user-agent': self.user_agent}).text) \
                    .xpath('//a[@class="product_preview-link"]'):
                if 'yeezy' in element.get('href') or 'air' in element.get('href') or 'sacai' in element.get('href') \
                        or 'dunk' in element.get('href') or 'retro' in element.get('href'):
                    links.append(api.Target('https://beliefmoscow.com' + element.get('href'), self.name, 0))

            for link in links:
                try:
                    if HashStorage.check_target(link.hash()):
                        page_content: etree.Element = etree.HTML(
                            self.provider.request(link.name, headers={'user-agent': self.user_agent}).text)
                        try:
                            sizes = [
                                api.Size(str(size_data.text).split(' /')[0],
                                         f"http://static.sellars.cf/links/belief?id={size_data.get('value')}")
                                for size_data in
                                page_content.xpath('//select[@id="variant-select"]')[0].xpath('option')
                            ]
                        except IndexError:
                            HashStorage.add_target(link.hash())
                            continue
                        name = page_content.xpath('//meta[@property="og:title"]')[0].get('content')
                        HashStorage.add_target(link.hash())

                        result.append(
                            IRelease(
                                link.name,
                                'belief',
                                name,
                                page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                                '',
                                api.Price(
                                    api.CURRENCIES['RUB'],
                                    float(page_content.xpath('//div[@class="product-page__price"]')[0].text.replace(
                                        '₽', '').replace('\n', '').replace(' ', ''))
                                ),
                                api.Sizes(api.SIZE_TYPES[''], sizes),
                                [
                                    FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                               name.replace(' ', '%20')),
                                    FooterItem('Cart', 'https://beliefmoscow.com/cart'),
                                    FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                ],
                                {'Site': 'Belief Moscow'}
                            )
                        )
                except etree.XMLSyntaxError:
                    raise etree.XMLSyntaxError('Exception XMLDecodeError')
            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
