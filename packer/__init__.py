from datetime import datetime, timedelta, timezone
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
        self.link: str = 'https://packershoes.com/collections/new-arrivals/sneakers?page=1'
        self.interval: float = 1
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot.html)Mozilla/5.0 ' \
                          '(compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html)' \
                          'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 ' \
                          '(KHTML, like Gecko) Chrome/41.0.2272.96 Mobile Safari/537.36 ' \
                          '(compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html)'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, self.time_gen(), 2, exp=30.)

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=1, microsecond=500000, tzinfo=timezone.utc).timestamp()

    def execute(self, mode: int, content: Union[CatalogType, TargetType]) -> List[
        Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            links = []
            counter = 0
            catalog_links = etree.HTML(self.provider.get(self.link,
                                                         headers={'user-agent': self.user_agent}, proxy=True)) \
                .xpath('//a[@class="grid-product__meta"]')
            if not catalog_links:
                raise ConnectionResetError('Shopify banned this IP')
            for element in catalog_links:
                if counter == 5:
                    break
                if 'yeezy' in element.get('href') or 'air' in element.get('href') or 'sacai' in element.get('href') \
                        or 'dunk' in element.get('href') or 'retro' in element.get('href'):
                    links.append([api.Target('https://packershoes.com' + element.get('href'), self.name, 0),
                                  'https://packershoes.com' + element.get('href')])
                counter += 1

            for link in links:
                if HashStorage.check_target(link[0].hash()):
                    try:
                        get_content = self.provider.get(link[1], headers={'user-agent': self.user_agent}, proxy=True)
                        page_content: etree.Element = etree.HTML(get_content)
                        sizes_data = Path.parse_str('$.product.variants.*').match(
                            loads(findall(r'var meta = {.*}', get_content)[0].replace('var meta = ', '')))
                        name = page_content.xpath('//meta[@property="og:title"]')[0].get('content')
                        HashStorage.add_target(link[0].hash())
                        available_sizes = list(size.get('id').split('-')[-1]
                                               for size in page_content.xpath('//fieldset[@id="ProductSelect-option-0'
                                                                              '"]/input')
                                               if 'disabled' not in size.get('class'))
                        sizes = [api.Size(str(size_data.current_value['public_title'].split(' /')[0]) + ' US',
                                          'https://packershoes.com/cart/' + str(size_data.current_value['id']) + ':1')
                                 for size_data in sizes_data
                                 if size_data.current_value['public_title'].split(' /')[0] in available_sizes]
                        result.append(IRelease(
                            link[1],
                            'shopify-filtered',
                            name,
                            page_content.xpath('//meta[@property="og:image"]')[0].get('content').split('?')[0],
                            '',
                            api.Price(
                                api.CURRENCIES['USD'],
                                float(page_content.xpath('//meta[@property="og:price:amount"]')[0].get('content')
                                      .replace(',', ''))
                            ),
                            api.Sizes(api.SIZE_TYPES[''], sizes),
                            [
                                FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                           name.replace(' ', '%20')),
                                FooterItem('Cart', 'https://packershoes.com/cart'),
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            {'Site': 'Packer Shoes'}
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
