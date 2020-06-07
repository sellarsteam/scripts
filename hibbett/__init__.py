from typing import List, Union

from lxml import etree
from user_agent import generate_user_agent

from source import api
from source.api import CatalogType, TargetType, RestockTargetType, TargetEndType, ItemType, FooterItem
import datetime
from time import mktime
from source.logger import Logger

MOUNTS = {
    'JAN': 1,
    'FEB': 2,
    'MAR': 3,
    'APR': 4,
    'MAY': 5,
    'JUN': 6,
    'JUL': 7,
    'AUG': 8,
    'SEP': 9,
    'OCT': 10,
    'NOV': 11,
    'DEC': 12
}


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider):
        super().__init__(name, log, provider)
        self.link: str = 'https://www.hibbett.com/launch-calendar/?prefn1=dtLaunch&prefv1=30&format=ajax'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> api.CatalogType:
        return api.CInterval(self.name, 1200)

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            counter = 0
            for element in etree.HTML(self.provider.get(url=self.link, proxy=True, mode=1,
                                                        headers={'user-agent': self.user_agent})) \
                    .xpath('//a[@class="thumb-link has-alt-image"]'):
                if counter == 10:
                    break
                if 'dunk' in element.get('href') or 'yeezy' in element.get('href') or 'jordan' in element.get('href') \
                        or 'sacai' in element.get('href') or 'air' in element.get('href'):
                    result.append(api.TInterval(element.get('href'), self.name, 0, 0))
                counter += 1
        elif mode == 1:
            result = []
            page_content = etree.HTML(self.provider.get(url=content.name + '&format=ajax', proxy=True, mode=1,
                                                        headers={'user-agent': self.user_agent}))
            available_sizes = []
            data_for_image = content.name.split('/')[-1]
            for element in page_content.xpath('//ul[@class="swatches size "]/li[@class="selectable"]/a'):
                size = element.get('href').split('size=')[-1].split('&')[0].replace('0', '')
                if len(size) == 2:
                    if size == '15':
                        size = '10.5 US'
                    else:
                        if size[-1] == '5':
                            size = f'{float(size) / 10} US'
                        else:
                            size = f'{size} US'
                else:
                    if size == '1':
                        size = '10 US'
                    elif size[-1] == '5':
                        size = f'{float(size) / 10} US'
                    else:
                        size = f'{size} US'
                available_sizes.append(api.Size(size, element.get('href')))
            try:
                name = page_content.xpath('//h1[@itemprop="name"]')[0].text
            except IndexError:
                name = ''
            try:
                image = page_content.xpath('//img[@class="lazy"]')[0].get('data-src')
            except IndexError:
                image = f'https://i1.adis.ws/i/hibbett/{data_for_image.split(".html")[0]}' + \
                        f'_{data_for_image.split("color=")[-1].split("&")[0]}_' + \
                        f'right1?w=580&h=580&fmt=jpg&bg=rgb(255,255,255)&img404=404&v=0'

            if not available_sizes:
                date_for_print = page_content.xpath('//div[@class="launch-date-box"]/script')[0].text.split('\'')[1]
                date_data = date_for_print.split(' ')
                date = mktime(datetime.datetime(int(date_data[-1]), MOUNTS[date_data[1].upper()], int(date_data[2]),
                                                int(date_data[3].split(':')[0]), int(date_data[3].split(':')[1]),
                                                int(date_data[3].split(':')[2])).timetuple())
                result.append(
                    api.IAnnounce(
                        content.name,
                        'hibbett',
                        name,
                        image,
                        '',
                        api.Price(api.CURRENCIES['USD'], float(page_content.xpath('//span[@class="price-sales"]')[0]
                                                               .get('content'))),
                        api.Sizes(api.SIZE_TYPES[''], []),
                        [
                            FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                       name.replace(' ', '%20').replace('"', '').replace('\n', '')),
                            FooterItem('Cart', 'https://www.hibbett.com/cart'),
                            FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                        ],
                        {'Site': 'Hibbett Sports', 'Date': date_for_print}
                    )
                )
                result.append(api.TSmart(content.name, self.name, 0, date + 1, 100))
            else:
                result.append(api.IRelease(
                    content.name,
                    'hibbett',
                    name,
                    image,
                    '',
                    api.Price(api.CURRENCIES['USD'], float(page_content.xpath('//span[@class="price-sales"]')[0]
                                                           .get('content'))),
                    api.Sizes(api.SIZE_TYPES[''], available_sizes),
                    [
                        FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                   name.replace(' ', '%20').replace('"', '').replace('\n', '')),
                        FooterItem('Cart', 'https://www.hibbett.com/cart'),
                        FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    ],
                    {'Site': 'Hibbett Sports'}
                ))
        return result

