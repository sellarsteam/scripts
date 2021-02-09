from datetime import datetime, timedelta, timezone
from json import loads, JSONDecodeError
from time import time
from typing import List, Union

import lxml
from lxml import etree
from pycurl_requests import exceptions
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem, \
    IAnnounce
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.catalog_link: str = 'https://www.revolve.com/content/nav/mobile/donde/search/?api_key=AIzaSyDxhzArAC6px' \
                                 'Ogb0A7HMa5tPWhzJ3hTX2w&app_id=63fda592e3ad03ef6e56377948a1e996&d_id=UI-9B050F7D-03' \
                                 '73-4DDB-BEBE-F2FF26E7E716&filter_factors%5B%5D=referralUrl%3AaHR0cHM6Ly93d3cucmV2b' \
                                 '2x2ZS5jb20vci9pcGFkQXBwL0JyYW5kcy5qc3A/ZD1Xb21lbnMmbj0mcz1jJmM9U2hvZXMmc2M9U25lYWt' \
                                 'lcnMmc3NjPSZzc3NjPSZmdz1mYWxzZSZkZXNpZ25lcj1Kb3JkYW4mZGVzaWduZXI9TmlrZSZmaWx0ZXJzP' \
                                 'WRlc2lnbmVyJnNvcnRCeT1uZXdlc3QmYXBwVmVyc2lvbj0zLjEyLjgmaXBob25lSWQ9RkU0QzQzNUUtMTN' \
                                 'CMy00MzhDLUFGM0UtQkVFRUIwQjgzNEY2JmRldmljZU9TVmVyc2lvbj0xNC4wLjEmZGV2aWNlVHlwZT1pc' \
                                 'GhvbmUmcGFnZVNpemU9MTAwJmNvdW50cnlDb2RlPVJVJnRva2VuPSZjdXJyZW5jeT1SVUImcGFnZU51bT0' \
                                 'x%2CdeviceType%3Aiphone&limit=100&localtime=2021-02-09%2014%3A01%3A29%20%2B0000&m' \
                                 'ain_category=Women&offset=0&types%5B%5D=Shoe' \
                                 '&ul=ru&user_id=FE4C435E-13B3-438C-AF3E-BEEEB0B834F6'

        self.headers = {
            'Host': 'www.revolve.com',
            'Accept': '*/*',
            'x-ios-bundle-identifier': 'com.revolveclothings.iphone',
            'User-Agent': 'RevolveClothing/3.12.8 (com.revolveclothings.iphone; build:1; iOS 14.0.1) Alamofire/1.0.0',
            'Accept-Language': 'ru-RU;q=1.0, en-RU;q=0.9, en-GB;q=0.8, uk-UA;q=0.7, de-RU;q=0.6',
        }
        self.user_agent = generate_user_agent()

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
            ok, response = self.provider.request(self.catalog_link, headers=self.headers)

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]
                else:
                    raise response
            json_response = loads(response.text)


            for item in json_response['results']:
                title = item['title']
                if self.kw.check(title.lower()):
                    price = api.Price(api.CURRENCIES['EUR'], float(item['price'].replace(',', '').replace('$','')[:-1]))
                    image = item['custom_data']['imageURLs'][0]
                    id = item['_id']
                    is_preorder = item['custom_data']['isPreorder']
                    url = 'https://www.revolveclothing.ru' + item['url']

                    if is_preorder:
                        result.append(
                            IAnnounce(
                                url,
                                'revolve-mobile',
                                title,
                                image,
                                'DELIVERY FROM $100 IS FREE',
                                price,
                                api.Sizes(api.SIZE_TYPES[''], []),
                                [
                                    FooterItem('Cart', 'https://www.revolveclothing.ru/r/ShoppingBag.jsp'),
                                    FooterItem('Login', 'https://www.revolveclothing.ru/r/SignIn.jsp')
                                ],
                                {
                                    'Type': 'Preorder',
                                    'Site': '[Revolve Mobile App](https://www.revolve.com/r/mobile)',
                                    'Download App': '[Android](https://play.google.com/store/apps/details?id=com'
                                                    '.revolve&hl=ru) | [iOS]('
                                                    'https://apps.apple.com/ru/app/revolve/id377018720) '
                                }

                            )
                        )
                    else:
                        result.append(
                            result.append(
                                api.TInterval(f'https://www.revolveclothing.ru/r/mobile/dialo'
                                              f'g/QuickView.jsp?fmt=plp&code={id}', self.name,
                                              [url, title, image, price, id], 1)))

            if isinstance(content, api.CSmart):
                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False
                result.append(content)
            else:
                result.extend([self.catalog, api.MAlert('Script is awake', self.name)])

        if mode == 1:
            ok, response = self.provider.request(content.name, headers={'user-agent': self.user_agent})

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]
                else:
                    raise response

            page_content = etree.HTML(response.text)

            sizes = [api.Size(f"{size.get('value')} US")
                     for size in page_content.xpath('//option[@value]') if size.get('value')]

            if sizes:
                result.append(
                    IRelease(
                        content.data[0],
                        'revolve-mobile',
                        content.data[1],
                        content.data[2],
                        'DELIVERY FROM $100 IS FREE',
                        content.data[3],
                        api.Sizes(api.SIZE_TYPES[''], sizes),
                        [
                            FooterItem('Cart', 'https://www.revolveclothing.ru/r/ShoppingBag.jsp'),
                            FooterItem('Login', 'https://www.revolveclothing.ru/r/SignIn.jsp')
                        ],
                        {
                            'Site': '[Revolve Mobile App](https://www.revolve.com/r/mobile)',
                            'Download App': '[Android](https://play.google.com/store/apps/details?id=com'
                                            '.revolve&hl=ru) | [iOS]('
                                            'https://apps.apple.com/ru/app/revolve/id377018720) '
                        }
                    )
                )

        return result
