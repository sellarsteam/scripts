from datetime import datetime, timedelta, timezone
from typing import List, Union

from pycurl_requests import exceptions
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
        self.link: str = 'https://api.retailrocket.net/api/2.0/recommendation/popular/' \
                         '552ccef36636b41010072dc3/?&categoryIds=26,10&categoryPaths=' \
                         'new&session=5ea424867c84cf0001e5d423&pvid=638364803722894&isDebug=false&format=json'
        self.user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'

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

            ok, resp = self.provider.request(self.link, headers={'user-agent': self.user_agent})

            if not ok:
                if isinstance(resp, exceptions.Timeout):
                    return result
                else:
                    raise result

            try:
                json = loads(resp.content)

            except ValueError:
                return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]

            for item in json:

                if self.kw.check(item['Name'].lower()):

                    url = item['Url']
                    pid = item['ItemId']

                    if HashStorage.check_target(api.Target(url, self.name, 0).hash()):
                        additional_columns = {'Site': '[Basketshop](https://www.basketshop.ru/)'}
                        HashStorage.add_target(api.Target(url, self.name, 0).hash())
                    else:
                        additional_columns = {'Site': '[Basketshop](https://www.basketshop.ru/)', 'Type': 'Restock'}
                    name = item['Name']
                    image = item['PictureUrl'].replace(' ', '%20')

                    price = api.Price(api.CURRENCIES['RUB'], float(item['Price'])) if item['OldPrice'] == 0 \
                        else api.Price(api.CURRENCIES['RUB'], float(item['Price']), float(item['OldPrice']))

                    sizes_data = [api.Size(f'{size} US', f'https://static.sellars.cf/links?site=basketshop&id={pid}&size={size}') for size in item['Size'].split(';')]

                    sizes = api.Sizes(api.SIZE_TYPES[''], sizes_data)

                    result.append(
                        IRelease(
                            url + f'?shash={sizes.hash().hex()}',
                            'basketshop',
                            name,
                            image,
                            '',
                            price,
                            sizes,
                            [
                                FooterItem('Cart', 'https://www.basketshop.ru/catalog/basket/'),
                                FooterItem('Login', 'https://www.basketshop.ru/user/')
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
