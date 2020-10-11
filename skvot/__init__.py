from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from requests import exceptions
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, ScriptStorage, Keywords
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://www.skvot.com/catalog/shoes/gumshoes;brand:nike,adidias'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'
        }
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=1, microsecond=0, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:

            ok, response = self.provider.request(url=self.link, headers=self.headers)

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.)]
                else:
                    raise response

            for element in etree.HTML(response.text).xpath(
                    '//a[@class="top-item top-item--catalog"]'):
                if Keywords.check(element.get('href').lower()):

                    try:
                        if HashStorage.check_target(
                                api.Target('https://www.skvot.com' + element.get('href'), self.name, 0).hash()):

                            ok, response = self.provider.request('https://www.skvot.com' + element.get('href'),
                                                                 headers={'user-agent': self.user_agent})

                            if not ok:
                                if isinstance(response, exceptions.Timeout):
                                    return [api.CInterval(self.name, 600.)]
                                else:
                                    raise response

                            page_content = etree.HTML(response.text)

                            sizes = api.Sizes(
                                api.SIZE_TYPES[''], [api.Size(size.text + ' US') for size in
                                                     page_content.xpath('//label[@class="product-size__label"]')]
                            )

                            if not sizes:
                                HashStorage.add_target(
                                    api.Target('https://www.skvot.com' + element.get('href'), self.name, 0).hash())
                                continue

                            name = page_content.xpath('//h1[@class="page-head__title"]')[0].text

                            image = page_content.xpath('//div[@class="product-preview__slider-slide"]')[0].get('href')

                            old_price_content = page_content.xpath('//div[@class="product-price__price-old"]')

                            if old_price_content:
                                old_price = old_price_content[0].text.replace('₽', '').replace(' ', '')
                                price = api.Price(
                                    api.CURRENCIES['RUB'],
                                    float(
                                        page_content.xpath('//div[@class="product-price__price-new"]')[0].text.replace(
                                            '₽', '').replace(' ', '')),
                                    float(old_price)
                                )
                            else:
                                price = api.Price(
                                    api.CURRENCIES['RUB'],
                                    float(
                                        page_content.xpath('//div[@class="product-price__price-new"]')[0].text.replace(
                                            '₽', '').replace(' ', ''))
                                )

                            HashStorage.add_target(
                                api.Target('https://www.skvot.com' + element.get('href'), self.name, 0).hash())
                            result.append(
                                IRelease(
                                    'https://www.skvot.com' + element.get('href'),
                                    'skvot',
                                    name,
                                    image,
                                    '',
                                    price,
                                    sizes,
                                    [
                                        FooterItem('Cart', 'https://www.skvot.com/cart'),
                                        FooterItem('Login', 'https://www.skvot.com/')
                                    ],
                                    {'Site': '[Skvot](https://www.skvot.com)'}
                                )
                            )
                    except etree.XMLSyntaxError:
                        raise etree.XMLSyntaxError('XMLDecodeEroor')
            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
