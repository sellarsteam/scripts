from time import time
from typing import List, Union

import requests
from ujson import loads

import source
from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem, \
    TInterval
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'

    @property
    def catalog(self) -> CatalogType:
        return api.CInterval(self.name, 120000)

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []

        if mode == 0:

            result.append(TInterval('catalog_1', self.name, ['yeezy', 'https://www.farfetch.com/ru/plpslice/listing-api/products-facets?view=90&scale=282&gender=Women|Men&pagetype=Shopping&designer=4968477&c-category=137174&page=2&pagetype=Search&pricetype=FullPrice'], 5))
            result.append(TInterval('catalog_2', self.name, ['yeezy', 'https://www.farfetch.com/ru/plpslice/listing-api/products-facets?view=90&scale=282&gender=Women|Men&pagetype=Shopping&designer=4968477&c-category=137174&pagetype=Search&pricetype=FullPrice'], 5))
            result.append(TInterval('catalog_3', self.name, ['nike_x_off-white', 'https://www.farfetch.com/ru/plpslice/listing-api/products-facets?view=90&scale=282&gender=Women|Men&pagetype=Shopping&pricetype=FullPrice&designer=12264703&c-category=135968&pagetype=Search&pricetype=FullPrice'], 5))
            result.append(TInterval('catalog_4', self.name, ['jordan', 'https://www.farfetch.com/ru/plpslice/listing-api/products-facets?view=200&scale=282&gender=Women|Men&pagetype=Shopping&designer=6687111&c-category=137174&page=2&pagetype=Search&pricetype=FullPrice'], 5))
            result.append(TInterval('catalog_5', self.name, ['jordan', 'https://www.farfetch.com/ru/plpslice/listing-api/products-facets?view=200&scale=282&gender=Women|Men&pagetype=Shopping&designer=6687111&c-category=137174&page=1&pagetype=Search&pricetype=FullPrice'], 5))
            result.append(TInterval('catalog_6', self.name, ['jordan', 'https://www.farfetch.com/ru/plpslice/listing-api/products-facets?view=200&scale=282&gender=Women|Men&pagetype=Shopping&designer=6687111&c-category=137174&page=3&pagetype=Search&pricetype=FullPrice'], 5))
            result.append(TInterval('catalog_7', self.name, ['jordan', 'https://www.farfetch.com/ru/plpslice/listing-api/products-facets?view=200&scale=282&gender=Women|Men&pagetype=Shopping&designer=6687111&c-category=137174&page=4&pagetype=Search&pricetype=FullPrice'], 5))
            result.append(TInterval('catalog_8', self.name, ['dunk', 'https://www.farfetch.com/ru/plpslice/listing-api/products-facets?view=90&scale=282&q=dunk&gender=Men|Women&pagetype=Search&pricetype=FullPrice&designer=1664'], 5))
            result.append(TInterval('catalog_9', self.name, ['dunk', 'https://www.farfetch.com/ru/plpslice/listing-api/products-facets?view=90&scale=282&q=dunk&gender=Men|Women&pagetype=Search&pricetype=FullPrice&page=2&designer=1664'], 5))

            result.append(content)
            return result
        if mode == 1:
            if 'catalog' in content.name:

                resp = requests.get(content.data[1], headers={'user-agent': self.user_agent})

                try:
                    json = loads(resp.content)

                except ValueError:
                    return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]

                for item in json['listingItems']['items']:
                    availability = False
                    try:
                        if item['type'] == 'CriteoProduct':
                            pass
                        else:
                            availability = True
                    except KeyError:
                        availability = True

                    if availability:
                        price_limit = .0
                        if content.data[0] == 'jordan' or content.data[0] == 'dunk':
                            price_limit = 15000.0
                        else:
                            price_limit = 25000.0
                        raw_final_price = float(item['priceInfo']['finalPrice'])
                        if raw_final_price < price_limit:
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
                            name = f"{item['brand']['name']} {item['shortDescription']}"

                            if content.data[0] != 'jordan' or content.data[0] != 'dunk' or self.kw.check(name.lower()):
                                additional_columns = {'Regions': f'[[ES]({link.replace("ru", "es")}) 🇪🇸] | '
                                                                 f'[[IT]({link.replace("ru", "it")}) 🇮🇹] | '
                                                                 f'[[DE]({link.replace("ru", "de")}) 🇩🇪] | '
                                                                 f'[[UK]({link.replace("ru", "uk")}) 🇬🇧]'
                                                      }

                                product_id = item['id']
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
                                try:
                                    HashStorage.add_target(target.hash())

                                except source.cache.UniquenessError:
                                    pass
                result.append(content)

            else:

                resp = requests.get(f'https://www.farfetch.com/ru/sizeguide/sizeinfo?productId='
                                                 f'{content.data[2]}', headers={'user-agent': self.user_agent})

                try:
                    json_sizes = loads(resp.content)

                except ValueError:
                    return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]
                try:
                    raw_sizes = []
                    min_price = 900000000
                    for size, size_data in json_sizes.items():
                        if size_data['available']:

                            if float(size_data["formattedFinalPrice"].replace('₽', '').replace('\xa0', '')) < min_price:
                                min_price = float(size_data["formattedFinalPrice"].replace('₽', '').replace('\xa0', ''))

                    for size, size_data in json_sizes.items():
                        if size_data['available']:

                            if min_price > 25000:
                                if float(size_data["formattedFinalPrice"].replace('₽', '').replace('\xa0', '')) == min_price:
                                    raw_sizes.append(api.Size(f'**{size} US [{size_data["formattedFinalPrice"]}]**'))
                                else:
                                    raw_sizes.append(api.Size(f'{size} US [{size_data["formattedFinalPrice"]}]'))
                            else:

                                if float(size_data["formattedFinalPrice"].replace('₽', '').replace('\xa0', '')) < 25000:
                                    raw_sizes.append(api.Size(f'**{size} US [{size_data["formattedFinalPrice"]}]**'))
                                else:
                                    raw_sizes.append(api.Size(f'{size} US [{size_data["formattedFinalPrice"]}]'))

                    sizes = api.Sizes(api.SIZE_TYPES[''], raw_sizes)
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
                except AttributeError:
                    pass

        return result
