from datetime import datetime, timedelta, timezone
from json import JSONDecodeError
from typing import List, Union

from jsonpath2 import Path
from requests import exceptions
from ujson import loads
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://api.tsum.ru/v2/catalog/search?section=18440&brand=2165673,2030075,2375139'
        self.user_agent = generate_user_agent()

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

            ok, resp = self.provider.request(self.link,
                                             headers={'user-agent': self.user_agent, 'accept': 'application/json'})

            if not ok:
                if isinstance(resp, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]
                else:
                    raise resp

            try:
                json = loads(resp.content)
            except ValueError:
                return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]

            for element in Path.parse_str('$.*').match(json):
                try:
                    name = element.current_value['title']

                    if Keywords.check(name):
                        target = api.Target('https://www.tsum.ru/' + element.current_value['slug'], self.name, 0)

                        if HashStorage.check_target(target.hash()):
                            HashStorage.add_target(target.hash())
                            additional_columns = {'Site': '[TSUM](https://www.tsum.ru/)'}
                        else:
                            additional_columns = {'Site': '[TSUM](https://www.tsum.ru/)', 'Type': 'Restock'}


                        sizes = api.Sizes(
                                    api.SIZE_TYPES[''],
                                    [
                                        api.Size(
                                            size.current_value['size_vendor_name'] + ' US',
                                            f'http://static.sellars.cf/'
                                            f'links?site=tsum&id={size.current_value["item_id"]}'
                                        ) for size in Path.parse_str('$.skuList.*').match(element.current_value)
                                        if size.current_value['availabilityInStock'] is True
                                    ][1:]
                                )

                        result.append(
                            IRelease(
                                'https://www.tsum.ru/product/' +
                                element.current_value['slug'] + f'?shash={sizes.hash().hex()}',
                                'tsum',
                                name,
                                element.current_value['photos'][0]['middle'],
                                '',
                                api.Price(
                                    api.CURRENCIES['RUB'],
                                    float(element.current_value['skuList'][0]['price_original'])
                                ),
                                sizes,
                                [
                                    FooterItem(
                                        'StockX',
                                        'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20').
                                        replace('"', '').replace('\n', '').replace(' ', '').replace('Кроссовки', '')
                                    ),
                                    FooterItem(
                                        'Urban QT',
                                        f'https://autofill.cc/api/v1/qt?storeId=tsum&monitor='
                                        f'{"https://www.tsum.ru/" + element.current_value["slug"]}'
                                    ),
                                    FooterItem('Cart', 'https://www.tsum.ru/cart'),
                                    FooterItem('Login', 'https://www.tsum.ru/login')
                                ],
                                additional_columns
                            )
                        )
                except JSONDecodeError as e:
                    raise e

            if isinstance(content, api.CSmart):
                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False
                result.append(content)
            else:
                result.extend([self.catalog, api.MAlert('Script is awake', self.name)])

        return result
