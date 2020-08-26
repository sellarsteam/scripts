from datetime import datetime, timedelta, timezone
from typing import List, Union

import yaml
from scripts.keywords_finding import check_name

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://api.retailrocket.net/api/2.0/recommendation/popular/' \
                         '552ccef36636b41010072dc3/?&categoryIds=26,10&categoryPaths=' \
                         'new&session=5ea424867c84cf0001e5d423&pvid=638364803722894&isDebug=false&format=json'

        raw = yaml.safe_load(open('./scripts/keywords.yaml'))

        if isinstance(raw, dict):
            if 'absolute' in raw and isinstance(raw['absolute'], list) \
                    and 'positive' in raw and isinstance(raw['positive'], list) \
                    and 'negative' in raw and isinstance(raw['negative'], list):
                self.absolute_keywords = raw['absolute']
                self.positive_keywords = raw['positive']
                self.negative_keywords = raw['negative']
            else:
                raise TypeError('Keywords must be list')
        else:
            raise TypeError('Types of keywords must be in dict')
        self.user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 6, 10))

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
            json_response = self.provider.request(self.link, headers={'user-agent': self.user_agent}).json()

            for item in json_response:

                if check_name(item['Name'].lower(), self.absolute_keywords,
                              self.positive_keywords, self.negative_keywords):

                    url = item['Url']

                    if HashStorage.check_target(api.Target(url, self.name, 0).hash()):
                        name = item['Name']
                        image = item['PictureUrl'].replace(' ', '%20')

                        if item['OldPrice'] == 0:
                            price = api.Price(api.CURRENCIES['RUB'], float(item['Price']))
                        else:
                            price = api.Price(api.CURRENCIES['RUB'], float(item['Price']), float(item['OldPrice']))

                        sizes = api.Sizes(api.SIZE_TYPES[''], [api.Size(f'{size} US')
                                                               for size in item['Size'].split(';')])
                        stockx_link = f'https://stockx.com/search/sneakers?s={name.replace(" ", "%20")}'

                        result.append(
                            IRelease(
                                url,
                                'basketshop',
                                name,
                                image,
                                '',
                                price,
                                sizes,
                                [
                                    FooterItem('StockX', stockx_link),
                                    FooterItem('Cart', 'https://www.basketshop.ru/catalog/basket/'),
                                    FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                ],
                                {'Site': 'Basketshop (StreetBall)'}
                            )
                        )

            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
