from typing import Union, List

from pycurl_requests import exceptions
from ujson import loads

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease
from source.library import SubProvider, Keywords
from source.tools import ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.link = 'https://ps5status.ru/api/data'
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Host': 'ps5status.ru',
            'TE': 'Trailers',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'
        }

    @property
    def catalog(self) -> api.CatalogType:
        return api.CInterval(self.name, 5)

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            ok, response = self.provider.request(self.link, headers=self.headers)

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]
                else:
                    raise response

            json_data = loads(response.text)

            catalog = [element for element in json_data['data']['shops'].values()]
            if not catalog:
                return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]

            for element in catalog:

                shop_name = element['name']
                image = element['pic']

                normal_link = element['normal_link']
                digital_link = element['digital_link']

                try:
                    if element['digital_info']['available'] is True:
                        result.append(
                            IRelease(
                                digital_link + f'?stime={element["digital_info"]["appearedAt"].replace(":", "").replace(",", "").replace(" ", "")}',
                                'ps5',
                                f'[{shop_name.upper()}] Play Station 5 Digital Edition',
                                image,
                                '',
                                api.Price(api.CURRENCIES[''], 37999.0),
                                api.Sizes(api.SIZE_TYPES[''], [api.Size('ONE SIZE')]),
                                [],
                                {
                                    'Site': shop_name.upper()
                                }
                            )
                        )

                    if element['normal_info']['available'] is True:
                        result.append(
                            IRelease(
                                normal_link + f'?stime={element["normal_info"]["appearedAt"].replace(":", "").replace(",", "").replace(" ", "")}',
                                'ps5',
                                f'[{shop_name.upper()}] Play Station 5',
                                image,
                                '',
                                api.Price(api.CURRENCIES[''], 46999.0),
                                api.Sizes(api.SIZE_TYPES[''], [api.Size('ONE SIZE')]),
                                [],
                                {
                                    'Site': shop_name.upper()
                                }
                            )
                        )
                except TypeError:
                    continue

        result.append(content)
        return result

