from datetime import datetime, timedelta, timezone
from json import JSONDecodeError
from typing import List, Union

from jsonpath2 import Path
from user_agent import generate_user_agent
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
        self.link: str = 'https://www.solefiness.com/products.json?limit=100'
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

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 2, 30))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=1, microsecond=750000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            response = self.provider.request(self.link, headers={'user-agent': generate_user_agent()}, proxy=True)

            if response.status_code == 430 or response.status_code == 520:
                result.append(api.CInterval(self.name, 600.))
                return result

            try:
                response = response.json()
            except JSONDecodeError:
                raise TypeError('Non JSON response')

            for element in Path.parse_str('$.products.*').match(response):
                title = element.current_value['title']
                handle = element.current_value['handle']
                variants = element.current_value['variants']
                image = element.current_value['images'][0]['src'] if len(element.current_value['images']) != 0 \
                    else 'http://via.placeholder.com/300/2A2A2A/FFF?text=No+image'

                del element

                title_ = title.lower()

                if check_name(handle, self.absolute_keywords, self.positive_keywords, self.negative_keywords) \
                        or check_name(title_, self.absolute_keywords, self.positive_keywords, self.negative_keywords):
                    target = api.Target('https://www.solefiness.com/products/' + handle, self.name, 0)
                    if HashStorage.check_target(target.hash()):
                        sizes_data = Path.parse_str('$.variants.*').match(
                            self.provider.request(target.name + '.js',
                                                  headers={'user-agent': generate_user_agent()},
                                                  proxy=True).json())
                        sizes = [api.Size(str(size.current_value['title']) +
                                          f' [?]',
                                          f'https://www.solefiness.com/cart/{size.current_value["id"]}:1')
                                 for size in sizes_data if size.current_value['available'] is True]
                        if not sizes:
                            HashStorage.add_target(target.hash())
                            continue

                        try:
                            price = api.Price(
                                api.CURRENCIES['AUD'],
                                float(variants[0]['price'])
                            )
                        except (KeyError, IndexError):
                            price = api.Price(
                                api.CURRENCIES['USD'],
                                float(0)
                            )

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
                                FooterItem('Cart', 'https://www.solefiness.com/cart'),
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            {'Site': 'Sole Finess'}
                        ))

            if isinstance(content, api.CSmart):
                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False

            result.append(content)
        return result
