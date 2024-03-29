from datetime import datetime, timedelta, timezone
from json import dumps
from typing import List, Union

from lxml import etree
from pycurl_requests import exceptions

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem, \
    IAnnounce
from source.cache import HashStorage
from user_agent import generate_user_agent
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage

SIZES = ["4 US", "4.5 US", "5 US", "5.5 US", "6 US", "6.5 US", "7 US", "7.5 US", "8 US", "8.5 US", "9 US", "9.5 US",
         "10 US", "10.5 US", "11 US", "11.5 US", "12 US", "12.5 US", "13 US", "13.5 US", "14 US", "14.5 US",
         "15 US", "15.5 US", "16 US", "16.5 US", "17 US", "17.5 US", "18.5 US", "19 US"]


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.link: str = 'https://www.itkkit.ru/catalog/footwear/sneakers/?FILTER=255348'

        self.headers = {
            'Host': 'www.itkkit.ru',
            'User-Agent': generate_user_agent(),
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://www.itkkit.ru',
            'Connection': 'keep-alive',
        }

        self.data = {"Form data": {"FILTER[PROP][CML2_MANUFACTURER][]": ["152261", "144643", "53371"],
                                   "FILTER[SECTION][]": "347", "FILTER[PRICE][MIN]": "1200",
                                   "FILTER[PRICE][MAX]": "65000", "money_man": ""}}

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
            ok, response = self.provider.request(url=self.link, headers=self.headers, proxy=True,
                                                 data=dumps(self.data), method='post')

            if not ok:

                if isinstance(response, exceptions.Timeout):

                    return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]

                else:

                    raise result

            catalog = [element for element in etree.HTML(response.text).xpath(
                '//a[@class="catalog-item catalog-item--compact link link--primary"]')]

            if not catalog:
                return [api.CInterval(self.name, 500), api.MAlert('Script go to sleep (Empty Catalog)', self.name)]

            for element in catalog:

                parts_of_name = element.xpath('div[@class="catalog-item__title"]/div')
                name = f'{parts_of_name[0].text} {parts_of_name[1].text.split("] ")[-1]}'

                if self.kw.check(name.lower()):
                    id = int(element.get('href').split('/')[3].split('_')[0])
                    try:
                        if HashStorage.check_target(
                                api.Target('https://www.itkkit.ru' + element.get('href'), self.name, 0).hash()):
                            HashStorage.add_target(
                                api.Target('https://www.itkkit.ru' + element.get('href'), self.name, 0).hash())
                            additional_columns = {'Site': '[ITKKit](https://www.itkkit.ru)'}
                        else:
                            additional_columns = {'Site': '[ITKKit](https://www.itkkit.ru)',
                                                  'Type': 'Restock'}

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
                                    {'Site': '[ITKKit](https://www.itkkit.ru)'}
                                )
                            )
                            continue
                        sizes = []
                        for size in sizes_data.split(' US '):
                            size_text = size.replace(' US', '').replace(',', '.') + ' US'
                            try:
                                num = SIZES.index(size_text) + 1
                                sizes.append(api.Size(size_text, f'http://static.sellars.cf/links?site=itkkit&id={int(id) + num}'))
                            except IndexError:
                                sizes.append(api.Size(size_text))

                        sizes = api.Sizes(api.SIZE_TYPES[''], sizes)

                        result.append(
                            IRelease(
                                'https://www.itkkit.ru' + element.get('href') + f'?shash={sizes.hash().hex()}',
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
                                additional_columns
                            )
                        )

                    except etree.XMLSyntaxError:
                        raise etree.XMLSyntaxError('XMLDecodeEroor')

            if isinstance(content, api.CSmart):
                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False
                result.append(content)
            else:
                result.extend([self.catalog, api.MAlert('Script is awake', self.name)])

        return result
