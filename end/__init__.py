from datetime import datetime, timedelta, timezone
from typing import List, Union

import pycurl
from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.link: str = 'https://ko4w2gbink-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia for JavaScri' \
                         'pt (3.35.1); Browser&x-algolia-application-id=KO4W2GBINK&x-algolia-api-key=dfa5df098f8d677d' \
                         'd2105ece472a44f8'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.endclothing.com',
            'Connection': 'keep-alive',
            'Referer': 'https://www.endclothing.com/ru'
        }
        self.last_yeezy_data = '{"requests":[{"indexName":"catalog_products_en",' \
                               '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                               '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B' \
                               '%5B%22categories%3ALatest%20%2F%20Latest%20Sneakers%22%5D%2C%5B' \
                               '%22websites_available_at%3A13%22%5D%2C%5B%22brand%3AYEEZY%22%5D%5D&filters=&facets' \
                               '=%5B%22*%22%5D&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C' \
                               '%22ru%22%2C%22RU%22%5D&clickAnalytics=true"},{"indexName":"catalog_products_en",' \
                               '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                               '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B' \
                               '%5B%22websites_available_at%3A13%22%5D%2C%5B%22categories%3ALatest%20%2F%20Latest' \
                               '%20Sneakers%22%5D%5D&facets=%5B%22*%22%5D&hitsPerPage=120&ruleContexts=%5B%22browse' \
                               '%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&clickAnalytics=true"},' \
                               '{"indexName":"catalog_products_en",' \
                               '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                               '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B' \
                               '%5B%22websites_available_at%3A13%22%5D%2C%5B%22brand%3AYEEZY%22%5D%5D&filters=&facets' \
                               '=categories&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C' \
                               '%22ru%22%2C%22RU%22%5D&analytics=false"},{"indexName":"catalog_products_en",' \
                               '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                               '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B' \
                               '%5B%22categories%3ALatest%20%2F%20Latest%20Sneakers%22%5D%2C%5B%22brand%3AYEEZY%22%5D' \
                               '%5D&filters=&facets=websites_available_at&hitsPerPage=120&ruleContexts=%5B%22browse' \
                               '%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&analytics=false"},' \
                               '{"indexName":"catalog_products_en",' \
                               '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                               '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B' \
                               '%5B%22categories%3ALatest%20%2F%20Latest%20Sneakers%22%5D%2C%5B' \
                               '%22websites_available_at%3A13%22%5D%5D&filters=&facets=brand&hitsPerPage=120' \
                               '&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D' \
                               '&analytics=false"}]} '
        self.yeezy_data = '{"requests":[{"indexName":"catalog_products_en_search",' \
                          '"params":"query=yeezy&query=yeezy&userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead' \
                          '&analyticsTags=%5B%22search%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%2C%22%22%5D' \
                          '&page=0&facetFilters=%5B%5B%22websites_available_at%3A13%22%5D%5D&filters=&facets=%5B%22' \
                          '*%22%5D&hitsPerPage=120&ruleContexts=%5B%22search%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C' \
                          '%22RU%22%2C%22%22%5D&clickAnalytics=true"},{"indexName":"catalog_products_en_search",' \
                          '"params":"query=yeezy&query=yeezy&userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead' \
                          '&analyticsTags=%5B%22search%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%2C%22%22%5D' \
                          '&page=0&facetFilters=%5B%5B%22websites_available_at%3A13%22%5D%5D&facets=%5B%22*%22%5D' \
                          '&hitsPerPage=120&ruleContexts=%5B%22search%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22' \
                          '%2C%22%22%5D&clickAnalytics=true"},{"indexName":"catalog_products_en_search",' \
                          '"params":"query=yeezy&query=yeezy&userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead' \
                          '&analyticsTags=%5B%22search%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%2C%22%22%5D' \
                          '&page=0&facetFilters=%5B%5D&filters=&facets=websites_available_at&hitsPerPage=120' \
                          '&ruleContexts=%5B%22search%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%2C%22%22%5D' \
                          '&analytics=false"}]} '
        self.jordan_data = '{"requests":[{"indexName":"catalog_products_en","params":"analytic' \
                           'sTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D&page=0&facetF' \
                           'ilters=%5B%5B%22categories%3AFootwear%22%5D%2C%5B%22websites_available_at' \
                           '%3A13%22%5D%2C%5B%22brand%3ANike%20Jordan%22%5D%5D&filters=&facets=%5B%22*%2' \
                           '2%5D&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D' \
                           '&clickAnalytics=true"},{"indexName":"catalog_products_en",' \
                           '"params":"analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D&page=0' \
                           '&facetFilters=%5B%5B%22websites_available_at%3A13%22%5D%2C%5B%22categories%3AFootwear%22' \
                           '%5D%5D&facets=%5B%22*%22%5D&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C' \
                           '%22v2%22%2C%22ru%22%5D&clickAnalytics=true"},{"indexName":"catalog_products_en",' \
                           '"params":"analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D&page=0' \
                           '&facetFilters=%5B%5B%22websites_available_at%3A13%22%5D%2C%5B%22brand%3ANike%20Jordan%22' \
                           '%5D%5D&filters=&facets=categories&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web' \
                           '%22%2C%22v2%22%2C%22ru%22%5D&analytics=false"},{"indexName":"catalog_products_en",' \
                           '"params":"analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D&page=0' \
                           '&facetFilters=%5B%5B%22categories%3AFootwear%22%5D%2C%5B%22brand%3ANike%20Jordan%22%5D%5D' \
                           '&filters=&facets=websites_available_at&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C' \
                           '%22web%22%2C%22v2%22%2C%22ru%22%5D&analytics=false"},{"indexName":"catalog_products_en",' \
                           '"params":"analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D&page=0' \
                           '&facetFilters=%5B%5B%22categories%3AFootwear%22%5D%2C%5B%22websites_available_at%3A13%22' \
                           '%5D%5D&filters=&facets=brand&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C' \
                           '%22v2%22%2C%22ru%22%5D&analytics=false"}]}'
        self.nike_data = '{"requests":[{"indexName":"catalog_products_en",' \
                         '"params":"analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D&page=0' \
                         '&facetFilters=%5B%5B%22categories%3AFootwear%22%5D%2C%5B%22websites_available_at%3A13%22%5D' \
                         '%2C%5B%22brand%3ANike%20SB%22%2C%22brand%3ANike%22%5D%5D&filters=&facets=%5B%22*%22%5D' \
                         '&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D' \
                         '&clickAnalytics=true"},{"indexName":"catalog_products_en",' \
                         '"params":"analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D&page=0' \
                         '&facetFilters=%5B%5B%22websites_available_at%3A13%22%5D%2C%5B%22categories%3AFootwear%22%5D' \
                         '%5D&facets=%5B%22*%22%5D&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2' \
                         '%22%2C%22ru%22%5D&clickAnalytics=true"},{"indexName":"catalog_products_en",' \
                         '"params":"analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D&page=0' \
                         '&facetFilters=%5B%5B%22websites_available_at%3A13%22%5D%2C%5B%22brand%3ANike%20SB%22%2C' \
                         '%22brand%3ANike%22%5D%5D&filters=&facets=categories&hitsPerPage=120&ruleContexts=%5B' \
                         '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D&analytics=false"},' \
                         '{"indexName":"catalog_products_en",' \
                         '"params":"analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D&page=0' \
                         '&facetFilters=%5B%5B%22categories%3AFootwear%22%5D%2C%5B%22brand%3ANike%20SB%22%2C%22brand' \
                         '%3ANike%22%5D%5D&filters=&facets=websites_available_at&hitsPerPage=120&ruleContexts=%5B' \
                         '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D&analytics=false"},' \
                         '{"indexName":"catalog_products_en",' \
                         '"params":"analyticsTags=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%5D&page=0' \
                         '&facetFilters=%5B%5B%22categories%3AFootwear%22%5D%2C%5B%22websites_available_at%3A13%22%5D' \
                         '%5D&filters=&facets=brand&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2' \
                         '%22%2C%22ru%22%5D&analytics=false"}]} '
        self.last_nike = '{"requests":[{"indexName":"catalog_products_en",' \
                         '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                         '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B%5B' \
                         '%22categories%3ALatest%20%2F%20Latest%20Sneakers%22%5D%2C%5B%22websites_available_at%3A13' \
                         '%22%5D%2C%5B%22brand%3ANike%22%2C%22brand%3ANike%20SB%22%5D%5D&filters=&facets=%5B%22*%22' \
                         '%5D&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU' \
                         '%22%5D&clickAnalytics=true"},{"indexName":"catalog_products_en",' \
                         '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                         '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B%5B' \
                         '%22websites_available_at%3A13%22%5D%2C%5B%22categories%3ALatest%20%2F%20Latest%20Sneakers' \
                         '%22%5D%5D&facets=%5B%22*%22%5D&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C' \
                         '%22v2%22%2C%22ru%22%2C%22RU%22%5D&clickAnalytics=true"},{"indexName":"catalog_products_en",' \
                         '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                         '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B%5B' \
                         '%22websites_available_at%3A13%22%5D%2C%5B%22brand%3ANike%22%2C%22brand%3ANike%20SB%22%5D%5D' \
                         '&filters=&facets=categories&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C' \
                         '%22v2%22%2C%22ru%22%2C%22RU%22%5D&analytics=false"},{"indexName":"catalog_products_en",' \
                         '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                         '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B%5B' \
                         '%22categories%3ALatest%20%2F%20Latest%20Sneakers%22%5D%2C%5B%22brand%3ANike%22%2C%22brand' \
                         '%3ANike%20SB%22%5D%5D&filters=&facets=websites_available_at&hitsPerPage=120&ruleContexts' \
                         '=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&analytics=false"},' \
                         '{"indexName":"catalog_products_en",' \
                         '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                         '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B%5B' \
                         '%22categories%3ALatest%20%2F%20Latest%20Sneakers%22%5D%2C%5B%22websites_available_at%3A13' \
                         '%22%5D%5D&filters=&facets=brand&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C' \
                         '%22v2%22%2C%22ru%22%2C%22RU%22%5D&analytics=false"}]} '
        self.last_jordan = '{"requests":[{"indexName":"catalog_products_en",' \
                           '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                           '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B%5B' \
                           '%22categories%3ALatest%20%2F%20Latest%20Sneakers%22%5D%2C%5B%22websites_available_at%3A13' \
                           '%22%5D%2C%5B%22brand%3ANike%20Jordan%22%5D%5D&filters=&facets=%5B%22*%22%5D&hitsPerPage' \
                           '=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D' \
                           '&clickAnalytics=true"},{"indexName":"catalog_products_en",' \
                           '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                           '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B%5B' \
                           '%22websites_available_at%3A13%22%5D%2C%5B%22categories%3ALatest%20%2F%20Latest%20Sneakers' \
                           '%22%5D%5D&facets=%5B%22*%22%5D&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22' \
                           '%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&clickAnalytics=true"},' \
                           '{"indexName":"catalog_products_en",' \
                           '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                           '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B%5B' \
                           '%22websites_available_at%3A13%22%5D%2C%5B%22brand%3ANike%20Jordan%22%5D%5D&filters' \
                           '=&facets=categories&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22%2C%22v2%22' \
                           '%2C%22ru%22%2C%22RU%22%5D&analytics=false"},{"indexName":"catalog_products_en",' \
                           '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                           '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B%5B' \
                           '%22categories%3ALatest%20%2F%20Latest%20Sneakers%22%5D%2C%5B%22brand%3ANike%20Jordan%22' \
                           '%5D%5D&filters=&facets=websites_available_at&hitsPerPage=120&ruleContexts=%5B%22browse%22' \
                           '%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&analytics=false"},' \
                           '{"indexName":"catalog_products_en",' \
                           '"params":"userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                           '%22browse%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&page=0&facetFilters=%5B%5B' \
                           '%22categories%3ALatest%20%2F%20Latest%20Sneakers%22%5D%2C%5B%22websites_available_at%3A13' \
                           '%22%5D%5D&filters=&facets=brand&hitsPerPage=120&ruleContexts=%5B%22browse%22%2C%22web%22' \
                           '%2C%22v2%22%2C%22ru%22%2C%22RU%22%5D&analytics=false"}]} '
        self.dunk_data = '{"requests":[{"indexName":"catalog_products_en_search","params":"query=nike ' \
                         'dunk&query=nike&userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead&analyticsTags=%5B' \
                         '%22search%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%2C%22%22%5D&page=0&facetFilters' \
                         '=%5B%5B%22websites_available_at%3A13%22%5D%2C%5B%22department%3ASneakers%22%5D%5D&filters' \
                         '=&facets=%5B%22*%22%5D&hitsPerPage=120&ruleContexts=%5B%22search%22%2C%22web%22%2C%22v2%22' \
                         '%2C%22ru%22%2C%22RU%22%2C%22%22%5D&clickAnalytics=true"},' \
                         '{"indexName":"catalog_products_en_search",' \
                         '"params":"query=nike&query=nike&userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead' \
                         '&analyticsTags=%5B%22search%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%2C%22%22%5D' \
                         '&page=0&facetFilters=%5B%5B%22websites_available_at%3A13%22%5D%5D&facets=%5B%22*%22%5D' \
                         '&hitsPerPage=120&ruleContexts=%5B%22search%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22' \
                         '%2C%22%22%5D&clickAnalytics=true"},{"indexName":"catalog_products_en_search",' \
                         '"params":"query=nike&query=nike&userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead' \
                         '&analyticsTags=%5B%22search%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%2C%22%22%5D' \
                         '&page=0&facetFilters=%5B%5B%22department%3ASneakers%22%5D%5D&filters=&facets' \
                         '=websites_available_at&hitsPerPage=120&ruleContexts=%5B%22search%22%2C%22web%22%2C%22v2%22' \
                         '%2C%22ru%22%2C%22RU%22%2C%22%22%5D&analytics=false"},' \
                         '{"indexName":"catalog_products_en_search",' \
                         '"params":"query=nike&query=nike&userToken=anonymous-9857eb1c-132e-4792-8703-ebf597c8cead' \
                         '&analyticsTags=%5B%22search%22%2C%22web%22%2C%22v2%22%2C%22ru%22%2C%22RU%22%2C%22%22%5D' \
                         '&page=0&facetFilters=%5B%5B%22websites_available_at%3A13%22%5D%5D&filters=&facets' \
                         '=department&hitsPerPage=120&ruleContexts=%5B%22search%22%2C%22web%22%2C%22v2%22%2C%22ru%22' \
                         '%2C%22RU%22%2C%22%22%5D&analytics=false"}]} '

    @property
    def catalog(self) -> api.CatalogType:
        return api.CInterval(self.name, 120)

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
            result.append(api.TInterval('last_yeezy', self.name, [self.last_yeezy_data], 3))
            result.append(api.TInterval('yeezy', self.name, [self.yeezy_data], 3))
            result.append(api.TInterval('jordan', self.name, [self.jordan_data], 3))
            result.append(api.TInterval('yeezy', self.name, [self.yeezy_data], 3))
            result.append(api.TInterval('nike', self.name, [self.nike_data], 3))
            result.append(api.TInterval('last_nike', self.name, [self.last_nike], 3))
            result.append(api.TInterval('last_jordan', self.name, [self.last_jordan], 3))
            result.append(api.TInterval('dunk', self.name, [self.dunk_data], 3))
        if mode == 1:
            ok, response = self.provider.request(self.link, headers=self.headers, data=content.data[0], method='POST')

            if not ok:
                if response.args[0] == pycurl.E_OPERATION_TIMEOUTED:
                    result.append(content)
                    return result
                else:
                    raise response

            try:
                json = response.json()
            except ValueError:
                return [content, api.MAlert('Script crashed', self.name)]

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

                if self.kw.check(name + ' ' + handle):
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
                            FooterItem('Cart', 'https://www.endclothing.com/ru/checkout'),
                            FooterItem('Login', 'https://www.endclothing.com/ru/customer')
                        ],
                        additional_columns
                    )
                    )
                else:
                    result.append(IRelease(
                        target.name,
                        'aio-nf',
                        name,
                        image,
                        '',
                        price,
                        sizes,
                        [
                            FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                       name.replace(' ', '%20')),
                            FooterItem('Cart', 'https://www.endclothing.com/ru/checkout'),
                            FooterItem('Login', 'https://www.endclothing.com/ru/customer')
                        ],
                        additional_columns
                    )
                    )
        result.append(content)
        return result
