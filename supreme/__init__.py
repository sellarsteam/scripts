from typing import List, Union

from lxml import etree
from requests.exceptions import SSLError
from user_agent import generate_user_agent
from time import time
import datetime
from datetime import timezone, timedelta, datetime
import threading

from source import logger
from source import api
from source.cache import HashStorage
from source.api import CatalogType, TargetType, CInterval, IRelease, RestockTargetType, ItemType, TargetEndType, \
    FooterItem, CSmart
from source.library import SubProvider


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://www.supremenewyork.com/shop/all'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, (datetime.utcnow() + timedelta(days=-((datetime.utcnow().weekday() - 3) % 7),
                                                                    weeks=1))
                          .replace(hour=10, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
                          .timestamp(), 5)

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result: list = [content]
        if mode == 0:
            content.timestamp = (datetime.utcnow() + timedelta(days=-((datetime.utcnow().weekday() - 3) % 7), weeks=1)) \
                .replace(hour=10, minute=0, second=0, microsecond=0, tzinfo=timezone.utc).timestamp()

            try:
                for element in etree.HTML(
                        self.provider.get(self.link, headers={'user-agent': self.user_agent})
                ).xpath('//a[@style="height:81px;"]'):
                    if len(element.xpath('div[@class="sold_out_tag"]')) == 0:
                        result.append(
                            api.TScheduled(
                                'https://www.supremenewyork.com/' + element.get('href'),
                                self.name,
                                0,
                                time()
                            )
                        )
            except SSLError:
                raise SSLError('Site is down')
            except etree.XMLSyntaxError:
                raise etree.XMLSyntaxError('Exception XMLDecodeError')
        elif mode == 1:
            page_content = etree.HTML(self.provider.get(content.name, headers={'user-agent': self.user_agent}))
            name = page_content.xpath('//h1[@itemprop="name"]')[0].text
            result.append(
                IRelease(
                    content.name,
                    'supreme-nyc',
                    name,
                    'https://' + page_content.xpath('//img[@itemprop="image"]')[0].get('src').replace('//', ''),
                    page_content.xpath('//p[@itemprop="description"]')[0].text,
                    api.Price(api.CURRENCIES['EUR'],
                              float(page_content.xpath('//span[@itemprop="price"]')[0].text.replace('€', ''))),
                    api.Sizes(api.SIZE_TYPES[''],
                              [api.Size(size.text) for size in page_content.xpath('//option[@value]')]),
                    [
                        FooterItem('StockX', 'https://stockx.com/search?s=' +
                                   page_content.xpath('//h1[@itemprop="name"]')
                                   [0].text.replace(' ', '%20').replace('®', '')),
                        FooterItem('Cart', 'https://www.supremenewyork.com/shop/cart'),
                        FooterItem('Mobile', 'https://www.supremenewyork.com/mobile#products/' +
                                   page_content.xpath('//form[@class="add"]')[0].get('action').split('/')[2]),
                        FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    ],
                    {'Site': 'Supreme'}
                )
            )
            HashStorage.add_target(content.hash())
        return result
