import datetime
from datetime import timezone, timedelta, datetime
from time import time
from typing import List, Union

from requests.exceptions import SSLError
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, IRelease, RestockTargetType, ItemType, TargetEndType, \
    FooterItem
from source.cache import HashStorage
from source.library import SubProvider
from source.tools import ExponentialSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://www.supremenewyork.com/shop.json'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, ExponentialSmart(self.time_gen(), 2, 30))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(days=-((datetime.utcnow().weekday() - 3) % 7), weeks=1)) \
            .replace(hour=10, minute=0, second=0, microsecond=0, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result: list = []

        if mode == 0:
            content.timestamp = self.time_gen()
            response = self.provider.request(self.link, headers={'user-agent': self.user_agent}, proxy=True)

            if response.status_code == 403:
                raise Exception('Site was banned')

            try:
                for c in response.json()['products_and_categories'].values():
                    for e in c:
                        result.append(
                            api.TScheduled(
                                f'https://www.supremenewyork.com/shop/{e["id"]}.json',
                                self.name,
                                (e['name'],
                                 float(e['price_euro']) / 100,
                                 e['category_name']
                                 ),
                                time()
                            )
                        )

            except SSLError:
                raise SSLError('Site is down')
            except (KeyError, AttributeError):
                raise Exception('Wrong scheme')

            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

        elif mode == 1:
            json_data = self.provider.request(
                content.name, headers={'user-agent': self.user_agent}, proxy=True, type='get').json()

            name = content.data[0]

            for style in json_data['styles']:
                if HashStorage.check_item(content.hash()):
                    style_id = style['id']
                    image = f'https:{style["image_url_hi"]}'
                    result.append(
                        IRelease(
                            content.name[:-5],
                            f'supreme-{content.data[2].lower()}',
                            name,
                            image,
                            '',
                            api.Price(api.CURRENCIES['EUR'], float(content.data[1])),
                            api.Sizes(
                                api.SIZE_TYPES[''],
                                [
                                    api.Size(size['name'], f'https://static.sellars.cf/links?site=supreme&style='
                                                           f'{style_id}&size={size["id"]}')
                                    for size in style['sizes']
                                ]
                            ),
                            [
                                FooterItem('StockX', 'https://stockx.com/search?s='
                                           + name.replace(' ', '%20').replace('®', '')),
                                FooterItem('Cart', 'https://www.supremenewyork.com/shop/cart'),
                                FooterItem('Mobile', 'https://www.supremenewyork.com/mobile#products/' +
                                           content.name[:-5].split('/')[-1])
                            ],
                            {'Site': 'Supreme'}
                        )
                    )
            HashStorage.add_target(content.hash())

        result.append(content)
        return result
