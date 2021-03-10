from datetime import datetime, timedelta, timezone
from typing import List, Union

from ujson import loads

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.link: str = 'https://beliefmoscow.com/collection/obuv.json'
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
                result.append(api.MAlert('Script is down', self.name))
                products = []

            try:
                json = loads(resp.content)
                products = json['products']

            except ValueError:
                result.append(api.MAlert('Script is down', self.name))
                products = []

            for product in products:

                if self.kw.check(product['permalink'].lower()) or self.kw.check(product['title'].lower()):

                    target = api.Target(f'https://beliefmoscow.com{product["url"]}', self.name, 0)

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

                    if HashStorage.check_target(target.hash()):
                        HashStorage.add_target(target.hash())
                        additional_columns = {'Site': '[Belief Moscow](https://beliefmoscow.com)'}
                    else:
                        additional_columns = {'Site': '[Belief Moscow](https://beliefmoscow.com)', 'Type': 'Restock'}

                    result.append(
                        IRelease(
                            url + f'?shash={sizes.hash().hex()}',
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
                                FooterItem('Cart', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            additional_columns
                        )
                    )

            if isinstance(content, api.CSmart):
                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False
                result.append(content)
            else:
                result.extend([self.catalog, api.MAlert('Script is awake', self.name)])

        return result
