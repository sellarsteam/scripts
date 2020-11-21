from datetime import datetime, timedelta, timezone
from typing import List, Union

from requests import exceptions
from ujson import loads
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem, IAnnounce
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://cactusplantfleamarket.com/products.json?limit=100'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

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
                published_date = datetime.fromisoformat(element['published_at'])

                try:
                    price = api.Price(
                        api.CURRENCIES['USD'],
                        float(variants[0]['price'])
                    )
                except (KeyError, IndexError):
                    price = api.Price(api.CURRENCIES['USD'], 0.)

                del element

                title_ = title.lower()

                if Keywords.check(handle) or Keywords.check(title_):

                    target = api.Target('https://cactusplantfleamarket.com/products/' + handle, self.name, 0)

                    if HashStorage.check_target(target.hash()):
                        HashStorage.add_target(target.hash())
                        additional_columns = {'Site': '[Cactus Plant Flea Market](https://cactusplantfleamarket.com)'}
                    else:
                        additional_columns = {'Site': '[Cactus Plant Flea Market](https://cactusplantfleamarket.com)',
                                              'Type': 'Restock'}

                    sizes = [
                        api.Size(
                            str(size['option1']) + f' US',
                            f'https://cactusplantfleamarket.com/cart/{size["id"]}:1')
                        for size in sizes_data if size["available"] is True
                    ]

                    if not sizes:
                        result.append(IAnnounce(
                                target.name + 'f?stype=Announce',
                                'cpfm',
                                title,
                                image,
                                'NO SIZES',
                                price,
                                api.Sizes(api.SIZE_TYPES[''], []),
                                [
                                    FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                               title.replace(' ', '%20')),
                                    FooterItem('Cart', 'https://cactusplantfleamarket.com/cart'),
                                    FooterItem('Login', 'https://cactusplantfleamarket.com/account')
                                ],
                                {'Site': '[Cactus Plant Flea Market](https://cactusplantfleamarket.com)',
                                 'Publish Date': str(published_date)}
                            )
                        )
                        continue

                    sizes = api.Sizes(api.SIZE_TYPES[''], sizes)

                    result.append(IRelease(
                            target.name + f'?shash={sizes.hash().hex()}',
                            'cpfm',
                            title,
                            image,
                            '',
                            price,
                            sizes,
                            [
                                FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                           title.replace(' ', '%20')),
                                FooterItem('Cart', 'https://cactusplantfleamarket.com/cart'),
                                FooterItem('Login', 'https://cactusplantfleamarket.com/account')
                            ],
                            additional_columns,
                            publish_date=published_date.timestamp()
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
