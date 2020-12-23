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
        self.link: str = 'https://api.net-a-porter.com/NAP/RU/en/60/0/summaries/expand?brandIds=1051,' \
                         '1840&categoryIds=4135&onSale=false&sort=category-default'
        self.interval: int = 1
        self.headers = {
            'authority': 'api.net-a-porter.com',
            'accept': '*/*',
            'user-agent': 'mobile-nap-netaporter/8.5.2 (iPhone; iOS 14.0.1; Scale/2.0)',
            'accept-language': 'ru'
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

            for c in loads(resp.text)['summaries']:
                if Keywords.check(c['name'].lower()):
                    result.append(
                        api.TScheduled(
                            str(c['id']),
                            self.name,
                            0,
                            time()
                        )
                    )

            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

        elif mode == 1:

            ok, resp = self.provider.request('https://api.net-a-porter.com/NAP/RU/en/detail/' + content.name,
                                             headers=self.headers, proxy=True)

            if not ok:

                if isinstance(resp, exceptions.Timeout):
                    return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]

                else:
                    raise resp

            json_data = loads(resp.text)

            name = f'{json_data["brand"]["name"]} {json_data["name"]}'
            link = f'https://www.net-a-porter.com/en-ru/shop/product/{content.name}'
            image = json_data['images']['urlTemplate'].replace('{{scheme}}', 'https:')\
                .replace('{{shot}}', 'in').replace('{{size}}', 'xl')
            sizes = api.Sizes(
                api.SIZE_TYPES[''],
                [
                    api.Size(sku['displaySize'])
                    for sku in json_data['skus']
                    if sku['stockLevel'] == 'In_Stock'
                ]
            )
            price = api.Price(api.CURRENCIES[json_data['price']['currency']],
                              float(json_data['price']['amount']) / float(json_data['price']['divisor']))

            result.append(
                IRelease(
                    f'{link}?shash={sizes.hash().hex()}',
                    'net-a-porter',
                    name,
                    image,
                    '',
                    price,
                    sizes,
                    [
                        FooterItem('Login', 'https://www.net-a-porter.com/ru/en/signin.nap'),
                        FooterItem('Cart', 'https://www.net-a-porter.com/ru/en/shoppingbag.nap')

                    ],
                    {
                        'Site': '[Net-A-Porter](https://www.net-a-porter.com)'
                    }
                )
            )

        result.append(content)
        return result
