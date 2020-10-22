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
        self.link: str = 'https://oktyabrskateshop.ru/products.json?limit=50'
        self.interval: int = 1

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 6, 10))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=0, microsecond=750000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            ok, resp = self.provider.request(self.link, headers={'user-agent': generate_user_agent()}, proxy=True)

            if not ok:
                if isinstance(resp, exceptions.Timeout):
                    return [api.CInterval(self.name, 900.), api.MAlert('Script go to sleep', self.name)]

            if resp.status_code == 430 or resp.status_code == 520:
                return [api.CInterval(self.name, 900.), api.MAlert('Script go to sleep', self.name)]

            try:
                json = loads(resp.content)

            except ValueError:
                return [api.CInterval(self.name, 900), api.MAlert('Script go to sleep', self.name)]

            for element in Path.parse_str('$.products.*').match(json):
                title = element.current_value['title']
                handle = element.current_value['handle']
                variants = element.current_value['variants']
                image = element.current_value['images'][0]['src'] if len(element.current_value['images']) != 0 \
                    else 'http://via.placeholder.com/300/2A2A2A/FFF?text=No+image'

                del element

                title_ = title.lower()

                if Keywords.check(handle) or Keywords.check(title_):

                    target = api.Target('https://oktyabrskateshop.ru/products/' + handle, self.name, 0)
                    if HashStorage.check_target(target.hash()):

                        ok, resp = self.provider.request(target.name + '.js',
                                                         headers={'user-agent': generate_user_agent()},
                                                         proxy=True)

                        if not ok:
                            if isinstance(resp, exceptions.Timeout):
                                return [api.CInterval(self.name, 900.)]

                        if resp.status_code == 430 or resp.status_code == 520:
                            return [api.CInterval(self.name, 900.)]

                        try:
                            resp = resp.json()
                        except JSONDecodeError:
                            return [api.CInterval(self.name, 900.)]

                        sizes_data = Path.parse_str('$.variants.*').match(resp)
                        sizes = [
                            api.Size(
                                str(size.current_value['option1']),
                                f'https://oktyabrskateshop.ru/cart/{size.current_value["id"]}:1')
                            for size in sizes_data if size.current_value['available'] is True
                        ]

                        if not sizes:
                            HashStorage.add_target(target.hash())
                            continue

                        try:
                            price = api.Price(
                                api.CURRENCIES['RUB'],
                                float(variants[0]['price'])
                            )
                        except (KeyError, IndexError):
                            price = api.Price(api.CURRENCIES['RUB'], 0.)

                        HashStorage.add_target(target.hash())
                        result.append(IRelease(
                            target.name,
                            'octobershop',
                            title,
                            image,
                            '',
                            price,
                            api.Sizes(api.SIZE_TYPES[''], sizes),
                            [
                                FooterItem('Cart', 'https://oktyabrskateshop.ru/cart'),
                                FooterItem('Login', 'https://oktyabrskateshop.ru/account/login?return_url=%2Faccount')
                            ],
                            {'Site': '[Oktyabr Skateshop](https://oktyabrskateshop.ru)'}
                        ))

            if result or (isinstance(content, api.CSmart) and content.expired):
                if isinstance(content, api.CSmart):
                    content.gen.time = self.time_gen()
                    content.expired = False
                    result.append(content)
                else:
                    result.append(self.catalog())
        return result
