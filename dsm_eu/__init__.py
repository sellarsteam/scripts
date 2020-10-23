from datetime import datetime, timedelta, timezone
from typing import List, Union

from requests import exceptions
from ujson import loads
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://eflash.doverstreetmarket.com/products.json?limit=15'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 6, 10))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=0, microsecond=0, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            ok, response = self.provider.request(self.link, headers={'user-agent': generate_user_agent()}, proxy=True)

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 900.), api.MAlert('Script go to sleep', self.name)]

            if response.status_code == 430 or response.status_code == 520:
                return [api.CInterval(self.name, 900.), api.MAlert('Script go to sleep', self.name)]

            try:
                json = loads(response.content)

            except ValueError:
                json = {'products': []}

            for element in json['products']:
                title = element['title']
                handle = element['handle']
                variants = element['variants']
                image = element['images'][0]['src'] if len(element['images']) != 0 \
                    else 'http://via.placeholder.com/300/2A2A2A/FFF?text=No+image'
                sizes_data = [element for element in element['variants']]

                del element
                target = api.Target('https://eflash.doverstreetmarket.com/products/' + handle, self.name, 0)

                if HashStorage.check_target(target.hash()):

                    sizes = [
                        api.Size(
                            str(size['title']), f'https://eflash.doverstreetmarket.com/cart/{size["id"]}:1')
                        for size in sizes_data if size["available"] is True
                    ]

                    if not sizes:
                        continue

                    try:
                        price = api.Price(
                            api.CURRENCIES['GBP'],
                            float(variants[0]['price'])
                        )
                    except (KeyError, IndexError):
                        price = api.Price(api.CURRENCIES['USD'], 0.)

                    HashStorage.add_target(target.hash())

                    result.append(IRelease(
                        target.name,
                        'doverstreetmarket',
                        title,
                        image,
                        '',
                        price,
                        api.Sizes(api.SIZE_TYPES[''], sizes),
                        [
                            FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' + title.replace(' ', '%20')),
                            FooterItem('Cart', 'https://eflash.doverstreetmarket.com/cart')
                        ],
                        {
                            'Site': '[DSM London](https://eflash.doverstreetmarket.com)',
                            'Location': 'Europe (London)',
                        }
                    ))

            if result or (isinstance(content, api.CSmart) and content.expired):
                if isinstance(content, api.CSmart):
                    content.gen.time = self.time_gen()
                    content.expired = False
                    result.append(content)
                else:
                    result.append(self.catalog())

        return result
