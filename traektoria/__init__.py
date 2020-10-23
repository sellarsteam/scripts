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
        self.link: str = 'https://www.traektoria.ru/wear/?brand=adidas%7Enike&SORT=ACTIVE_FROM&ORDER=DESC&bxajaxid' \
                         '=26cf383ee40d9f97469772becb6e86ca '
        self.user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 10, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=0, microsecond=750000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:

            ok, resp = self.provider.request(self.link, headers={'user-agent': self.user_agent})

            if not ok:
                if isinstance(resp, exceptions.Timeout):
                    raise Exception('Timeout')
                else:
                    raise result

            lxml_resp = etree.HTML(resp.text)

            for item in lxml_resp.xpath('//a[@class="p_link"]'):

                link = 'https://www.traektoria.ru' + item.get('href')

                if Keywords.check(link.split('/')[4].split('_')[-1], divider='-'):

                    if HashStorage.check_target(api.Target(link, self.name, 0).hash()):

                        ok, resp = self.provider.request(link, headers={'user-agent': self.user_agent})

                        if not ok:
                            if isinstance(resp, exceptions.Timeout):
                                raise Exception('Timeout')
                            else:
                                raise result

                        item_lxml = etree.HTML(resp.text)
                        name = item_lxml.xpath('//meta[@name="keywords"]')[0].get('content')
                        image = item_lxml.xpath('//meta[@property="og:image"]')[0].get('content')
                        price = api.Price(api.CURRENCIES['RUB'],
                                          float(item_lxml.xpath('//meta[@property="og:product:price:amount"]')[0]
                                                .get('content')))
                        sizes = api.Sizes(api.SIZE_TYPES[''],
                                          [api.Size(size.text + ' US')
                                           for size in item_lxml.xpath('//div[@class="choose_size_column"]/span')])

                        stockx_link = f'https://stockx.com/search/sneakers?s={name.replace(" ", "%20")}'

                        HashStorage.add_target(api.Target(link, self.name, 0).hash())

                        result.append(
                            IRelease(
                                link,
                                'traektoria',
                                name,
                                image,
                                '',
                                price,
                                sizes,
                                [
                                    FooterItem('StockX', stockx_link),
                                    FooterItem('Cart', 'https://www.traektoria.ru/cart/'),
                                    FooterItem('Login', 'https://www.traektoria.ru/personal/')
                                ],
                                {'Site': '[Traektoria](https://www.traektoria.ru)'}
                            )
                        )

            if isinstance(content, api.CSmart):
                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False
                result.append(content)
            else:
                result.append(self.catalog())

        return result
