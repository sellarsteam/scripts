from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from user_agent import generate_user_agent
from lxml import etree

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem, \
    IAnnounce
from source.cache import HashStorage
from source.library import SubProvider


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://brandshop.ru/New/'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, self.time_gen(), 21, 5, 1.2)

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=0, microsecond=500000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            links = []
            for element in etree.HTML(
                    self.provider.get(
                        self.link,
                        headers={'user-agent': self.user_agent}
                    )
            ).xpath('//div[@class="product"]/a'):
                if 'yeezy' in element.get('href') or 'air' in element.get('href') or 'sacai' in element.get('href') \
                        or 'dunk' in element.get('href') or 'retro' in element.get('href'):
                    try:
                        if HashStorage.check_target(api.Target(element.get('href'), self.name, 0).hash()):
                            page_content = etree.HTML(
                                self.provider.get(element.get('href'), headers={'user-agent': self.user_agent}))
                            sizes = [api.Size(size.text) for size in page_content.xpath('//div[@class="sizeselect"]')]
                            name = page_content.xpath('//span[@itemprop="name"]')[0].text
                            HashStorage.add_target(api.Target(element.get('href'), self.name, 0).hash())
                            result.append(
                                IRelease(
                                    element.get('href'),
                                    'brandshop',
                                    name,
                                    page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                                    '',
                                    api.Price(
                                        api.CURRENCIES['RUB'],
                                        float(page_content.xpath('//meta[@itemprop="price"]')[0].get('content'))
                                    ),
                                    api.Sizes(api.SIZE_TYPES[''], sizes),
                                    [
                                        FooterItem(
                                            'StockX',
                                            'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20').
                                            replace('"', '').replace('\n', '').replace(' ', '')
                                        ),
                                        FooterItem('Cart', 'https://brandshop.ru/cart'),
                                        FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                    ],
                                    {'Site': 'Brandshop'}
                                )
                            )
                    except etree.XMLSyntaxError:
                        raise etree.XMLSyntaxError('XMLDecodeEroor')
                elif element.get('href') == 'javascript:void(0);':
                    result.append(IAnnounce(
                        'https://brandshop.ru/New/',
                        'russian-retailers',
                        element.xpath('img')[0].get('alt'),
                        element.xpath('img')[0].get('src'),
                        'Подробности скоро',
                        api.Price(api.CURRENCIES['RUB'], float(0)),
                        api.Sizes(api.SIZE_TYPES[''], []),
                        [
                            FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                       element.xpath('img')[0].get('alt')
                                       .replace(' ', '%20').replace('"', '').replace('\n', '').replace(' ', '')),
                            FooterItem('Cart', 'https://brandshop.ru/cart'),
                            FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                        ],
                        {'Site': 'Brandshop'}
                    ))
            if result or content.expired:
                content.timestamp = self.time_gen()
                content.expired = False

            result.append(content)
        return result
