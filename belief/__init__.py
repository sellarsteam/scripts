from datetime import datetime, timedelta, timezone
from typing import List, Union

from requests import exceptions
from ujson import loads

from scripts.keywords_finding import check_name
from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, ScriptStorage
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://beliefmoscow.com/collection/all.json'
        self.interval: int = 1
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Host': 'beliefmoscow.com',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        }

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=0, microsecond=250000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []

        if mode == 0:
            result.append(content)

            ok, resp = self.provider.request(self.link, headers=self.headers)

            if not ok:
                if isinstance(resp, exceptions.Timeout):
                    return result
                else:
                    raise result

            try:
                json = loads(resp.content)

            except ValueError:
                return [api.CInterval(self.name, 300)]

            for product in json['products']:

                if check_name(product['permalink'].lower()) or check_name(product['title'].lower()):

                    target = api.Target(f'https://beliefmoscow.com{product["url"]}', self.name, 0)

                    if HashStorage.check_target(target.hash()):

                        url = f'https://beliefmoscow.com{product["url"]}'
                        name = product['title']
                        price = api.Price(
                            api.CURRENCIES['RUB'],
                            float(product['variants'][0]['price'])

                        )
                        image = product['images'][0]['medium_url'] if len(product['images']) != 0 \
                            else 'http://via.placeholder.com/300/2A2A2A/FFF?text=No+image'

                        raw_sizes = [api.Size(f"{size['title'].split(' /')[0]} [{size['quantity']}]",
                                              f"http://static.sellars.cf/links?site=belief&id={size['id']}")
                                     for size in product['variants'] if size['quantity'] > 0]

                        sizes = api.Sizes(api.SIZE_TYPES[''], raw_sizes)

                        if not raw_sizes:
                            continue

                        HashStorage.add_target(target.hash())

                        result.append(
                            IRelease(
                                url,
                                'belief',
                                name,
                                image,
                                '',
                                price,
                                sizes,
                                [
                                    FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                               name.replace(' ', '%20')),
                                    FooterItem('Cart', 'https://beliefmoscow.com/cart'),
                                    FooterItem(
                                        'Urban QT',
                                        f'https://autofill.cc/api/v1/qt?storeId=beliefmoscow&monitor={url}'
                                    ),
                                    FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                ],
                                {'Site': '[Belief Moscow](https://beliefmoscow.com)'}
                            )
                        )

                    else:

                        url = f'https://beliefmoscow.com{product["url"]}'
                        name = product['title']
                        price = api.Price(
                            api.CURRENCIES['RUB'],
                            float(product['variants'][0]['price'])

                        )
                        image = product['images'][0]['medium_url'] if len(product['images']) != 0 \
                            else 'http://via.placeholder.com/300/2A2A2A/FFF?text=No+image'

                        if len(product['variants']) == 0:
                            HashStorage.remove_item(
                                IRelease(
                                    url,
                                    'belief',
                                    name,
                                    image,
                                    '',
                                    price,
                                    api.Sizes(api.SIZE_TYPES[''], []),
                                    [
                                        FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                                   name.replace(' ', '%20')),
                                        FooterItem('Cart', 'https://beliefmoscow.com/cart'),
                                        FooterItem(
                                            'Urban QT',
                                            f'https://autofill.cc/api/v1/qt?storeId=beliefmoscow&monitor={url}'
                                        ),
                                        FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                    ],
                                    {'Site': '[Belief Moscow](https://beliefmoscow.com)'}
                                ).hash()
                            )

            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
