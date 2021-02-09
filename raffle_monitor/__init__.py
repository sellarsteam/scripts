from datetime import datetime
from typing import List, Union

from pycurl_requests import exceptions
from ujson import loads, dumps

from source import api
from source.api import CatalogType, TargetType, RestockTargetType, TargetEndType, ItemType, IRelease, FooterItem
from source.cache import HashStorage
from source.logger import Logger
from source.tools import ScriptStorage

regions = {
    'EU': '🇪🇺', 'IT': '🇮🇹', 'WW': '🇺🇳', 'JP': '🇯🇵', 'US': '🇺🇸', 'DE': '🇩🇪', 'ES': '🇪🇸', 'CA': '🇨🇦',
    'GB': '🇬🇧', 'NZ': '🇳🇿', 'AU': '🇦🇺', 'ZA': '🇿🇦', 'HK': '🇭🇰', 'AE': '🇦🇪', 'KR': '🇰🇷', 'FR': '🇫🇷',
    'PH': '🇵🇭', 'TH': '🇹🇭', 'DK': '🇩🇰', 'BR': '🇧🇷', 'MY': '🇲🇾', 'TR': '🇹🇷', 'SK': '🇸🇰', 'NL': '🇳🇱',
    'CZ': '🇨🇿', 'ID': '🇮🇩', 'RU': '🇷🇺', 'FI': '🇫🇮', 'PL': '🇵🇱', 'CH': '🇨🇭', 'AT': '🇦🇹', 'RO': '🇷🇴',
    'HR': '🇭🇷', 'HU': '🇭🇺', 'BE': '🇧🇪', 'KW': '🇰🇼'
}


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider, storage: ScriptStorage, kw: api.Keywords):
        super().__init__(name, log, provider, storage, kw)
        self.graphql_url = 'https://api.soleretriever.com/graphql/'

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/json',
        }

        self.catalog_query = {  # It's body for post request of catalog with shoes
            "operationName": "Search",
            "variables": {
                "query": "",
                "archived": False,
                "limit": 25,
                "raffleFilters": {
                    "locales": [],
                    "types": []
                }
            },
            "query": "query Search($query: String, $raffleFilters: RaffleFilters, $archived: Boolean, $from: Int, "
                     "$limit: Int) {\n  search(query: $query, raffle: false, raffleFilters: $raffleFilters, "
                     "release: false, archived: $archived, from: $from, limit: $limit) {\n    count\n    products {\n "
                     "     id\n      name\n      reaction\n      brand\n      releaseDate\n      pid\n      "
                     "colorway\n      price\n      stockxSlug\n      imageUrl\n      cloudFrontImageUrl\n      slug\n "
                     "     __typename\n    }\n    __typename\n  }\n}\n "
        }

    @staticmethod
    def target_query(id_: int) -> dict:
        return {  # It's body for post request of raffles for one pair shoes
            "operationName": "RafflesFromProduct",
            "variables": {
                "productId": id_, "limit": 12, "filters": {"locales": [], "types": []}  # product Id it's id of
                # shoes, it's changeable
            },
            "query": "query RafflesFromProduct($productId: Int!, $from: Int, $limit: Int, $filters: RaffleFilters) "
                     "{\n  rafflesFromProduct(productId: $productId, from: $from, limit: $limit, filters: "
                     "$filters) "
                     "{\n    count\n    raffles {\n      id\n      url\n      type\n      isPickup\n      "
                     "hasPostage\n      locale\n      entered\n      startDate\n      endDate\n      "
                     "retailer {\n        name\n        url\n        imageUrl\n        "
                     "cloudFrontImageUrl\n        affiliate\n        mid\n        "
                     "campaign\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"
        }

    @property
    def catalog(self) -> api.CatalogType:
        return api.CInterval(self.name, 120)

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        try:

            if mode == 0:
                result.append(content)

                ok, resp = self.provider.request(self.graphql_url, data=dumps(self.catalog_query),
                                                 headers=self.headers, method='post', proxy=True)

                if not ok:
                    if isinstance(resp, exceptions.Timeout):
                        return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]
                    else:
                        raise result

                catalog_data = loads(resp.content)
                counter = 1
                for item in catalog_data['data']['search']['products']:
                    result.append(api.TInterval(item['id'], self.name,
                                                {'name': item['name'], 'pid': item['pid'], 'price': item['price'],
                                                 'imageUrl': item['imageUrl'], 'slug': item['slug']}, counter))
                    counter += 0.5
                result.append(content)
                return result

            elif mode == 1:
                ok, resp = self.provider.request(self.graphql_url, data=dumps(self.target_query(int(content.name))),
                                                 headers=self.headers, method='post')

                if not ok:
                    if isinstance(resp, exceptions.Timeout):
                        return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]
                    else:
                        raise result

                raffles_data = loads(resp.content)

                for raffle in raffles_data['data']['rafflesFromProduct']['raffles']:
                    target = api.Target(raffle['url'], self.name, 0)

                    if HashStorage.check_target(target.hash()):
                        if 'endDate' in raffle and raffle['endDate']:
                            location = raffle['locale'] + ' ' + (regions[raffle['locale']] if raffle['locale'] in regions else '')

                            end_date = datetime.fromisoformat(raffle['endDate'][:-1])
                            if datetime.now() <= datetime(year=end_date.year, month=end_date.month, day=end_date.day):
                                HashStorage.add_target(target.hash())

                                result.append(
                                    IRelease(
                                        raffle['url'],
                                        'raffles-ru'
                                        if location.split(' ')[0].lower() == 'ru' or location.split(' ')[0].lower() == 'ww'
                                        else f'raffles-{raffle["type"].lower()}',
                                        f'{content.data["name"]}\n[PID: {content.data["pid"]}]',
                                        content.data['imageUrl'],
                                        'You will need to pay for the shipment'
                                        if raffle['hasPostage'] else 'Postage is free',
                                        api.Price(api.CURRENCIES['USD'], float(content.data['price'])),
                                        api.Sizes(api.SIZE_TYPES[''], []),
                                        [FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                                    content.data["pid"].replace(" ", ""))],
                                        {
                                            'Retailer': f'[{raffle["retailer"]["name"]}]'
                                                        f'({raffle["retailer"]["url"]}) {location}',
                                            'Type Of Raffle': raffle['type'],
                                            'End of raffle': str(end_date),
                                            'Slug': content.data['slug']
                                        }

                                    )
                                )
        except Exception:
            result.extend([self.catalog, api.MAlert('Script is crashed', self.name)])

        return result
