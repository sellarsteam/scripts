from datetime import datetime, timedelta, timezone
from time import time
from typing import List, Union

from requests import exceptions
from ujson import loads, dump, dumps

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://www.farfetch.com/ru/plpslice/listing-api/products-facets?view=90&scale=275&designer' \
                         '=4968477|12264703&pagetype=Shopping&gender=Women|Men&pricetype=FullPrice&c-category=136301 '
        self.user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

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

            ok, resp = self.provider.request(self.link, headers={'user-agent': self.user_agent}, proxy=True)

            if not ok:

                if isinstance(resp, exceptions.Timeout):
                    return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]

                else:
                    raise resp

            try:
                json = loads(resp.content)

            except ValueError:
                return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]

            for item in json['listingItems']['items']:

                raw_final_price = float(item['priceInfo']['finalPrice'])
                if raw_final_price < 25000.0:
                    channel = 'farfetch-filtered'
                else:
                    channel = 'farfetch'

                if float(item['priceInfo']['finalPrice']) == float(item['priceInfo']['initialPrice']):
                    price = api.Price(api.CURRENCIES['RUB'], float(item['priceInfo']['finalPrice']))
                else:
                    price = api.Price(api.CURRENCIES['RUB'], float(item['priceInfo']['finalPrice']),
                                      float(item['priceInfo']['initialPrice']))

                link = f'https://www.farfetch.com{item["url"]}$sprice={price.hash().hex()}'

                target = api.Target(link, self.name, 0)

                if HashStorage.check_target(target.hash()):
                    additional_columns = {'Regions': f'[[ES]({link.replace("ru", "es")}) 🇪🇸] | '
                                                     f'[[IT]({link.replace("ru", "it")}) 🇮🇹] | '
                                                     f'[[DE]({link.replace("ru", "de")}) 🇩🇪] | '
                                                     f'[[UK]({link.replace("ru", "uk")}) 🇬🇧]'
                                          }

                    product_id = item['id']
                    name = f"{item['brand']['name']} {item['shortDescription']}"
                    stockx_link = f'https://stockx.com/search/sneakers?s={item["shortDescription"]}'
                    image = item['images']['cutOut']
                    result.append(
                        api.TScheduled(
                            link,
                            self.name,
                            (
                                name, image, product_id, channel, stockx_link, price, additional_columns
                            ),
                            time()
                        )
                    )

        if mode == 1:

            ok, resp = self.provider.request(f'https://www.farfetch.com/ru/sizeguide/sizeinfo?productId='
                                             f'{content.data[2]}', headers={'user-agent': self.user_agent},
                                             proxy=True)
            if not ok:

                if isinstance(resp, exceptions.Timeout):
                    return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]

                else:
                    raise resp

            try:
                json_sizes = loads(resp.content)

            except ValueError:
                return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]
            try:

                sizes = api.Sizes(api.SIZE_TYPES[''], [api.Size(f'{size} UK [{size_data["formattedFinalPrice"]}]')
                                                       for size, size_data in json_sizes.items()
                                                       if size_data['available']])

                result.append(
                    IRelease(
                        content.name,
                        content.data[3],
                        content.data[0],
                        content.data[1],
                        '',
                        content.data[5],
                        sizes,
                        [
                            FooterItem('StockX', content.data[4].replace(' ', '%20')),
                            FooterItem('Cart', 'https://www.farfetch.com/uk/checkout/basket.aspx'),
                            FooterItem('MBot QT', f'https://mbot.app/ff/variant/{content.data[2]}')
                        ],
                        content.data[6]
                    )
                )
                target = api.Target(content.name, self.name, 0)

                try:
                    HashStorage.add_target(target.hash())

                except source.cache.UniquenessError:
                    pass

            except AttributeError:
                pass

        if isinstance(content, api.CSmart):
            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False
            result.append(content)
        else:
            result.extend([self.catalog, api.MAlert('Script is awake', self.name)])

        return result
