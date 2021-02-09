import datetime
from datetime import timezone, timedelta, datetime
from time import time
from typing import List, Union

import pycurl
import yaml

from source import api
from source import logger
from source.api import CatalogType, TargetType, IRelease, RestockTargetType, ItemType, TargetEndType, \
    FooterItem
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.men_link = "https://www.asos.com/api/product/search/v2/categories/4209?brand=14269,2986,13623,15177&channel=desktop-web&country=GB&currency=GBP&keyStoreDataversion=3pmn72e-27&lang=en-GB&limit=300&offset=0&rowlength=4&sort=freshness&store=COM"
        self.women_link = "https://www.asos.com/api/product/search/v2/categories/4172?brand=14269,2986,15177&channel=desktop-web&country=GB&currency=GBP&keyStoreDataversion=3pmn72e-27&lang=en-GB&limit=300&offset=0&rowlength=4&store=COM"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'
        }

        self.product_link: str = "https://api.asos.com/product/catalogue/v3/products/PRODUCT_ID?sizeSchema=UK&store=COM&keyStoreDataversion=3pmn72e-27&currency=GBP&lang=en-GB"

        self.interval: int = 1
        if self.storage.check('secret.yaml'):
            raw = yaml.safe_load(self.storage.file('secret.yaml'))
            if isinstance(raw, dict):
                if 'pids' in raw and isinstance(raw['pids'], list):
                        self.pids = [k for k in raw['pids']]
                else:
                    raise IndexError('secret.yaml must contain pids (as object)')
            else:
                raise TypeError('secret.yaml must contain object')
        else:
            raise FileNotFoundError('secret.yaml not found')

        del raw

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
            ok_0, resp_0 = self.provider.request(self.men_link, headers=self.headers)
            ok_1, resp_1 = self.provider.request(self.women_link, headers=self.headers)

            if not ok_0:
                if resp_0.args[0] == pycurl.E_OPERATION_TIMEOUTED:
                    return result
                else:
                    raise resp_0

            if not ok_1:
                if resp_1.args[0] == pycurl.E_OPERATION_TIMEOUTED:
                    return result
                else:
                    raise resp_1

            catalog_0 = resp_0.json()
            catalog_1 = resp_1.json()

            for pid in self.pids:
                result.append(api.TScheduled(str(pid), self.name, [str(pid)], time()))

            for c in catalog_0['products']:
                if self.kw.check(c['name'].lower() + ' ' + str(c['id'])):
                    result.append(
                        api.TScheduled(
                            str(c['id']),
                            self.name,
                            [c['url']],
                            time()
                        )
                    )

            for c in catalog_1['products']:
                if self.kw.check(c['name'].lower() + ' ' + str(c['id'])):
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

            ok, response = self.provider.request(self.product_link.replace('PRODUCT_ID', content.name),
                                                 headers=self.headers)

            if not ok:
                if response.args[0] == pycurl.E_OPERATION_TIMEOUTED:
                    return result
                else:
                    raise result

            json_data = response.json()

            try:

                name = json_data["name"]
                link = f'https://asos.com/{content.data[0]}'
                image = f"https://images.weserv.nl/?url={json_data['media']['images'][0]['url']}"

                row_sizes = [
                    api.Size(sku['brandSize'])
                    for sku in json_data['variants']
                    if sku['isInStock'] is True
                ]

                sizes = api.Sizes(api.SIZE_TYPES[''], row_sizes)
                price = api.Price(api.CURRENCIES['GBP'],
                                  float(json_data['price']['current']['value']))

                if row_sizes:
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
            except KeyError:
                pass

        return result
