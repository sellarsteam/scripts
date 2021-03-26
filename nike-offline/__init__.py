import time
from typing import List, Union

from lxml import etree

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, TScheduled
from source.library import SubProvider, Keywords
from source.tools import ScriptStorage

CITIES = ['Москва']

CITIES_DARA = {
}

LINKS = {
    "jordan_1": "https://up-and-run.ru/catalog/?PAGEN_1=1&q=jordan&searchFilter_57_1536390870=Y&searchFilter_P3_MIN=&searchFilter_P3_MAX=&set_filter=Y&AJAX_PAGE=Y",
    "jordan_2": "https://up-and-run.ru/catalog/?PAGEN_2=2&q=jordan&searchFilter_57_1536390870=Y&searchFilter_P3_MIN=&searchFilter_P3_MAX=&set_filter=Y&AJAX_PAGE=Y",
    "dunk": "https://up-and-run.ru/catalog/?PAGEN_1=1&q=dunk&searchFilter_57_1536390870=Y&searchFilter_P3_MIN=&searchFilter_P3_MAX=&set_filter=Y&AJAX_PAGE=Y"
}


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.counter = 0
        self.headers = {
            'cookie': 'PHPSESSID=eeuc8cv7k3d1tv9qn59tc8qpq2; BX_USER_ID=e86dd952e2aaf6819ed9514305db6185;'
                      ' _ga_RT9D6RKN6F=GS1.1.1616777271.2.0.1616777271.0; _ga=GA1.2.840946506.1616765869; '
                      '_ym_uid=1616765869626360248; _ym_d=1616765869; _gid=GA1.2.385747489.1616765869; _ym_'
                      'isad=2; _dc_gtm_UA-62374597-1=1; _dc_gtm_UA-71374419-1=1; _ym_visorc=w'
        }

    @property
    def catalog(self) -> api.CatalogType:
        return api.CInterval(self.name, 10000000)

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            if self.counter == len(CITIES):
                self.counter = 0

            result.append(result.append(api.TInterval('jordan_1 catalog', self.name, [CITIES[self.counter]], 5)))
            result.append(result.append(api.TInterval('jordan_2 catalog', self.name, [CITIES[self.counter]], 5)))
            result.append(result.append(api.TInterval('dunk catalog', self.name, [CITIES[self.counter]], 5)))
            result.append(content)

        if mode == 1:
            if content.name.split(' ')[-1] == 'catalog':
                ok, response = self.provider.request(LINKS[content.name.split(' ')[0]], headers=self.headers)

                lxml = etree.HTML(response.text)
                catalog = lxml.xpath('//div[@class="container" or @class="container w1024"]')

                for item in catalog:
                    name = item.xpath('div/a/div[@class="name"]')[0].text
                    if self.kw.check(name.lower()):
                        link = 'https://up-and-run.ru' + item.xpath('div/a')[0].get('href')

                        pid = link.split('/')
                        pid = pid[len(pid) - 2]

                        color_id = item.xpath('div/a/div[@class="img"]'
                                              '/div[@class="carousel"]/div/div/div/img')[0].get('data-link')
                        try:
                            price = api.Price(api.CURRENCIES[''], float(item.xpath('div/a/div[@class="price"]'
                                                                                   '/span[@class="new_price"]')[0]
                                                                        .text.replace(' ', '')),
                                              float(item.xpath('div/a/div[@class="price"]/span[@class="old_price"]')
                                                    [0].text.replace(' ', '')))
                        except IndexError:
                            price = api.Price(api.CURRENCIES[''], float(item.xpath('div/a/div[@class="price"]')[0]
                                                                        .text.replace(' ', '')))

                        image = 'https://up-and-run.ru' + item.xpath('div/a/div[@class="img"]/img')[0].get('src')
                        result.append(api.TScheduled(name, self.name, [link, pid, color_id, price, image], time.time()))
                result.append(content)
            else:
                ok, response = self.provider.request('https://up-and-run.ru/ajax/order.php?id=ITEM_ID&color=COLOR_ID'
                                                     .replace('ITEM_ID', content.data[1])
                                                     .replace('COLOR_ID', content.data[2]),
                                                     headers=self.headers
                                                     )
                lxml_data = etree.HTML(response.text)

                raw_sizes = []
                for size in lxml_data.xpath('//div[@class="form__item __right"]/select'):
                    shops = ''
                    for shop in size.xpath('option'):
                        if shop.text != 'Не выбран':
                            shops += f"{shop.text} [{shop.get('data-merch-count')}]\n"
                    raw_sizes.append(api.Size(f"**{size.get('id').replace('_', '.')}**\n{shops}"))

                sizes = api.Sizes(api.SIZE_TYPES[''], raw_sizes)

                if raw_sizes:
                    result.append(
                        IRelease(
                            content.data[0] + f'?shas="{sizes.hash().hex()}"',
                            'nike-offline',
                            content.name,
                            content.data[4],
                            '',
                            content.data[3],
                            sizes,
                            [],
                            {
                                'Site': 'Nike Offline',
                                'City': 'Moscow'
                            }
                        )
                    )

        return result
