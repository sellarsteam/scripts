from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from requests import exceptions

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem, \
    IAnnounce
from source.cache import HashStorage
from source.library import SubProvider, ScriptStorage, Keywords
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://www.itkkit.ru/catalog/footwear/sneakers/?FILTER=247748'
        self.headers = {
            'Host': 'www.itkkit.ru',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://www.itkkit.ru',
            'Connection': 'keep-alive',
        }

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=0, microsecond=500000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            ok, response = self.provider.request(url=self.link, headers=self.headers, proxy=True)

            if not ok:

                if isinstance(response, exceptions.Timeout):

                    return [api.CInterval(self.name, 300)]

                else:

                    raise result

            for element in etree.HTML(response.text).xpath(
                    '//a[@class="catalog-item catalog-item--compact link link--primary"]'):

                parts_of_name = element.xpath('div[@class="catalog-item__title"]/div')
                name = f'{parts_of_name[0].text} {parts_of_name[1].text.split("] ")[-1]}'

                if Keywords.check(name.lower()):

                    try:
                        if HashStorage.check_target(
                                api.Target('https://www.itkkit.ru' + element.get('href'), self.name, 0).hash()):

                            sizes_data = element.xpath('div[@class="catalog-item__img-wrapper"]'
                                                       '/div[@class="catalog-item__img-hover"]/div')[0].text

                            image = 'https://www.itkkit.ru' + \
                                    element.xpath('div[@class="catalog-item__img-wrapper"]'
                                                  '/div[@class="catalog-item__img-list"]'
                                                  '/div[@class="catalog-item__img catalog-item__img--active "]'
                                                  '/picture/img')[0].get('data-src')

                            price = api.Price(api.CURRENCIES['EUR'],
                                              float(element.xpath('div[@class="catalog-item__price"]/div/div'
                                                                  '/span/span')[0].text.replace(' ', '')
                                                    .replace('\t', '').replace('\n', '').split('.')[0]))

                            if 'Sold' in sizes_data:
                                continue

                            if 'Soon' in sizes_data:
                                result.append(
                                    IAnnounce(
                                        'https://www.itkkit.ru' + element.get('href'),
                                        'itkkit',
                                        name,
                                        image,
                                        '',
                                        price,
                                        api.Sizes(api.SIZE_TYPES[''], []),
                                        [
                                            FooterItem('Cart', 'https://www.itkkit.ru/checkout/'),
                                            FooterItem('QT Urban',
                                                       'https://autofill.cc/api/v1/qt?storeId=itkkit&monitor='
                                                       + 'https://www.itkkit.ru' + element.get('href'))
                                        ],
                                        {'Site': '[ITK Kit](https://www.itkkit.ru)'}
                                    )
                                )
                                continue

                            sizes = api.Sizes(
                                api.SIZE_TYPES[''],
                                [
                                    api.Size(size.replace(' US', '') + ' US')
                                    for size in sizes_data.split(' US ')
                                ]
                            )

                            HashStorage.add_target(
                                api.Target('https://www.itkkit.ru' + element.get('href'), self.name, 0).hash())

                            result.append(
                                IRelease(
                                    'https://www.itkkit.ru' + element.get('href'),
                                    'itkkit',
                                    name,
                                    image,
                                    '',
                                    price,
                                    sizes,
                                    [
                                        FooterItem('Cart', 'https://www.itkkit.ru/checkout/'),
                                        FooterItem('QT Urban', 'https://autofill.cc/api/v1/qt?storeId=itkkit&monitor='
                                                   + 'https://www.itkkit.ru' + element.get('href'))
                                    ],
                                    {'Site': '[ITK Kit](https://www.itkkit.ru)'}
                                )
                            )

                    except etree.XMLSyntaxError:
                        raise etree.XMLSyntaxError('XMLDecodeEroor')

            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
