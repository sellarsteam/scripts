from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.link: str = 'https://www.regard.ru/catalog/group4037.htm'
        self.interval: int = 1
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:85.0) Gecko/20100101 Firefox/85.0',
            'Cookie': '_ym_uid=16140824471027440334; _ym_d=1614082447;'
                      ' _userGUID=0:klhz0iw7:kw6Yssnzx8kCQ2NGZyYVaVYJgjUBhkRH; _ym_isad=2;'
                      ' _ga=GA1.2.2070612808.1614082448; _gid=GA1.2.334155988.1614082448;'
                      ' sorting=price_desc; PHPSESSID=akcl18eod1kv4slv57gbr0e2s7;'
                      ' dSesn=f56eca2f-db25-b4b4-90b0-54d91505b5fa;'
                      ' _dvs=0:kli50cun:mqV~lsvLcBjVLr11aMVdahhw8PY~uSIs; _ym_visorc=w; page_limit=9999'
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

            ok, response = self.provider.request(self.link, headers=self.headers)

            if not ok:
                return [api.CInterval(self.name, 60.), api.MAlert('Script go to sleep', self.name)]
            try:
                catalog = [element for element in etree.HTML(response.content).xpath('//div[@class="content"]'
                                                                                  '/div[@class="block"]/div')]
            except AttributeError:
                return [api.CInterval(self.name, 60.), api.MAlert('Script go to sleep', self.name)]
            if not catalog:
                return [api.CInterval(self.name, 60.), api.MAlert('Script go to sleep', self.name)]

            for element in catalog:

                link = 'https://www.regard.ru' + element.xpath('div[@class="aheader"]/a')[0].get('href')

                name = element.xpath('div[@class="aheader"]/span')[0].get('content')
                if '3050' in name or '3060' in name or '3070' in name or '3080' in name or '3090' in name:
                    image = 'https://www.regard.ru' + element.xpath('div[@class="block_img"]/a/img')[0].get('src')
                    price = api.Price(
                        api.CURRENCIES['RUB'],
                        float(element.xpath('div[@class="price"]/span')[-1].text.replace(' ', ''))
                    )
                    available = True
                    try:
                        if element.xpath('div[@class="price"]/a')[0].get('class') == 'cart-disabled':
                            available = False
                        else:
                            available = True
                    except IndexError:
                        available = True

                    sizes = api.Sizes(api.SIZE_TYPES[''], [api.Size('ONE SIZE')])

                    if available:

                        result.append(
                            IRelease(
                                link + '#sllrs',
                                'nvidia',
                                name.replace('Âèäåîêàðòà ', ''),
                                image,
                                '',
                                price,
                                sizes,
                                [
                                    FooterItem('Cart', 'https://www.regard.ru/basket/')
                                ],
                                {}#additional_columns
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