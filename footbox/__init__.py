from datetime import datetime, timedelta, timezone
from json import loads, JSONDecodeError
from typing import List, Union

from lxml import etree
from requests import exceptions
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
        self.catalog_link: str = 'https://www.footboxshop.ru/muzhskoe/krossovki/?filter[marka][0]=Nike&filter[marka][' \
                                 '3]=adidas+Originals '

        self.headers = {'user-agent': generate_user_agent()}

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

            result.append(content)

            ok, response = self.provider.request(self.catalog_link, headers=self.headers)

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]
                else:
                    raise response

            resp_html = etree.HTML(response.text)

            catalog = [element for element in resp_html.xpath('//div[@class="product col-md-4 col-sm-6 col-12"]/a')]
            if len(catalog) == 0:
                raise Exception('Catalog is empty')

            for element in catalog:
                href = element.get('href')

                if Keywords.check(href.split('/')[3], '-'):
                    link = f'https://www.footboxshop.ru{href}'
                    target = api.Target(link, self.name, 0)

                    if HashStorage.check_target(target.hash()):
                        ok, response = self.provider.request(link, headers=self.headers)

                        if not ok:
                            if isinstance(response, exceptions.Timeout):
                                return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]
                            else:
                                raise response

                        element_html = etree.HTML(response.text)

                        price = api.Price(api.CURRENCIES['RUB'],
                                          float(element_html.xpath('//span[@class="item_sale_price mr-3"]')[0].text
                                                .replace('₽', '').replace(' ', '')))
                        image = 'https://www.footboxshop.ru' + \
                                element_html.xpath('//img[@class="img-fluid open-gallery"]')[0].get('src')
                        name = element_html.xpath('//div[@class="item_name"]/h1')[0].text
                        sizes = api.Sizes(api.SIZE_TYPES[''],
                                          [api.Size(size.text)
                                           for size in element_html.xpath('//select[@class="form-control '
                                                                          'custom-select custom-select-lg '
                                                                          'mb-3"]/option') if size]
                                          )
                        result.append(
                            IRelease(
                                link,
                                'footbox',
                                name,
                                image,
                                '',
                                price,
                                sizes,
                                [
                                    FooterItem('Cart', 'https://www.footboxshop.ru/emarket/cart/')
                                ],
                                {'Site': '[FootBox](https://www.footboxshop.ru)'}
                            )
                        )

                        HashStorage.add_target(target.hash())

            if isinstance(content, api.CSmart):
                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False
                result.append(content)
            else:
                result.extend([self.catalog, api.MAlert('Script is awake', self.name)])

        return result
