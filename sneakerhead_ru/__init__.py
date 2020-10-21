from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from requests import exceptions

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://sneakerhead.ru/shoes/adidas-originals-or-jordan-or-nike-or-nike-sb/?sort' \
                         '=date_avail_desc '
        self.interval: int = 1
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
            'Host': 'sneakerhead.ru',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=1, microsecond=0, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:

            ok, response = self.provider.request(self.link, headers=self.headers)

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.)]
                else:
                    raise response

            for element in etree.HTML(response.text).xpath('//div[@class="product-cards__item"]'):

                if Keywords.check(element[0].xpath('meta[@itemprop="description"]')[0].get('content').lower()):

                    try:

                        link = 'https://sneakerhead.ru' + element[0].xpath('h5[@class="product-card__title"]/a')[0].get(
                            'href')

                        if HashStorage.check_target(api.Target(link, self.name, 0).hash()):

                            name = element[0].xpath('meta[@itemprop="description"]')[0].get('content')
                            image = 'https://sneakerhead.ru' + \
                                    element[0].xpath('div[@class="product-card__image"]/div/picture/source')[0] \
                                    .get('data-src')
                            price = api.Price(
                                api.CURRENCIES['RUB'],
                                float(element[0].xpath('div[@class="product-card__price"]/meta[@itemprop="price"]')[0]
                                      .get('content'))
                            )

                            sizes = api.Sizes(
                                api.SIZE_TYPES[''],
                                [
                                    api.Size(
                                        str(size.text),
                                        f'http://static.sellars.cf/links?site=sneakerhead&id={size.get("data-id")}'
                                    )
                                    for size in element[0].xpath('div[@class="product-card__hover"]/dl/dd')
                                ]
                            )

                            HashStorage.add_target(api.Target(link, self.name, 0).hash())

                            result.append(
                                IRelease(
                                    link,
                                    'sneakerhead',
                                    name,
                                    image,
                                    '',
                                    price,
                                    sizes,
                                    [
                                        FooterItem('Cart', 'https://sneakerhead.ru/cart'),
                                        FooterItem('Login', 'https://sneakerhead.ru/login'),
                                        FooterItem('Urban QT',
                                                   f'https://autofill.cc/api/v1/qt?storeId=sneakerhead&monitor={link}')
                                    ],
                                    {'Site': '[Sneakerhead](https://sneakerhead.ru)'}
                                )
                            )

                    except etree.XMLSyntaxError:
                        raise etree.XMLSyntaxError('XMLDecodeError')

            if result or (isinstance(content, api.CSmart) and content.expired):
                if isinstance(content, api.CSmart()):
                    content.gen.time = self.time_gen()
                    content.expired = False
                    result.append(content)
                else:
                    result.append(self.catalog())

        return result
