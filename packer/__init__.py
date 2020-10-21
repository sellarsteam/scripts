from datetime import datetime, timedelta, timezone
from typing import List, Union

from requests import exceptions
from ujson import loads
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
        self.link: str = 'https://packershoes.com/collections/footwear/products.json?limit=100&_=pf&pf_t_footwear' \
                         '=footwear%3Asneakers&pf_v_brand=NIKE&pf_v_brand=ADIDAS '

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 6, 10))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=1, microsecond=500000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            ok, response = self.provider.request(self.link, headers={'user-agent': generate_user_agent()}, proxy=True)

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 900.)]

            if response.status_code == 430 or response.status_code == 520:
                return [api.CInterval(self.name, 900.)]

            try:
                json = loads(response.content)

            except ValueError:
                return [api.CInterval(self.name, 900)]

            for element in json['products']:
                title = element['title']
                handle = element['handle']
                variants = element['variants']
                image = element['images'][0]['src'] if len(element['images']) != 0 \
                    else 'http://via.placeholder.com/300/2A2A2A/FFF?text=No+image'
                sizes_data = [element for element in element['variants']]

                del element

                title_ = title.lower()

                if Keywords.check(handle) or Keywords.check(title_):

                    target = api.Target('https://packershoes.com/products/' + handle, self.name, 0)

                    if HashStorage.check_target(target.hash()):

                        sizes = [
                            api.Size(
                                str(size['option1']) + f' US',
                                f'https://www.packershoes.com/cart/{size["id"]}:1')
                            for size in sizes_data if size["available"] is True
                        ]

                        if not sizes:
                            continue

                        try:
                            price = api.Price(
                                api.CURRENCIES['USD'],
                                float(variants[0]['price'])
                            )
                        except (KeyError, IndexError):
                            price = api.Price(api.CURRENCIES['USD'], 0.)

                        HashStorage.add_target(target.hash())
                        result.append(IRelease(
                            target.name,
                            'shopify-filtered',
                            title,
                            image,
                            '',
                            price,
                            api.Sizes(api.SIZE_TYPES[''], sizes),
                            [
                                FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                           title.replace(' ', '%20')),
                                FooterItem('Cart', 'https://packershoes.com/cart'),
                                FooterItem('Login', 'https://packershoes.com/account/login')
                            ],
                            {'Site': '[Packer Shoes](https://packershoes.com)'}
                        ))

            if result or (isinstance(content, api.CSmart) and content.expired):
                if isinstance(content, api.CSmart()):
                    content.gen.time = self.time_gen()
                    content.expired = False
                    result.append(content)
                else:
                    result.append(self.catalog())

        return result
