from datetime import datetime, timedelta, timezone
from typing import List, Union

from user_agent import generate_user_agent
from json import loads, JSONDecodeError

from jsonpath2 import Path
from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://api.tsum.ru/catalog/search/?q=yeezy'
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 2, 10))

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
            for element in Path.parse_str('$.*').match(self.provider.request(
                    self.link, headers={'user-agent': self.user_agent, 'accept': 'application/json'}).json()):
                try:
                    if HashStorage.check_target \
                                (api.Target('https://www.tsum.ru/' + element.current_value['slug'],
                                            self.name, 0).hash()):
                        name = element.current_value['title']
                        result.append(
                            IRelease(
                                'https://www.tsum.ru/' + element.current_value['slug'],
                                'tsum',
                                name,
                                element.current_value['photos'][0]['middle'],
                                '',
                                api.Price(
                                    api.CURRENCIES['RUB'],
                                    float(element.current_value['skuList'][0]['price_original'])
                                ),
                                api.Sizes(api.SIZE_TYPES[''], [api.Size(size.current_value['size_vendor_name'] + ' US',
                                                                        f'http://static.sellars.cf/links/tsum?id='
                                                                        f'{size.current_value["item_id"]}')
                                                               for size in Path.parse_str('$.skuList.*')
                                          .match(element.current_value)
                                                               if size.current_value['availabilityInStock']]
                                [1:]),
                                [
                                    FooterItem(
                                        'StockX',
                                        'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20').
                                        replace('"', '').replace('\n', '').replace(' ', '').replace('Кроссовки', '')
                                    ),
                                    FooterItem('Cart', 'https://www.tsum.ru/cart'),
                                    FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                ],
                                {'Site': 'TSUM'}
                            )
                        )
                except JSONDecodeError as e:
                    raise e
            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
