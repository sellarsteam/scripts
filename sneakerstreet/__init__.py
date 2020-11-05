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
        self.link: str = 'https://sneaker-street.ru/sneakers?bfilter=brand[adidas,jordan,nike]/gender[men]'
        self.user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

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

            counter = 0

            ok, resp = self.provider.request(self.link, headers={'user-agent': self.user_agent})

            if not ok:
                if isinstance(resp, exceptions.Timeout):
                    raise Exception('Timeout')
                else:
                    raise result

            lxml_resp = etree.HTML(resp.text)
            catalog = [element for element in lxml_resp.xpath('//div[@class="pli"]')]

            if not catalog:
                raise Exception('Catalog is empty')

            for item in catalog:
                link = item.xpath('a[@class="pli__main"]')[0].get('href')

                counter = counter + 1
                name = item.xpath('a[@class="pli__main"]/span[@class="pli__main__brand"]')[0].text + ' ' + \
                       item.xpath('a[@class="pli__main"]/span[@class="pli__main__name"]')[0].text

                if Keywords.check(name.lower()):

                    if HashStorage.check_target(
                            api.Target(link, self.name, 0).hash()):
                        HashStorage.add_target(
                            api.Target(link, self.name, 0).hash())
                        additional_columns = {'Site': '[Sneaker Street](https://sneaker-street.ru/)'}
                    else:
                        additional_columns = {'Site': '[Sneaker Street](https://sneaker-street.ru/)',
                                              'Type': 'Restock'}

                    image = item.xpath('a/span[@class="pli__main__image"]/img')[0].get('src')

                    try:
                        price = api.Price(api.CURRENCIES['RUB'],
                                          float(item.xpath('a/span[@class="pli__main__price"]')[0]
                                                .text.replace(' ', '').replace('\n', '').replace('₽', '')))
                    except ValueError:
                        price = api.Price(api.CURRENCIES['RUB'],
                                          float(item.xpath('a/span[@class="pli__main__price"]'
                                                           '/span[@class="pli__main__price__new"]')
                                                [0].text.replace(' ', '').replace('\n', '').replace('₽', '')),
                                          float(item.xpath('a/span[@class="pli__main__price"]'
                                                           '/span[@class="pli__main__price__old"]')
                                                [0].text.replace(' ', '').replace('\n', '').replace('₽', '')))

                    raw_sizes = [api.Size(size.text.replace('\n', ''))
                                 for size in item.xpath('div[@class="pli__options"]/button')]

                    sizes = api.Sizes(api.SIZE_TYPES[''], raw_sizes)

                    stockx_link = f'https://stockx.com/search/sneakers?s={name.replace(" ", "%20")}'

                    result.append(
                        IRelease(
                            link + f'?shash={str(sizes).__hash__()}',
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
                            additional_columns
                        )
                    )

            if isinstance(content, api.CSmart):
                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False
                result.append(content)
            else:
                result.extend([self.catalog, api.MAlert('Script is awake', self.name)])

        return result
