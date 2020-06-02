from json import loads, JSONDecodeError
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
        self.link: str = 'https://shop.pharmabergen.no/collections/new-arrivals/'
        self.interval: int = 1
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot.html)Mozilla/5.0 ' \
                          '(compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html)' \
                          'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 ' \
                          '(KHTML, like Gecko) Chrome/41.0.2272.96 Mobile Safari/537.36 (compatible; ' \
                          'Pinterestbot/1.0; +https://www.pinterest.com/bot.html)'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, self.time_gen(), 2, exp=30.)

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=6, microsecond=500000, tzinfo=timezone.utc).timestamp()

    def execute(self, mode: int, content: Union[CatalogType, TargetType]) -> List[
        Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            links = []
            counter = 0
            for element in etree.HTML(self.provider.get(self.link, headers={'user-agent': self.user_agent}, proxy=True
                                                        )).xpath('//div[@class="product-info-inner"]/a'):
                if counter == 5:
                    break
                if 'yeezy' in element.get('href') or 'air' in element.get('href') or 'sacai' in element.get('href') \
                        or 'dunk' in element.get('href') or 'retro' in element.get('href'):
                    links.append([api.Target('https://shop.pharmabergen.no' + element.get('href'), self.name, 0),
                                  'https://shop.pharmabergen.no' + element.get('href')])
                counter += 1

            for link in links:
                try:
                    if HashStorage.check_target(link[0].hash()):
                        page_content: etree.Element = etree.HTML(self.provider.get(link[1],
                                                                                   headers={
                                                                                       'user-agent': self.user_agent},
                                                                                   proxy=True))
                        available_sizes = list(size.get('data-value').replace(' 1/2', '.5')
                                               for size in page_content.xpath('//div[@class="swatch clearfix"]/div')
                                               if 'available' in size.get('class'))
                        sizes_data = Path.parse_str('$.variants.*').match(
                            loads(page_content.xpath('//form[@action="/cart/add"]')[0].get('data-product')))

                        name = page_content.xpath('//meta[@property="og:title"]')[0].get('content')
                        HashStorage.add_target(link[0].hash())
                        sizes = [api.Size(str(size_data.current_value['option1']) + ' EU',
                                          'https://shop.pharmabergen.no/cart/' + str(
                                              size_data.current_value['id']) + ':1')
                                 for size_data in sizes_data
                                 if size_data.current_value['option1'] in available_sizes]
                        result.append(IRelease(
                            link[1],
                            'shopify-filtered',
                            name,
                            page_content.xpath('//meta[@property="og:image:secure_url"]')[0].get('content'),
                            '',
                            api.Price(
                                api.CURRENCIES['NOK'],
                                float(page_content.xpath('//meta[@property="og:price:amount"]')[0].get('content')
                                      .replace('.', '').replace(',', '.'))
                            ),
                            api.Sizes(api.SIZE_TYPES[''], sizes),
                            [
                                FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                           name.replace(' ', '%20')),
                                FooterItem('Cart', 'https://shop.pharmabergen.no/cart'),
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            {'Site': 'Pharma Bergen'}
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
