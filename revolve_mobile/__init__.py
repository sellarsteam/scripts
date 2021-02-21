from datetime import datetime, timedelta, timezone
from json import load, JSONDecodeError
from time import time
from typing import List, Union

import lxml
from lxml import etree
from pycurl_requests import exceptions
from ujson import loads
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
        self.catalog_link: str = 'https://www.revolve.com/content/nav/mobile/donde/search/?api_key=AIzaSyDxhzArAC6pxOgb0A7HMa5tPWhzJ3hTX2w&app_id=63fda592e3ad03ef6e56377948a1e996&d_id=UI-9B050F7D-0373-4DDB-BEBE-F2FF26E7E716&filter_factors[]=deviceType:iphone,referralUrl:aHR0cHM6Ly93d3cucmV2b2x2ZS5jb20vci9pcGFkQXBwL0JyYW5kcy5qc3A/ZD1Xb21lbnMmbj0mcz1jJmM9U2hvZXMmc2M9U25lYWtlcnMmc3NjPSZzc3NjPSZmdz1mYWxzZSZkZXNpZ25lcj1Kb3JkYW4mZmlsdGVycz1kZXNpZ25lciZzb3J0Qnk9ZmVhdHVyZWQmYXBwVmVyc2lvbj0zLjEyLjgmaXBob25lSWQ9RkU0QzQzNUUtMTNCMy00MzhDLUFGM0UtQkVFRUIwQjgzNEY2JmRldmljZU9TVmVyc2lvbj0xNC4wLjEmZGV2aWNlVHlwZT1pcGhvbmUmcGFnZVNpemU9MTAwJmNvdW50cnlDb2RlPVJVJnRva2VuPSZjdXJyZW5jeT1SVUImcGFnZU51bT0x&limit=100&localtime=2021-02-21%2015:34:49+0000&main_category=Women&offset=0&types[]=Shoe&ul=ru&user_id=FE4C435E-13B3-438C-AF3E-BEEEB0B834F6'

        self.headers = {
            'Host': 'www.revolve.com',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:85.0) Gecko/20100101 Firefox/85.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Cookie': 'viewNumR1=100; isPopupEnabledR1=true; pocketViewR1=front; currency=RUB; currencyOverride=USD; userLanguagePref=ru; fontsLoaded=1; sortByR2=featured; JSESSIONID2=E7E8099341FEC32D0B75ED37222ACD71.tc-chuck_tomcat4; bb_PageURL=%2Fcontent%2Fnav%2Fmobile%2Fdonde%2Fsearch%2F%3F%26api_key%3DAIzaSyDxhzArAC6pxOgb0A7HMa5tPWhzJ3hTX2w%26app_id%3D63fda592e3ad03ef6e56377948a1e996%26d_id%3DUI-9B050F7D-0373-4DDB-BEBE-F2FF26E7E716%26filter_factors%5B%5D%3DdeviceType%253Aiphone%252CreferralUrl%253AaHR0cHM6Ly93d3cucmV2b2x2ZS5jb20vci9pcGFkQXBwL0JyYW5kcy5qc3A%252FZD1Xb21lbnMmbj0mcz1jJmM9U2hvZXMmc2M9U25lYWtlcnMmc3NjPSZzc3NjPSZmdz1mYWxzZSZkZXNpZ25lcj1Kb3JkYW4mZmlsdGVycz1kZXNpZ25lciZzb3J0Qnk9ZmVhdHVyZWQmYXBwVmVyc2lvbj0zLjEyLjgmaXBob25lSWQ9RkU0QzQzNUUtMTNCMy00MzhDLUFGM0UtQkVFRUIwQjgzNEY2JmRldmljZU9TVmVyc2lvbj0xNC4wLjEmZGV2aWNlVHlwZT1pcGhvbmUmcGFnZVNpemU9MTAwJmNvdW50cnlDb2RlPVJVJnRva2VuPSZjdXJyZW5jeT1SVUImcGFnZU51bT0x%26limit%3D100%26localtime%3D2021-02-21%2B15%253A34%253A49%2B0000%26main_category%3DWomen%26offset%3D0%26types%5B%5D%3DShoe%26ul%3Dru%26user_id%3DFE4C435E-13B3-438C-AF3E-BEEEB0B834F6; altexp=%7B%22896%22%3A1%2C%221026%22%3A0%2C%221031%22%3A0%2C%221036%22%3A1%2C%22787%22%3A1%2C%22916%22%3A0%2C%221046%22%3A0%2C%22921%22%3A0%2C%221051%22%3A0%2C%22672%22%3A0%2C%221056%22%3A0%2C%22931%22%3A1%2C%22677%22%3A1%2C%221061%22%3A1%2C%22936%22%3A1%2C%22941%22%3A0%2C%221071%22%3A1%2C%22946%22%3A1%2C%22821%22%3A1%2C%22951%22%3A1%2C%221081%22%3A0%2C%22956%22%3A0%2C%22702%22%3A0%2C%221086%22%3A0%2C%22836%22%3A1%2C%221093%22%3A1%2C%22966%22%3A0%2C%22712%22%3A1%2C%22971%22%3A0%2C%221100%22%3A0%2C%22976%22%3A1%2C%22722%22%3A1%2C%221107%22%3A1%2C%22981%22%3A0%2C%22727%22%3A0%2C%22856%22%3A0%2C%22986%22%3A1%2C%221114%22%3A0%2C%22732%22%3A1%2C%22861%22%3A1%2C%22991%22%3A1%2C%22866%22%3A0%2C%221122%22%3A1%2C%221124%22%3A0%2C%22871%22%3A1%2C%221001%22%3A0%2C%22876%22%3A0%2C%221006%22%3A1%2C%22881%22%3A0%2C%221011%22%3A1%2C%22886%22%3A0%2C%221016%22%3A1%2C%22891%22%3A1%2C%221021%22%3A0%7D; optimizelyEndUserId=oeu1613923094044r0.41800295053719305; browserID=DzgbzLd7YM6lTJp4Qg6e18KWLJ3AEb',
            'Cache-Control': 'max-age=0'
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
                id = item['_id']
                if self.kw.check(title.lower() + ' ' + id.lower()):

                    result.append(
                        api.TScheduled(id, self.name, [item['custom_data']['isPreorder']], time())
                    )

            if isinstance(content, api.CSmart):
                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False
                result.append(content)
            else:
                result.extend([self.catalog, api.MAlert('Script is awake', self.name)])
            return result

        if mode == 1:
            ok, response = self.provider.request(f'https://www.revolve.com/r/ipadApp/ProductDetails.jsp?ap'
                                          f'pVersion=3.12.8&countryCode=RU&currency=RUB&deviceName='
                                          f'iPhone_6S&deviceOSVersion=14.0.1&deviceType=iphone&i'
                                          f'phoneId=FE4C435E-13B3-438C-AF3E-BEEEB0B834F6&token=&'
                                          f'code={content.name}&dept=F&noProductRecs=true',
                                                 headers={'user-agent': self.user_agent})

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]
                else:
                    raise response

            json_data = loads(response.text)['productData'][0]

            raw_sizes = [api.Size(size['sizeLabel'] + f' [{size["quantity"]}]')
                         for size in json_data['sizeCollection']['sizes'] if size['quantity'] > 0]
            sizes = api.Sizes(api.SIZE_TYPES[''], raw_sizes)

            if raw_sizes:
                result.append(
                    IRelease(
                        json_data['shareLink'] + f'&shas={sizes.hash().hex()}',
                        'revolve-mobile',
                        json_data['name'],
                        json_data['images'][0],
                        'DELIVERY FROM $100 IS FREE',
                        api.Price(api.CURRENCIES['USD'], json_data['price']),
                        sizes,
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
