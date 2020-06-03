from json import loads, JSONDecodeError
from re import findall
from typing import List, Union

from jsonpath2 import Path
from lxml import etree
from datetime import datetime, timedelta, timezone

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://rsvpgallery.com/collections/footwear?sort_by=created-descending'
        self.interval: int = 1
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot.html)Mozilla/5.0 (compatible; ' \
                          'Pinterestbot/1.0; +https://www.pinterest.com/bot.html)Mozilla/5.0 (Linux; Android ' \
                          '6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                          'Chrome/41.0.2272.96 Mobile Safari/537.36 (compatible; ' \
                          'Pinterestbot/1.0; +https://www.pinterest.com/bot.html)'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, self.time_gen(), 2, exp=30.)

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=1, microsecond=750000, tzinfo=timezone.utc).timestamp()

    def execute(self, mode: int, content: Union[CatalogType, TargetType]) -> List[
        Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            links = []
            counter = 0
            catalog_links = etree.HTML(self.provider.get(self.link,
                                                         headers={'user-agent': self.user_agent}, proxy=True)) \
                .xpath('//div[@class="product-details"]/a')
            if not catalog_links:
                raise ConnectionResetError('Shopify banned this IP')
            for element in catalog_links:
                if counter == 5:
                    break
                if 'slider' not in element.get('href') and ('yeezy' in element.get('href')
                                                            or 'air' in element.get('href')
                                                            or 'dunk' in element.get('href')
                                                            or 'dunk' in element.get('href')
                                                            or 'retro' in element.get('href')
                                                            or 'blazer' in element.get('href')
                                                            or 'off-white' in element.get('href')):
                    links.append([api.Target('https://rsvpgallery.com' + element.get('href'), self.name, 0),
                                  'https://rsvpgallery.com' + element.get('href')])
                counter += 1

            for link in links:
                try:
                    if HashStorage.check_target(link[0].hash()):
                        get_content = self.provider.get(link[1], headers={'user-agent': self.user_agent}, proxy=True)
                        page_content: etree.Element = etree.HTML(get_content)
                        sizes = [api.Size(str(size_data.current_value['public_title']) + ' US',
                                          'https://rsvpgallery.com/cart/' + str(size_data.current_value['id']) + ':1')
                                 for size_data in Path.parse_str('$.variants.*').match(
                                loads(findall(r'product: {.*}', get_content)[0].replace('product: ', ''))) if
                                 size_data.current_value['available'] is True]
                        name = page_content.xpath('//h1[@class="desktop-12"]')[0].text
                        try:
                            price = float(page_content.xpath('//div[@class="price-field"]/span')[0].text.split(' ')[1])
                        except ValueError:
                            price = 0.
                        HashStorage.add_target(link[0].hash())
                        result.append(IRelease(
                            link[1],
                            'shopify-filtered',
                            name,
                            'http:' + page_content.xpath('//meta[@itemprop="image"]')[0].get('content'),
                            '',
                            api.Price(
                                api.CURRENCIES['USD'],
                                price
                            ),
                            api.Sizes(api.SIZE_TYPES[''], sizes),
                            [
                                FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                           name.replace(' ', '%20')),
                                FooterItem('Cart', 'https://rsvpgallery.com/cart'),
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            {'Site': 'RSVP Gallery'}
                        )
                        )
                except etree.XMLSyntaxError:
                    raise etree.XMLSyntaxError('Exception XMLDecodeError')
                except JSONDecodeError:
                    raise JSONDecodeError('Exception JSONDecodeError')
            if result or content.expired:
                content.timestamp = self.time_gen()
                content.expired = False

            result.append(content)
        return result
