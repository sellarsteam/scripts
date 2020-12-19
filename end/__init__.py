from datetime import datetime, timedelta, timezone
from typing import List, Union

from requests import exceptions
from ujson import loads, dumps

from user_agent import generate_user_agent
from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://ko4w2gbink-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia%20for' \
                         '%20JavaScript%20(3.35.1)%3B%20Browser&x-algolia-application-id=KO4W2GBINK&x-algolia-api-key' \
                         '=dfa5df098f8d677dd2105ece472a44f8 '
        self.post_data = {"requests": [{"indexName": "catalog_products_en",
                                        "params": "analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22us%22%5D"
                                                  "&page=0&facetFilters=%5B%5B%22categories%3AFootwear%22%5D%2C%5B"
                                                  "%22websites_available_at%3A2%22%5D%2C%5B%22brand%3AAdidas%22%2C"
                                                  "%22brand%3ANike%20SB%22%2C%22brand%3ANike%20Jordan%22%2C%22brand"
                                                  "%3ANike%22%5D%5D&filters=&facets=%5B%22*%22%5D&hitsPerPage=120"
                                                  "&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22us%22%5D"
                                                  "&clickAnalytics=true"},
                                       {"indexName": "catalog_products_en",
                                        "params": "analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22us%22%5D"
                                                  "&page=0&facetFilters=%5B%5B%22websites_available_at%3A2%22%5D%2C"
                                                  "%5B%22categories%3AFootwear%22%5D%5D&facets=%5B%22*%22%5D"
                                                  "&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2"
                                                  "%22%2C%22us%22%5D&clickAnalytics=true"},
                                       {"indexName": "catalog_products_en",
                                        "params": "analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22us%22%5D"
                                                  "&page=0&facetFilters=%5B%5B%22websites_available_at%3A2%22%5D%2C"
                                                  "%5B%22brand%3AAdidas%22%2C%22brand%3ANike%20SB%22%2C%22brand"
                                                  "%3ANike%20Jordan%22%2C%22brand%3ANike%22%5D%5D&filters=&facets"
                                                  "=categories&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web"
                                                  "%22%2C%22v2%22%2C%22us%22%5D&analytics=false"},
                                       {"indexName": "catalog_products_en",
                                        "params": "analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22us%22%5D"
                                                  "&page=0&facetFilters=%5B%5B%22categories%3AFootwear%22%5D%2C%5B"
                                                  "%22brand%3AAdidas%22%2C%22brand%3ANike%20SB%22%2C%22brand%3ANike"
                                                  "%20Jordan%22%2C%22brand%3ANike%22%5D%5D&filters=&facets"
                                                  "=websites_available_at&hitsPerPage=120&ruleContexts=%5B%22browse"
                                                  "%22%2C%22web%22%2C%22v2%22%2C%22us%22%5D&analytics=false"},
                                       {"indexName": "catalog_products_en",
                                        "params": "analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22us%22%5D"
                                                  "&page=0&facetFilters=%5B%5B%22categories%3AFootwear%22%5D%2C%5B"
                                                  "%22websites_available_at%3A2%22%5D%5D&filters=&facets=brand"
                                                  "&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2"
                                                  "%22%2C%22us%22%5D&analytics=false"}]}

        self.headers = {
            'Connection': 'keep - alive',
            'Pragma': 'no - cache',
            'Cache-Control': 'no - cache',
            'Content-type': 'application/x-www-form-urlencoded',
            'Host': 'ko4w2gbink - dsn.algolia.net',
            'User-Agent': generate_user_agent(),
            'Accept': 'application / json, text / plain, * / *'

        }

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 6, 10))

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

            data_json = dumps(self.post_data)

            ok, response = self.provider.request(self.link, headers=self.headers, data=data_json, method='post')

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    raise Exception('Timeout')
                else:
                    raise result

            try:
                json = loads(response.text)
            except ValueError:
                return [api.CInterval(self.name, 900.), api.MAlert('Script go to sleep', self.name)]

            catalog = [element for element in json['results'][0]['hits']]

            if not catalog:
                raise Exception('Catalog is empty')

            for element in catalog:

                name = element['name']
                handle = element['url_key'] + '.html'
                skus = element['sku_stock']
                sku_stock = [skus[key] for key in skus if skus[key] != 0]
                available_sizes = element['size']
                image = 'https://media.endclothing.com/media/f_auto,q_auto:eco/prodmedia/media/catalog/product' \
                        + element['small_image']

                try:
                    launch_mode = element['launches_mode']
                    launch_date = element['launches_release_date']

                except (KeyError, IndexError):
                    launch_mode = 0
                    launch_date = 'No launch date'

                try:
                    price = api.Price(
                        api.CURRENCIES['RUB'],
                        float(element['final_price_13'])
                    )
                except (KeyError, IndexError):
                    price = api.Price(api.CURRENCIES['USD'], 0.)

                del element

                if Keywords.check(name.lower()):

                    target = api.Target('https://www.endclothing.com/' + handle, self.name, 0)

                    additional_columns = {'Site': '[END.](https://www.endclothing.com)'}

                    if HashStorage.check_target(target.hash()):
                        HashStorage.add_target(target.hash())
                    else:
                        additional_columns.update({'Type': 'Restock'})

                    if launch_mode == 'countdown':
                        additional_columns.update({'Release Type': f'Countdown ({launch_date})'})

                    sizes = []
                    counter = 0
                    for stock in sku_stock:
                        sizes.append(api.Size(available_sizes[counter] + f' [{stock}]'))
                        counter += 1

                    sizes = api.Sizes(api.SIZE_TYPES[''], sizes)

                    result.append(IRelease(
                        target.name + f'?shash={sizes.hash().hex()}',
                        'end',
                        name,
                        image,
                        '',
                        price,
                        sizes,
                        [
                            FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                       name.replace(' ', '%20')),
                            FooterItem('Cart', 'https://deadstock.ca/cart'),
                            FooterItem('Login', 'https://www.deadstock.ca/account')
                        ],
                        additional_columns
                    )
                    )

            if isinstance(content, api.CSmart):

                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False
            else:
                result.extend([self.catalog, api.MAlert('Script is awake', self.name)])

        return result
