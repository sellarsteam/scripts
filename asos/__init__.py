import datetime
from datetime import timezone, timedelta, datetime
from time import time
from typing import List, Union

from requests import exceptions
from ujson import loads

from source import api
from source import logger
from source.api import CatalogType, TargetType, IRelease, RestockTargetType, ItemType, TargetEndType, \
    FooterItem
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://api.asos.com/product/search/v2/categories/4209?customerguid=c89b52686ec44937b0d4c2ac63d9c01e&offset=0&includeGroups=true&brand=14269&keyStoreDataversion=3pmn72e-27&limit=48&currency=RUB&sizeSchema=RU&country=RU&channel=mobile-app&lang=ru&store=ru'
        self.interval: int = 1
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
            'host': 'api.asos.com',

        }

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=0, microsecond=500000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result: list = []

        if mode == 0:
            result.append(content)
            ok, resp = self.provider.request(self.link, headers=self.headers)

            if not ok:

                if isinstance(resp, exceptions.Timeout):
                    return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]

                else:
                    raise resp

            print(resp.text)

            for c in loads(resp.text)['products']:
                if Keywords.check(c['name'].lower()):
                    result.append(
                        api.TScheduled(
                            str(c['id']),
                            self.name,
                            [c['url']],
                            time()
                        )
                    )

            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

        elif mode == 1:
            ok, resp = self.provider.request(f'https://api.asos.com/product/catalogue/v3/products/{content.name}?'
                                             f'sizeSchema=RU&store=RU&keyStoreDataversion=3pmn72e-27&'
                                             f'currency=RUB&lang=ru-RU', headers=self.headers)

            print(resp.text)

            if not ok:

                if isinstance(resp, exceptions.Timeout):
                    return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]

                else:
                    raise resp

            json_data = loads(resp.text)

            name = json_data["name"]
            link = f'https://asos.com/{content.data[0]}'
            image = 'https://' + json_data['media']['images'][0]['url']
            sizes = api.Sizes(
                api.SIZE_TYPES[''],
                [
                    api.Size(sku['brandSize'])
                    for sku in json_data['variants']
                    if sku['isInStock'] is True
                ]
            )
            price = api.Price(api.CURRENCIES['RUB'],
                              float(json_data['price']['current']['value']))

            result.append(
                IRelease(
                    f'{link}?shash={sizes.hash().hex()}',
                    'asos',
                    name,
                    image,
                    '',
                    price,
                    sizes,
                    [
                        FooterItem('Login', 'https://my.asos.com/'),
                        FooterItem('Cart', 'https://www.asos.com/bag')

                    ],
                    {
                        'Site': '[ASOS](https://asos.com)'
                    }
                )
            )

        result.append(content)
        return result
