from datetime import datetime, timedelta, timezone
from json import loads, JSONDecodeError
from typing import List, Union

from requests import exceptions

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, ScriptStorage, Keywords
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link_new_catalog: str = 'http://api1.imshop.io/v1/clients/streetbeat/items?category=8f02a684-51f9-5d4a' \
                                     '-a59c-ab7099a9f913&q_vendor[]=Jordan&q_vendor[]=Nike&q_vendor[]=adidas ' \
                                     'Originals&region=Санкт-Петербург&regionWithType=г ' \
                                     'Санкт-Петербург&area=null&areaWithType=null&city=Санкт-Петербург&cityWithType=г '\
                                     'Санкт-Петербург&settlement=null&settlementWithType=null&street=null&house=null' \
                                     '&block=null&apt=null&lat=59.939084&lon=30.315879&streetWithType=null&areaFiasId' \
                                     '=null&cityFiasId=c2deb16a-0330-4f05-821f-1d09c93331e6&regionFiasId=c2deb16a' \
                                     '-0330-4f05-821f-1d09c93331e6&settlementFiasId=null&streetFiasId=null' \
                                     '&houseFiasId=null&regionKladrId=7800000000000&cityKladrId=7800000000000' \
                                     '&areaKladrId=null&settlementKladrId=null&streetKladrId=null&houseKladrId=null' \
                                     '&federalDistrict=null&fiasId=c2deb16a-0330-4f05-821f-1d09c93331e6&fiasCode' \
                                     '=7800000000000000000&kladrId=7800000000000&postalCode=190000&valueCity' \
                                     '=Санкт-Петербург&valueCityFull=Санкт-Петербург&valueAddress=&valueAddressFull=г '\
                                     'Санкт-Петербург&page=1 '
        self.headers = {
            'Host': 'api1.imshop.io',
            'Accept': '*/*',
            'Accept-Language': 'ru',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': 'imshopmobile/2353 CFNetwork/1197 Darwin/20.0.0'
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

            ok, response = self.provider.request(self.link_new_catalog, headers=self.headers)

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.)]
                else:
                    raise response

            json_response = loads(response.text)

            for element in json_response['items']:
                name = element['name']

                if Keywords.check(name.lower()):

                    link = element['externalUrl']

                    try:
                        if HashStorage.check_target(api.Target(link, self.name, 0).hash()):
                            mobile_link = f'https://content.imshop.io/landings/streetbeat/item/{element["privateId"]}'
                            name = element['name']
                            price = api.Price(api.CURRENCIES['RUB'], float(element['price']))
                            metadata = element['configurations']['metadata']
                            sizes = api.Sizes(api.SIZE_TYPES[''], [api.Size(f"{size['paramNames'][-1]['value']} US",
                                                                            f"https://static.sellars.cf/links?site="
                                                                            f"streetbeat&id={size['id']}")
                                                                   for size in metadata.values()])

                            image = element['image'].replace('street-beat', 'static.street-beat')

                            result.append(
                                IRelease(
                                    link,
                                    'streetbeat',
                                    name,
                                    image,
                                    '',
                                    price,
                                    sizes,
                                    [
                                        FooterItem('Cart', 'https://street-beat.ru/cart'),
                                        FooterItem('Mobile', mobile_link),
                                        FooterItem('Urban QT',
                                                   f'https://autofill.cc/api/v1/qt?storeId=streetbeat&monitor={link}')
                                    ],
                                    {'Site': '[Street-Beat](https://street-beat.ru)'}
                                )
                            )

                    except JSONDecodeError:
                        raise Exception('JSONDecodeError')
            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
