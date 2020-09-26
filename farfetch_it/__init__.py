from datetime import datetime, timedelta, timezone
from typing import List, Union

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://www.farfetch.com/it/plpslice/listing-api/products-facets?view=180&designer=4968477' \
                         '|12264703 '
        self.user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=1, microsecond=250000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []

        if mode == 0:
            json_response = self.provider.request(self.link, headers={'user-agent': self.user_agent}).json()

            for item in json_response['listingItems']['items']:

                if item['priceInfo']['isOnSale'] is True or item['priceInfo']['finalPrice'] < 250:
                    link = f'https://www.farfetch.com{item["url"]}'

                    if HashStorage.check_target(api.Target(link, self.name, 0).hash()):

                        product_id = item['id']
                        name = f"{item['brand']['name']} {item['shortDescription']}"
                        price = api.Price(api.CURRENCIES['EUR'], float(item['priceInfo']['finalPrice']),
                                          float(item['priceInfo']['initialPrice']))
                        image = item['images']['cutOut']
                        sizes = api.Sizes(api.SIZE_TYPES[''], [api.Size(f'TOTAL STOCK: [{item["stockTotal"]}]')])
                        stockx_link = f'https://stockx.com/search/sneakers?s={item["shortDescription"]}'

                        result.append(
                            IRelease(
                                link,
                                'farfetch',
                                name,
                                image,
                                '',
                                price,
                                sizes,
                                [
                                    FooterItem('StockX', stockx_link.replace(' ', '%20')),
                                    FooterItem('Cart', 'https://www.farfetch.com/it/checkout/basket.aspx'),
                                    FooterItem('MBot QT', f'https://mbot.app/ff/variant/{product_id}'),
                                    FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                ],
                                {'Region': 'Italy 🇮🇹'}
                            )
                        )

                        HashStorage.add_target(api.Target(link, self.name, 0).hash())

            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result