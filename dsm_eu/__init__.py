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
        self.link: str = 'https://eflash.doverstreetmarket.com/products.json?limit=15'
        self.interval: int = 1

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 2, 30))

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
            response = self.provider.request(self.link, headers={'user-agent': generate_user_agent()}, proxy=True)

            if response.status_code == 430 or response.status_code == 520:
                result.append(api.CInterval(self.name, 60.))
                return result

            try:
                response = response.json()
            except JSONDecodeError:
                raise TypeError('Non JSON response')
            for element in Path.parse_str('$.products.*').match(response):
                title = element.current_value['title']
                handle = element.current_value['handle']
                variants = element.current_value['variants']
                image = element.current_value['images'][0]['src']

                del element

                title_ = title.lower()

                target = api.Target('https://eflash.doverstreetmarket.com/products/' + handle, self.name, 0)
                if HashStorage.check_target(target.hash()):
                    sizes = [api.Size(str(size['title']) +
                                      f' [?]',
                                      f'https://eflash.doverstreetmarket.com/cart/{size["id"]}:1')
                             for size in variants]
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
                            FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                       title.replace(' ', '%20')),
                            FooterItem('Cart', 'https://eflash.doverstreetmarket.com/cart'),
                            FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                        ],
                        {'Location': 'Europe (London)'}
                    ))

            if result or content.expired:
                content.timestamp = self.time_gen()
                content.expired = False

            result.append(content)
        return result
