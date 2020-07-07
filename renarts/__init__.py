from datetime import datetime, timedelta, timezone
from json import JSONDecodeError
from typing import List, Union

from jsonpath2 import Path
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://renarts.com/products.json?limit=100'
        self.interval: float = 1

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 2, 30))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=1, microsecond=0, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            response = self.provider.request(self.link,
                                             headers={'user-agent': generate_user_agent()}, proxy=True, type='get')

            if response.status_code == 430 or response.status_code == 520:
                result.append(api.CInterval(self.name, 600.))
                return result

            try:
                response = response.json()
            except JSONDecodeError:
                raise TypeError('Non JSON response')

            for element in Path.parse_str('$.products.*').match(response):
                id_ = element.current_value['id']
                title = element.current_value['title']
                handle = element.current_value['handle']
                variants = element.current_value['variants']
                image = element.current_value['images'][0]['src']

                del element

                title_ = title.lower()

                if any(i in title_ for i in ('yeezy', 'air', 'sacai', 'retro', 'dunk')):
                    target = api.Target('https://renarts.com/products/' + handle, self.name, 0)
                    if HashStorage.check_target(target.hash()):
                        sizes_data = Path.parse_str('$.product.variants.*').match(
                            self.provider.request(target.name + '/count.json',
                                                  headers={'user-agent': generate_user_agent()},
                                                  proxy=True, type='get').json())
                        sizes = [api.Size(str(size.current_value['option1']) + ' US'
                                                                               f' [{size.current_value["inventory_quantity"]}]',
                                          f'https://renarts.com/cart/{size.current_value["id"]}:1')
                                 for size in sizes_data if int(size.current_value["inventory_quantity"]) > 0]

                        if not sizes:
                            HashStorage.add_target(target.hash())
                            continue

                        try:
                            price = api.Price(
                                api.CURRENCIES['USD'],
                                float(variants[0]['price'])
                            )
                        except (KeyError, IndexError):
                            price = api.Price(api.CURRENCIES['USD'], 0.)

                        HashStorage.add_target(target.hash())
                        result.append(IRelease(
                            target.name,
                            'shopify-filtered',
                            title,
                            image,
                            '',
                            price,
                            api.Sizes(api.SIZE_TYPES[''], sizes),
                            [
                                FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                           title.replace(' ', '%20')),
                                FooterItem('Cart', 'https://renarts.com/cart'),
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            {'Site': 'Renarts'}
                        ))

            if result or content.expired:
                content.timestamp = self.time_gen()
                content.expired = False

            result.append(content)
        return result
