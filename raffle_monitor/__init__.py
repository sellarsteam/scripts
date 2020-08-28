from typing import List, Union

from source import api
from source.api import CatalogType, TargetType, RestockTargetType, TargetEndType, ItemType, IRelease, FooterItem
from source.cache import HashStorage
from source.logger import Logger

from requests import post


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider):
        super().__init__(name, log, provider)
        self.graphql_url = 'https://api.soleretriever.com/graphql/'

        self.shoes = []  # List with shoes data

        self.post_catalog_body = {  # It's body for post request of catalog with shoes
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

        self.post_raffles_body = {  # It's body for post request of raffles for one pair shoes
            "operationName": "RafflesFromProduct",
            "variables": {
                "productId": 0, "limit": 12, "filters": {"locales": [], "types": []}  # product Id it's id of
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

        if mode == 0:
            catalog_data = post(
                self.graphql_url, json=self.post_catalog_body
            ).json()

            for item in catalog_data['data']['search']['products']:
                self.shoes.append({'id': item['id'], 'name': item['name'], 'pid': item['pid'],
                                   'price': item['price'], 'imageUrl': item['imageUrl'], 'slug': item['slug']})

            result.append(content)

            result.extend([
                api.TInterval(shoe['id'], self.name, 0, 30)
                for shoe in self.shoes
            ])

            return result

        elif mode == 1:
            self.post_raffles_body['variables']['productId'] = int(content.name)

            raffles_data = post(
                self.graphql_url, json=self.post_raffles_body
            ).json()

            for raffle in raffles_data['data']['rafflesFromProduct']['raffles']:
                try:
                    end_date = f"{raffle['endDate'].split('T')[0].replace('-', '/')} " \
                               f"{raffle['endDate'].split('T')[-1].split('.')[0]}"
                except AttributeError:
                    end_date = 'No date'

                if True:  # TODO My Shift+Tab Doesn't work and i can't delete tabulation :(

                    url = raffle['url']
                    target = api.Target(url, self.name, 0)

                    if HashStorage.check_target(target.hash()):
                        HashStorage.add_target(target.hash())

                        shoes_data = {}

                        for shoe in self.shoes:
                            if int(shoe['id']) == int(content.name):
                                shoes_data = shoe
                                break

                        name = shoes_data['name']
                        pid = shoes_data['pid']
                        price = api.Price(
                            api.CURRENCIES['USD'],
                            float(shoes_data['price'])
                        )
                        image_url = shoes_data['imageUrl']
                        slug = shoes_data['slug']

                        type_raffle = raffle['type']
                        if raffle['hasPostage']:
                            postage = 'You will need to pay for the shipment'
                        else:
                            postage = 'Postage is free'
                        location = raffle['locale']
                        shop = f'[{raffle["retailer"]["name"]}]({raffle["retailer"]["url"]})'

                        try:
                            end_date = f"{raffle['endDate'].split('T')[0].replace('-', '/')} " \
                                       f"{raffle['endDate'].split('T')[-1].split('.')[0]}"
                        except AttributeError:
                            end_date = 'No date'

                        result.append(
                            IRelease(
                                url,
                                'raffles',
                                f'{name}\n[PID: {pid}]',
                                image_url,
                                postage,
                                price,
                                api.Sizes(api.SIZE_TYPES[''], []),
                                [
                                    FooterItem('StockX', f'https://stockx.com/search/sneakers?s={pid}'),
                                    FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                ],
                                {
                                    'Retailer': shop + f' [{location}]',
                                    'Type Of Raffle': type_raffle,
                                    'End of raffle': end_date
                                }

                            )
                        )
            result.append(content)
            return result