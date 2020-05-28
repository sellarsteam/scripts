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
        self.link: str = 'https://www.a-ma-maniere.com/collections/new-arrivals'
        self.interval: int = 1
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot.html)Mozilla/5.0 (compatible; ' \
                          'Pinterestbot/1.0; +https://www.pinterest.com/bot.html)Mozilla/5.0 (Linux; Android ' \
                          '6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                          'Chrome/41.0.2272.96 Mobile Safari/537.36 (compatible; ' \
                          'Pinterestbot/1.0; +https://www.pinterest.com/bot.html)'

    @property
    def catalog(self) -> CatalogType:
        return api.CInterval(self.name, 3.)

    def execute(self, mode: int, content: Union[CatalogType, TargetType]) -> List[
        Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        if mode == 0:
            links = list()
            counter = 0
            for element in etree.HTML(self.provider.get(self.link,
                                                        headers={'user-agent': self.user_agent}, proxy=True)) \
                    .xpath('//div[@class="collection-product"]/a'):
                if counter == 5:
                    break
                if 'yeezy' in element.get('href') or 'air' in element.get('href') or 'dunk' in element.get('href') \
                        or 'dunk' in element.get('href') or 'retro' in element.get('href') \
                        or 'blazer' in element.get('href'):
                    links.append([api.Target('https://www.a-ma-maniere.com' + element.get('href'), self.name, 0),
                                  'https://www.a-ma-maniere.com' + element.get('href')])
                counter += 1
            if len(links) == 0:
                return [content]
            for link in links:
                try:
                    if HashStorage.check_target(link[0].hash()):
                        item_link = link[1]
                        get_content = self.provider.get(item_link, headers={'user-agent': self.user_agent}, proxy=True)
                        page_content = etree.Element = etree.HTML(get_content)
                        counter = 0
                        symbol = 'c'
                        available_sizes = list()
                        for size in page_content.xpath('//div[@class="product-size-container"]/span'):
                            if counter == 0:
                                symbol = size.text[-1]
                                counter += 1
                            if 'unavailable' not in size.get('class'):
                                available_sizes.append(size.text.replace(symbol, ''))
                        sizes = list()
                        for size in Path.parse_str('$.product.variants.*').match(
                                loads(findall(r'var meta = {.*}', get_content)[0].replace('var meta = ', ''))):
                            value = size.current_value['public_title']
                            if value in available_sizes:
                                sizes.append(api.Size(str(size.current_value['public_title']) + symbol,
                                                      'https://www.a-ma-maniere.com/cart/' + str(value) + ':1'))
                        name = page_content.xpath('//meta[@property="og:title"]')[0].get('content')
                        HashStorage.add_target(link[0].hash())
                        return [IRelease(
                            name,
                            item_link,
                            'shopify-filtered',
                            page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                            '',
                            api.Price(
                                api.CURRENCIES['USD'],
                                float(page_content.xpath('//meta[@property="og:price:amount"]')[0].get('content'))
                            ),
                            api.Sizes(api.SIZE_TYPES[''], sizes),
                            [
                                FooterItem('StockX',
                                           'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                                FooterItem('Cart', 'https://www.a-ma-maniere.com/cart'),
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            {'Site': 'A-Ma-Maniere'}
                        ), content]
                    else:
                        continue
                except etree.XMLSyntaxError:
                    raise etree.XMLSyntaxError('Exception XMLDecodeError')
                except JSONDecodeError:
                    raise JSONDecodeError('Exception JSONDecodeError')
