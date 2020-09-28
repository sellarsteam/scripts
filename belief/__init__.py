from datetime import datetime, timedelta, timezone
from typing import List, Union

from scripts.keywords_finding import check_name
import yaml
from requests import exceptions, get
from json import JSONDecodeError

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem, CInterval
from source.cache import HashStorage
from source.library import SubProvider
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://beliefmoscow.com/collection/frontpage.json?order=&q=nike'
        self.interval: int = 1

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
        self.user_agent = 'Mozilla/5.0 (compatible; YandexAccessibilityBot/3.0; +http://yandex.com/bots)'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

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
            result.append(content)

            ok, response = self.provider.request(self.link, headers={'user-agent': self.user_agent})

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return result
                else:
                    raise result

            try:
                page_content = response.json()

            except JSONDecodeError:

                result.append(api.CInterval(self.name, 300))
                return result

            for product in page_content['products']:

                if check_name(product['permalink'], self.absolute_keywords, self.positive_keywords,
                              self.negative_keywords) \
                        or check_name(product['title'].lower(),
                                      self.absolute_keywords, self.positive_keywords, self.negative_keywords):

                    target = api.Target(f'https://beliefmoscow.com{product["url"]}', self.name, 0)

                    if HashStorage.check_target(target.hash()):

                        url = f'https://beliefmoscow.com{product["url"]}'
                        name = product['title']
                        price = api.Price(
                            api.CURRENCIES['RUB'],
                            float(product['variants'][0]['price'])

                        )
                        image = product['images'][0]['medium_url'] if len(product['images']) != 0 \
                            else 'http://via.placeholder.com/300/2A2A2A/FFF?text=No+image'

                        sizes = api.Sizes(api.SIZE_TYPES[''],
                                          [api.Size(f"{size['title'].split(' /')[0]} [{size['quantity']}]",
                                                    f"http://static.sellars.cf/links?site=belief&id={size['id']}")
                                           for size in product['variants'] if size['quantity'] > 0])

                        if len(product['variants']) == 0:
                            continue

                        HashStorage.add_target(target.hash())

                        result.append(
                            IRelease(
                                url,
                                'belief',
                                name,
                                image,
                                '',
                                price,
                                sizes,
                                [
                                    FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                               name.replace(' ', '%20')),
                                    FooterItem('Cart', 'https://beliefmoscow.com/cart'),
                                    FooterItem('Urban QT', f'https://autofill.cc/api/v1/qt?storeId=beliefmoscow&monitor={url}'),
                                    FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                ],
                                {'Site': 'Belief Moscow'}
                            )
                        )

                    else:

                        url = f'https://beliefmoscow.com{product["url"]}'
                        name = product['title']
                        price = api.Price(
                            api.CURRENCIES['RUB'],
                            float(product['variants'][0]['price'])

                        )
                        image = product['images'][0]['medium_url'] if len(product['images']) != 0 \
                            else 'http://via.placeholder.com/300/2A2A2A/FFF?text=No+image'

                        if len(product['variants']) == 0:
                            HashStorage.remove_item(
                                IRelease(
                                    url,
                                    'belief',
                                    name,
                                    image,
                                    '',
                                    price,
                                    api.Sizes(api.SIZE_TYPES[''], []),
                                    [
                                        FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                                   name.replace(' ', '%20')),
                                        FooterItem('Cart', 'https://beliefmoscow.com/cart'),
                                        FooterItem('Urban QT', f'https://autofill.cc/api/v1/qt?storeId=beliefmoscow&monitor={url}'),
                                        FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                    ],
                                    {'Site': 'Belief Moscow'}
                                ).hash()
                            )

            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result


if __name__ == '__main__':
    link: str = 'https://beliefmoscow.com/collection/frontpage.json?order=&q=nike'
    user_agent = 'Mozilla/5.0 (compatible; YandexAccessibilityBot/3.0; +http://yandex.com/bots)'
    while True:
        print(get(link, headers={'user-agent': user_agent}).json())