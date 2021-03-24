import datetime
from datetime import timezone, timedelta, datetime
from time import time
from typing import List, Union

import pycurl
import yaml
from ujson import loads

from source import api
from source import logger
from source.api import CatalogType, TargetType, IRelease, RestockTargetType, ItemType, TargetEndType, \
    FooterItem
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
# https://www.asos.com/api/product/search/v2/categories/6455?attribute_1046=8620&channel=desktop-web&country=PL&currency=GBP&keyStoreDataversion=hnm9sjt-28&lang=pl-PL&limit=72&offset=0&rowlength=4&store=PL
        # RU region
        self.ru_men_link = "https://www.asos.com/api/product/search/v2/categories/4172?attribute_1047=8606" \
                           "&brand=14269,2986,13623&country=RU&currency=RUB&lang=ru-RU&limit=100&store=RU&keyStoreDataversion=3pmn72e-27"
        self.ru_women_link = "https://www.asos.com/api/product/search/v2/categories/4172?attribute_1047=8606" \
                             "&brand=14269,2986&country=RU&currency=RUB&lang=ru-RU&limit=100&store=RU&keyStoreDataversion=3pmn72e-27"
        self.ru_aj1_search_link = "https://www.asos.com/api/product/search/v2/?attribute_10992=61388&country" \
                                  "=RU&currency=RUB&lang=ru-RU&limit=100&q=air%20jordan%201&store=RU&keyStoreDataversion=3pmn72e-27"
        self.ru_dunk_search_link = "https://www.asos.com/api/product/search/v2/?attribute_1047=8606&attribut" \
                                   "e_10992=61388&country=RU&currency=RUB&lang=ru-RU&limit=100&q=dunk&store=RU&keyStoreDataversion=3pmn72e-27"

        # GB/COM region
        self.en_women_link = "https://www.asos.com/api/product/search/v2/categories/4172?attribute_1047=8606&b" \
                             "rand=14269,2986&country=GB&currency=GBP&lang=en-GB&limit=100&store=COM&keyStoreDataversion=3pmn72e-27"
        self.en_men_link = "https://www.asos.com/api/product/search/v2/categories/4209?attribute_1047=8606&bra" \
                           "nd=14269,2986,13623&country=GB&currency=GBP&lang=en-GB&limit=100&store=COM&keyStoreDataversion=3pmn72e-27"
        self.en_aj1_search_link = "https://www.asos.com/api/product/search/v2/?attribute_10992=61388&country=GB" \
                                  "&currency=GBP&lang=en-GB&limit=100&q=air%20jordan%201&store=COM&keyStoreDataversion=3pmn72e-27"
        self.en_dunk_search_link = "https://www.asos.com/api/product/search/v2/?attribute_1047=8606&attribute_1" \
                                   "0992=61388&country=GB&currency=GBP&lang=en-GB&limit=100&q=dunk&store=COM&keyStoreDataversion=3pmn72e-27"

        # Poland
        self.pl_men_link = "https://www.asos.com/api/product/search/v2/categories/4172?attribute_1047=8606" \
                           "&brand=14269,2986,13623&country=PL&currency=GBP&lang=pl-PL&limit=100&store=PL&keyStoreDataversion=3pmn72e-27"
        self.pl_women_link = "https://www.asos.com/api/product/search/v2/categories/4172?attribute_1047=8606" \
                             "&brand=14269,2986&country=PL&currency=GBP&lang=pl-PL&limit=100&store=PL&keyStoreDataversion=3pmn72e-27"
        self.pl_aj1_search_link = "https://www.asos.com/api/product/search/v2/?attribute_10992=61388&country" \
                                  "=PL&currency=GBP&lang=pl-PL&limit=100&q=air%20jordan%201&store=PL&keyStoreDataversion=3pmn72e-27"
        self.pl_dunk_search_link = "https://www.asos.com/api/product/search/v2/?attribute_1047=8606&attribut" \
                                   "e_10992=61388&country=PL&currency=GBP&lang=pl-PL&limit=100&q=dunk&store=PL&keyStoreDataversion=3pmn72e-27"

        # Products links
        self.en_product_link = "https://www.asos.com/api/product/catalogue/v3/products/PRODUCT_ID" \
                               "?store=COM&currency=GBP&keyStoreDataversion=3pmn72e-27"
        self.ru_product_link = "https://www.asos.com/api/product/catalogue/v3/products/PRODUCT_ID" \
                               "?store=RU&currency=RUB&keyStoreDataversion=3pmn72e-27"
        self.pl_product_link = "https://www.asos.com/api/product/catalogue/v3/products/PRODUCT_ID" \
                               "?store=PL&currency=RUB&keyStoreDataversion=3pmn72e-27"

        self.headers = {
            'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'
        }

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
            result.append(api.TScheduled('ru_men_catalog', self.name,
                                         ['catalog', self.ru_men_link, 'RUB', 'Russia :flag_ru:'], time()))
            result.append(api.TScheduled('ru_women_catalog', self.name,
                                         ['catalog', self.ru_women_link, 'RUB', 'Russia :flag_ru:'], time()))
            result.append(api.TScheduled('ru_search_aj1_catalog', self.name,
                                         ['catalog', self.ru_aj1_search_link, 'RUB', 'Russia :flag_ru:'], time()))
            result.append(api.TScheduled('ru_search_dunk_catalog', self.name,
                                         ['catalog', self.ru_dunk_search_link, 'RUB', 'Russia :flag_ru:'], time()))

            result.append(api.TScheduled('en_men_catalog', self.name,
                                         ['catalog', self.en_men_link, 'GBP', 'UK :flag_gb:'], time()))
            result.append(api.TScheduled('en_women_catalog', self.name,
                                         ['catalog', self.en_women_link, 'GBP', 'UK :flag_gb:'], time()))
            result.append(api.TScheduled('en_search_aj1_catalog', self.name,
                                         ['catalog', self.en_aj1_search_link, 'GBP', 'UK :flag_gb:'], time()))
            result.append(api.TScheduled('en_search_dunk_catalog', self.name,
                                         ['catalog', self.en_dunk_search_link, 'GBP', 'UK :flag_gb:'], time()))

            result.append(api.TScheduled('pl_men_catalog', self.name,
                                         ['catalog', self.pl_men_link, 'POL', 'PL :flag_pl:'], time()))
            result.append(api.TScheduled('pl_women_catalog', self.name,
                                         ['catalog', self.pl_women_link, 'POL', 'PL :flag_pl:'], time()))
            result.append(api.TScheduled('pl_search_aj1_catalog', self.name,
                                         ['catalog', self.pl_aj1_search_link, 'POL', 'PL :flag_pl:'], time()))
            result.append(api.TScheduled('pl_search_dunk_catalog', self.name,
                                         ['catalog', self.pl_dunk_search_link, 'POL', 'PL :flag_pl:'], time()))

            for pid in self.pids:
                result.append(api.TScheduled(str(pid), self.name, ['item', 'GBP', 'UK :flag_gb:'], time()))
                result.append(api.TScheduled(str(pid), self.name, ['item', 'RUB', 'RU :flag_ru:'], time()))
                result.append(api.TScheduled(str(pid), self.name, ['item', 'POL', 'PL :flag_pl:'], time()))

            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

        elif mode == 1:
            if content.data[0] == 'catalog':
                ok, response = self.provider.request(content.data[1], headers=self.headers)
                try:
                    catalog = loads(response.text)
                except (AttributeError, ValueError):
                    result.append(result.append(api.MAlert(f'Script is down {content.name}', self.name)))
                    return result

                if not ok:
                    return result

                for c in catalog['products']:

                    if self.kw.check(c['name'].lower() + ' ' + str(c['id'])):
                        result.append(
                            api.TScheduled(
                                str(c['id']),
                                self.name,
                                ['item', content.data[2], content.data[3]],
                                time()
                            )
                        )

            elif content.data[0] == 'item':
                if content.data[1] == 'RUB':
                    product_url = self.ru_product_link
                    currency = 'RUB'
                    region = 'ru'
                elif content.data[1] == 'GBP':
                    product_url = self.en_product_link
                    currency = 'GBP'
                    region = 'gb'
                else:
                    product_url = self.pl_product_link
                    currency = 'RUB'
                    region = 'pl'

                ok, response = self.provider.request(product_url.replace('PRODUCT_ID', content.name),
                                                     headers=self.headers)

                if not ok:
                    if response.args[0] == pycurl.E_OPERATION_TIMEOUTED:
                        return result
                    else:
                        raise result
                try:
                    json_data = response.json()
                except ValueError:
                    result.append(result.append(api.MAlert(f'Script is down {content.name}', self.name)))
                    return result

                try:
                    name = json_data["name"]
                except KeyError:
                    if json_data['errorCode'] == 'pdt_011':
                        return result

                link = f'https://asos.com/{region}/prd/{content.name}'
                image = f"https://images.weserv.nl/?url={json_data['media']['images'][0]['url']}"

                raw_sizes = []

                for sku in json_data['variants']:
                    if sku['isInStock']:
                        if sku['isLowInStock']:
                            raw_sizes.append(
                                api.Size(f"{sku['brandSize']} [LOW]"))
                        else:
                            raw_sizes.append(
                                api.Size(f"{sku['brandSize']} [HIGH]"))

                sizes = api.Sizes(api.SIZE_TYPES[''], raw_sizes)
                price = api.Price(api.CURRENCIES[currency],
                                  float(json_data['price']['current']['value']))

                if raw_sizes:
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
                                'Site': '[ASOS](https://asos.com)',
                                'Region': content.data[2]
                            }
                        )
                    )

        return result
