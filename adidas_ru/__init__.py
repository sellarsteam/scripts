from lxml import etree

from datetime import datetime
from json import loads, JSONDecodeError
from time import time
from typing import List, Union

from source import api
from source.api import CURRENCIES, SIZE_TYPES, CatalogType, TargetType, RestockTargetType, TargetEndType, ItemType, \
    Price, Sizes, Size, IRelease, IAnnounce
from source.cache import HashStorage
from source.logger import Logger
from source.tools import ExponentialSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider):
        super().__init__(name, log, provider)
        self.catalog_url = 'https://www.adidas.ru/yeezy'
        self.availability_link = 'https://www.adidas.ru/api/products/sku/availability'
        self.data_link = 'https://www.adidas.ru/api/products/sku'
        self.user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'


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
            response_json = loads(etree.HTML(self.provider.request(self.catalog_url,
                                                                   headers={'user-agent': self.user_agent}).text)
                                  .xpath('//script[@type="text/javascript"]')[0].text.replace('window.ENV = ', ''))

            result.append(content)

            result.extend([
                api.TInterval(i, self.name, 0, 0) for i in response_json['productData']
            ])

            return result

        elif mode == 1:

            try:
                try:
                    item_json = self.provider.request(
                        self.data_link.replace('sku', content.name),
                        headers={'user-agent': self.user_agent}
                    ).json()
                except JSONDecodeError:
                    self.log.error(f'Non JSON response: {content.name}')
                    return [api.TEFail(content, f'Bad json\n{content.hash()}')]

                name = item_json['name']
                image = item_json['view_list'][0]['image_url']
                price = Price(CURRENCIES['RUB'], float(item_json['pricing_information']['standard_price']))
                date = datetime.fromisoformat(item_json['attribute_list']['preview_to'].replace('Z', ''))

                if date.timestamp() < time():
                    result.append(IRelease(
                        'https://adidas.ru/yeezy',
                        'adidas-ru',
                        name,
                        image,
                        '',
                        price,
                        Sizes(SIZE_TYPES[''], []),
                        [
                            api.FooterItem('Cart', 'https://www.adidas.ru/cart'),
                            api.FooterItem('Login', 'https://www.adidas.ru/account-login')
                        ]
                        )
                    )
                else:
                    sizes_was_loaded = False

                    try:
                        size_response = self.provider.request(
                            self.availability_link.replace('sku', content.name),
                            headers={'user-agent': self.user_agent}
                        ).json()
                        sizes_was_loaded = size_response['availability_status'] == 'IN_STOCK'
                    except JSONDecodeError:
                        size_response = dict()
                        pass

                    sizes = Sizes(SIZE_TYPES[''], [])

                    if sizes_was_loaded and size_response:
                        sizes = Sizes(SIZE_TYPES[''], [api.Size(f"{size['size']} [{size['availability']}]")
                                                       for size in size_response['variation_list']
                                                       if size['availability_status'] != 'NOT_AVAILABLE'])

                    result.append(IAnnounce(
                        'https://adidas.ru/yeezy',
                        'adidas-ru',
                        name,
                        image,
                        '',
                        price,
                        sizes,
                        [
                            api.FooterItem('Cart', 'https://www.adidas.ru/cart'),
                            api.FooterItem('Login', 'https://www.adidas.ru/account-login')
                        ],
                        {'Date': str(datetime.utcfromtimestamp(date.timestamp() + 21600).strftime('%Y/%m/%d %H:%M'))}
                        )
                    )

                if result:
                    if isinstance(content, api.TSmart):
                        content.gen.time = date.timestamp()
                        result.append(content)
                    else:
                        result.append(
                            api.TSmart(content.name, self.name, 0, ExponentialSmart(date.timestamp(), 100))
                        )

                    return result
                else:
                    HashStorage.add_target(api.TInterval(content.name, self.name, 0, 0.).hash())
                    return [api.TESuccess(content, 'No more products')]
            except JSONDecodeError:
                self.log.error(f'Non JSON response: {content.name}')
                return [api.TEFail(content, f'Bad json\n{content.hash()}')]


