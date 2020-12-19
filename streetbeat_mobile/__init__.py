from datetime import datetime, timedelta, timezone
from json import loads, JSONDecodeError
from time import time
from typing import List, Union

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
        self.catalog_link: str = 'http://api1.imshop.io/v1/clients/streetbeat/items?term=TERMPATTERN&region' \
                                 '=Москва&regionWithType=г ' \
                                 'Москва&area=null&areaWithType=null&city=Москва&cityWithType=г ' \
                                 'Москва&settlement=null&settlementWithType=null&street=null&house=null&block' \
                                 '=null&apt=null&lat=55.75396&lon=37.620393&streetWithType=null&areaFiasId' \
                                 '=null&cityFiasId=0c5b2444-70a0-4932-980c-b4dc0d3f02b5&regionFiasId=0c5b2444' \
                                 '-70a0-4932-980c-b4dc0d3f02b5&settlementFiasId=null&streetFiasId=null' \
                                 '&houseFiasId=null&regionKladrId=7700000000000&cityKladrId=7700000000000' \
                                 '&areaKladrId=null&settlementKladrId=null&streetKladrId=null&houseKladrId' \
                                 '=null&federalDistrict=null&fiasId=0c5b2444-70a0-4932-980c-b4dc0d3f02b5' \
                                 '&fiasCode=7700000000000000000&kladrId=7700000000000&postalCode=null' \
                                 '&valueCity=Москва&valueCityFull=Москва&valueAddress=&valueAddressFull=г ' \
                                 'Москва&page=1 '

        self.headers = {
            'Host': 'api1.imshop.io',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'platform': 'ios',
            'client-version': '5.9.14',
            'install-id': '7fe2b20f-7e94-4152-b2e3-a2001c363f6c',
            'Accept-Language': 'ru',
            'User-Agent': 'imshopmobile/2517 CFNetwork/1197 Darwin/20.0.0'
        }

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=1, microsecond=250000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            result.append(api.TScheduled(self.catalog_link.replace('TERMPATTERN', 'Jordan'), self.name, 0, time()))
            result.append(api.TScheduled(self.catalog_link.replace('TERMPATTERN', 'Jordan').replace('page=1', 'page=2')
                                         , self.name, 0, time()))
            result.append(api.TScheduled(self.catalog_link.replace('TERMPATTERN', 'Jordan').replace('page=1', 'page=3')
                                         , self.name, 0, time()))

            result.append(api.TScheduled(self.catalog_link.replace('TERMPATTERN', 'yeezy'), self.name, 0, time()))
            result.append(api.TScheduled(self.catalog_link.replace('TERMPATTERN', 'yeezy').replace('page=1', 'page=2')
                                         , self.name, 0, time()))
            result.append(api.TScheduled(self.catalog_link.replace('TERMPATTERN', 'yeezy').replace('page=1', 'page=3')
                                         , self.name, 0, time()))

            result.append(api.TScheduled(self.catalog_link.replace('TERMPATTERN', 'nike%20sb'), self.name, 0, time()))
            result.append(api.TScheduled(self.catalog_link.replace('TERMPATTERN', 'nike%20sb')
                                         .replace('page=1', 'page=2'), self.name, 0, time()))
            result.append(api.TScheduled(self.catalog_link.replace('TERMPATTERN', 'nike%20sb')
                                         .replace('page=1', 'page=3'), self.name, 0, time()))

            if isinstance(content, api.CSmart):
                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False
                result.append(content)
            else:
                result.extend([self.catalog, api.MAlert('Script is awake', self.name)])

        if mode == 1:

            ok, response = self.provider.request(content.name, headers=self.headers)

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]
                else:
                    raise response

            json_response = loads(response.text)

            for element in json_response['items']:
                name = element['name']

                if Keywords.check(name.lower()):

                    link = element['externalUrl']

                    try:
                        if HashStorage.check_target(api.Target(link, self.name, 0).hash()):
                            mobile_link = f'https://content.imshop.io/landings' \
                                          f'/streetbeat/item/{element["privateId"]}'
                            price = api.Price(api.CURRENCIES['RUB'], float(element['price']))
                            metadata = element['configurations']['metadata']
                            sizes = api.Sizes(api.SIZE_TYPES[''],
                                              [api.Size(f"{size['paramNames'][-1]['value']} US")
                                               for size in metadata.values()])

                            image = element['image']

                            result.append(
                                IRelease(
                                    mobile_link,
                                    'streetbeat-mobile',
                                    name,
                                    image,
                                    '',
                                    price,
                                    sizes,
                                    [
                                        FooterItem('Cart', 'https://street-beat.ru/cart'),
                                        FooterItem('Mobile', mobile_link),
                                    ],
                                    {'Site': 'Street-Beat Mobile App',
                                     'Download App': '[Android](https://play.google.com/store/apps/details?id='
                                                     'ru.streetbeat.android&hl=en_US) | '
                                                     '[iOS](https://apps.apple.com/ru/app/street-beat-'
                                                     '%D0%BA%D1%80%D0%BE%D1%81%D1%81%D0%BE%D0%B2%D0%BA%'
                                                     'D0%B8-%D0%BE%D0%B4%D0%B5%D0%B6%D0%B4%D0%B0/id1484704923)'
                                     }
                                )
                            )

                    except JSONDecodeError:
                        raise Exception('JSONDecodeError')

        return result
