from datetime import datetime, timedelta, timezone
from json import JSONDecodeError, dumps
from typing import List, Union

from lxml import etree
from requests import exceptions

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, ScriptStorage, Keywords
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.catalog_link: str = 'https://street-beat.ru/cat/ajax.php'
        self.data = 'SECTION_CODE%5B%5D=krossovki&GENDER%5B%5D=man&BRAND%5B%5D=nike&BRAND%5B%5D=jordan&BRAND%5B%5D=' \
                    'adidas-originals&PRODUCT_STATUS%5B%5D=new&action=get_full_catalog&folder=cat '

        self.headers = {
            'Host': 'street-beat.ru',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
            'Accept': 'text/html, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Length': '170',
            'Origin': 'https://street-beat.ru',
            'Connection': 'keep-alive',
            'Referer': 'https://street-beat.ru/cat/man/krossovki/nike;jordan;adidas-originals/new/',
            'Cookie': 'BITRIX_SM_SALE_UID=777636887; __exponea_etc__=78d10e7f-86f7-11ea-b47f-aab19ae2307c; '
                      'tmr_reqNum=541; tmr_lvid=fb11c3f7ad7147e376f8a66043996c52; tmr_lvidTS=1584766415938; '
                      '_ga=GA1.2.661256707.1587820803; _gcl_au=1.1.775106293.1587820804; '
                      'adspire_uid=AS.861116527.1587820804; _ym_uid=1584766417183513667; _ym_d=1587820804; '
                      '_fbp=fb.1.1587820804889.1932629938; '
                      'cto_bundle=QEUtUl80TjNMTUpySURsUnRPSmdaTkhMYjQ5QnJFM1VhbHphU2d0S2paR2hvd1dnWnFHdFpSREx6djlzaW40c'
                      'nlWYkI0dnd4NzZ0U0NJWVBnMWRRWWc1eHZCMVN6eEp3bU1yeUNZQVlHUXkwVzR6cWVRMU94TEtjdDd4MWlFUEFEZm5tTndl'
                      'M25HVk5l TnRHajUlMkJhQkFLY3k0dyUzRCUzRA; ssaid=ebf74ff0-6b2f-11ea-8146-575fe9f7467a; ipp_uid2=6j'
                      'WsBowbpEAQY07X/TtLIpiSKHEec0Z7j3BuFFw==; ipp_uid1=1598802699533; ipp_uid=1598802699533/6jWsBowbp'
                      'EAQY07X/TtLIpiSKHEec0Z7j3BuFFw==; rerf=AAAAAF94PR4EImG+AxGgAg==; user_city=%D0%9C%D0%BE%D1%81%D0'
                      '%BA%D0%B2%D0%B0; user_usee=a%3A9%3A%7Bi%3A0%3Bs%3A7%3A%222646022%22%3Bi%3A1%3Bs%3A7%3A%222646727'
                      '%22%3Bi%3A2%3Bs%3A7%3A%222732838%22%3Bi%3A3%3Bs%3A7%3A%222646854%22%3Bi%3A4%3Bs%3A7%3A%222646916'
                      '%22%3Bi%3A5%3Bs%3A7%3A%222771155%22%3Bi%3A6%3Bs%3A7%3A%222712367%22%3Bi%3A7%3Bs%3A7%3A%222667143'
                      '%22%3Bi%3A8%3Bs%3A7%3A%%22%3B%7D; ipp_key=v1602773099240/v3394bd400b5e53a13cfc65163aeca6afa04ab'
                      '3/0j8UEvuInmjdfxAVQthrIQ==; PHPSESSID=SUTIQXKXJkEoi6Xyy6bA7UiRNcu'
                      'vY2Sa; mainpagetype=man; __tld__=null '
        }

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

            ok, response = self.provider.request(self.catalog_link, headers=self.headers, data=dumps(self.data),
                                                 method='post')

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.)]
                else:
                    raise response

            lxml_catalog = etree.HTML(response.text)

            catalog = [item for item in lxml_catalog.xpath('//div[@class="grid-row grid-row--flex"]/div/div')]

            if len(catalog) == 0:
                raise Exception('Catalog is empty')

            for item in catalog:

                name = item.xpath('a[@class="link link--no-color catalog-item__title ddl_product_link"]/span')[0].text
                link = 'https://street-beat.ru' + \
                       item.xpath('a[@class="link link--no-color catalog-item__title ddl_product_link"]')[0].get('href')

                if Keywords.check(name.lower()):

                    try:
                        if HashStorage.check_target(api.Target(link, self.name, 0).hash()):
                            price = api.Price(api.CURRENCIES['RUB'],
                                              float(item.xpath('div[@class="price__wrapper"]/div/span/div')
                                                    [0].text.replace('\xa0', '')))

                            sizes = api.Sizes(api.SIZE_TYPES[''],
                                              [api.Size(
                                                  size_data.text.replace(" ", "").replace("\n", "") + ' US',
                                                  f'https://static.sellars.cf/links?site=streetbeat-mobile&id='
                                                  f'{size_data.get("data-product-id")}')
                                                  for size_data in item.xpath('div[@class="catalog-item__block--hover"]'
                                                                              '/div[@class="catalog-item__size'
                                                                              '"]/noindex '
                                                                              '/form/div/div/label/span/a')])

                            image = item.xpath('a[@class="link catalog-item__img-wrapper ddl_product_link"]'
                                               '/picture[@class="catalog-item__picture catalog-item__'
                                               'picture--has-hover"]/source')[0].get('srcset').split(' 1x')[0]

                            result.append(
                                IRelease(
                                    link,
                                    'streetbeat',
                                    name,
                                    image,
                                    '',
                                    price,
                                    sizes,
                                    [
                                        FooterItem('Cart', 'https://street-beat.ru/cart'),
                                        FooterItem('Urban QT',
                                                   f'https://autofill.cc/api/v1/qt?storeId=streetbeat&monitor={link}')
                                    ],
                                    {'Site': '[Street-Beat](https://street-beat.ru)'}
                                )
                            )

                    except JSONDecodeError:
                        raise Exception('JSONDecodeError')
            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
