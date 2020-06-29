from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from user_agent import generate_user_agent
from requests import get
from json import loads, JSONDecodeError

from jsonpath2 import Path
from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://api.tsum.ru/catalog/search/?q=yeezy'
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, self.time_gen(), 21, 5, 1.2)

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
            for element in Path.parse_str('$.*').match(loads(self.provider.get(self.link,
                                                                               headers={
                                                                                   'user-agent': self.user_agent}))):
                try:
                    if HashStorage.check_target \
                                (api.Target('https://www.tsum.ru/' + element.current_value['slug']
                                , self.name, 0).hash()):
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
                content.timestamp = self.time_gen()
                content.expired = False

            result.append(content)
        return result


if __name__ == '__main__':
    print(get('https://api.tsum.ru/catalog/search/?q=yeezy', headers={
        'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'}).text)
