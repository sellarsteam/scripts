from json import loads, JSONDecodeError
from re import findall
from typing import List, Union

from jsonpath2 import Path
from lxml import etree

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://www.lapstoneandhammer.com/collections/new-arrival-1'
        self.interval: int = 1
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot.html)Mozilla/5.0 (compatible; ' \
                          'Pinterestbot/1.0; +https://www.pinterest.com/bot.html)Mozilla/5.0 (Linux; ' \
                          'Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                          'Chrome/41.0.2272.96 Mobile Safari/537.36 (compatible; Pinterestbot/1.0; ' \
                          '+https://www.pinterest.com/bot.html)'

    @property
    def catalog(self) -> CatalogType:
        return api.CInterval(self.name, 3.)

    def execute(self, mode: int, content: Union[CatalogType, TargetType]) -> List[
        Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = [content]
        if mode == 0:
            links = list()
            counter = 0
            for element in etree.HTML(self.provider.get(
                    self.link,
                    headers={'user-agent': self.user_agent}, proxy=True)).xpath('//div[@class="image-wrapper"]/a'):
                if counter == 1000:
                    break
                if 'yeezy' in element.get('href') or 'jordan' in element.get('href') or 'air' in element.get('href') \
                        or 'dunk' in element.get('href') or 'sacai' in element.get('href'):
                    links.append([api.Target('https://www.lapstoneandhammer.com' + element.get('href'), self.name, 0),
                                  'https://www.lapstoneandhammer.com' + element.get('href')])
                counter += 1
            if len(links) == 0:
                return result
            for link in links:
                if HashStorage.check_target(link[0].hash()):
                    try:
                        get_content = self.provider.get(link[1], headers={'user-agent': self.user_agent}, proxy=True)
                        page_content: etree.Element = etree.HTML(get_content)
                        sizes_data = Path.parse_str('$.product.variants.*'). \
                            match(loads(findall(r'var meta = {.*}', get_content)[0].replace('var meta = ', '')))
                    except etree.XMLSyntaxError:
                        raise etree.XMLSyntaxError('Exception XMLDecodeError')
                    except JSONDecodeError:
                        raise JSONDecodeError('Exception JSONDecodeError')
                    HashStorage.add_target(link[0].hash())
                    name = page_content.xpath('//meta[@property="og:title"]')[0].get('content')
                    try:  # If item is available via raffle
                        if page_content.xpath('//h2[@style="color:#ff8c00;"]')[0].text \
                                == 'THIS PRODUCT IS ONLY AVAILABLE VIA RAFFLE.':
                            result.append(IRelease(
                                link[1],
                                'shopify-filtered',
                                '[RAFFLE] ' + name,
                                'https:' + page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                                '',
                                api.Price(
                                    api.CURRENCIES['USD'],
                                    float(page_content.xpath('//span[@class="actual-price"]')[0].text.split(' ')[-1])
                                ),
                                api.Sizes(api.SIZE_TYPES[''], []),
                                [
                                    FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                               name.replace(' ', '%20')),
                                    FooterItem('Cart', 'https://www.lapstoneandhammer.com/cart'),
                                    FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                ],
                                {'Site': 'Lapstone And Hammer'}
                            )
                            )
                        continue
                    except IndexError:
                        pass
                    available_sizes = list()
                    try:
                        for size in page_content.xpath('//select[@id="variant-listbox"]/option'):
                            if size.items()[0][0] != 'disabled':
                                available_sizes.append(size.text.replace(' ', ''))
                    except IndexError:
                        continue
                    sizes = [api.Size(str(size_data.current_value['public_title'].split(' ')[-1]) + ' US',
                                      'https://www.lapstoneandhammer.com/cart/' + str(
                                          size_data.current_value['id']) + ':1')
                             for size_data in sizes_data
                             if size_data.current_value['public_title'].split(' ')[-1] in available_sizes]
                    result.append(IRelease(
                        link[1],
                        'shopify-filtered',
                        name,
                        'https:' + page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                        '',
                        api.Price(
                            api.CURRENCIES['USD'],
                            float(page_content.xpath('//span[@class="actual-price"]')[0].text.split(' ')[-1])
                        ),
                        api.Sizes(api.SIZE_TYPES[''], sizes),
                        [
                            FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                       name.replace(' ', '%20')),
                            FooterItem('Cart', 'https://www.lapstoneandhammer.com/cart'),
                            FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                        ],
                        {'Site': 'Lapstone And Hammer'}
                    )
                    )
        return result
