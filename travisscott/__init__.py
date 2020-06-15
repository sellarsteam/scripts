from datetime import datetime, timedelta, timezone
from json import loads, JSONDecodeError
from typing import List, Union

from jsonpath2 import Path
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://shop.travisscott.com/products.json?limit=1000'
        self.interval: int = 1

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, self.time_gen(), 2, exp=30.)

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
            try:
                products = self.provider.get(self.link, headers={'user-agent': generate_user_agent()}, proxy=True)
                if products == '{"products":[]}':
                    result.append(api.CInterval(self.name, 0, 600.))
                    return result

                for element in Path.parse_str('$.products.*').match(loads(products)):
                    target = api.Target('https://shop.travisscott.com/products/' + element.
                                        current_value['handle'], self.name, 0)
                    if HashStorage.check_target(target.hash()):
                        sizes_data = Path.parse_str('$.product.variants.*').match(loads(
                            self.provider.get(target.name + '/count.json',
                                              headers={'user-agent': generate_user_agent()},
                                              proxy=True)))
                        sizes = [api.Size(str(size.current_value['title']).upper() +
                                          f' [{size.current_value["inventory_quantity"]}]',
                                          f'https://shop.travisscott.com/cart/{size.current_value["id"]}:1')
                                 for size in sizes_data if int(size.current_value["inventory_quantity"]) > 0]
                        try:
                            price = api.Price(
                                api.CURRENCIES['USD'],
                                float(element.current_value['variants'][0]['price'])
                            )
                        except KeyError:
                            price = api.Price(
                                api.CURRENCIES['USD'],
                                float(0)
                            )
                        except IndexError:
                            price = api.Price(
                                api.CURRENCIES['USD'],
                                float(0)
                            )
                        name = element.current_value['title']
                        HashStorage.add_target(target.hash())
                        result.append(IRelease(
                            target.name,
                            'travis-scott',
                            name,
                                image,
                            '',
                            price,
                            api.Sizes(api.SIZE_TYPES[''], sizes),
                            [
                                FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                           name.replace(' ', '%20')),
                                FooterItem('Cart', 'https://shop.travisscott.com/cart'),
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            {'Site': 'Travis Scott'}
                        ))
            except JSONDecodeError:
                raise JSONDecodeError('Exception JSONDecodeError')
            if result or content.expired:
                content.timestamp = self.time_gen()
                content.expired = False

            result.append(content)
        return result