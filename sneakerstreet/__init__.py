from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from requests import exceptions

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://sneaker-street.ru/krossovki/?sort=p.date_added&order=DESC'
        self.user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=3, microsecond=0, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:

            counter = 0

            ok, resp = self.provider.request(self.link, headers={'user-agent': self.user_agent})

            if not ok:
                if isinstance(resp, exceptions.Timeout):
                    raise Exception('Timeout')
                else:
                    raise result

            lxml_resp = etree.HTML(resp.text)
            catalog = [element for element in lxml_resp.xpath('//div[@class="main_cont_block_block"]')]

            for item in catalog:
                link = item.xpath('a[@rel="external"]')[0].get('href')

                counter = counter + 1

                if Keywords.check(link.split('/')[-1].lower().replace('-', ' ')):

                    if HashStorage.check_target(api.Target(link, self.name, 0).hash()):
                        name_data = item.xpath('a/div')
                        name = name_data[1].text + name_data[2].text
                        image = 'https://sneaker-street.ru/' + item.xpath('a/div/img')[0].get('src')

                        price = api.Price(api.CURRENCIES['RUB'],
                                          float(item.xpath(f'//div[@class="main_cont_block_block_b_price "]')[counter - 1].text
                                                .replace('₽', '').replace(' ', '')))

                        sizes = api.Sizes(api.SIZE_TYPES[''],
                                          [api.Size(size.text)
                                           for size in item.xpath('//div[@class="block_product__size"]')
                                           [counter - 1].xpath('div/span')])
                        stockx_link = f'https://stockx.com/search/sneakers?s={name.replace(" ", "%20")}'

                        result.append(
                            IRelease(
                                link,
                                'sneakerstreet',
                                name,
                                image,
                                '',
                                price,
                                sizes,
                                [
                                    FooterItem('StockX', stockx_link),
                                    FooterItem('Cart', 'https://sneaker-street.ru/checkout/')
                                ],
                                {'Site': '[Sneaker Street](https://sneaker-street.ru/)'}
                            )
                        )
            if result or (isinstance(content, api.CSmart) and content.expired):
                if isinstance(content, api.CSmart):
                    content.gen.time = self.time_gen()
                    content.expired = False
                    result.append(content)
                else:
                    result.append(self.catalog())

        return result
