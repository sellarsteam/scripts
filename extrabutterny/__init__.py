from json import loads, JSONDecodeError
from re import findall
from typing import List, Union

from jsonpath2 import Path
from lxml import etree

from requests import get

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://extrabutterny.com/collections/footwear/Mens'
        self.interval: int = 1
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot.html)Mozilla/5.0 ' \
                          '(compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html)' \
                          'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 ' \
                          '(KHTML, like Gecko) Chrome/41.0.2272.96 Mobile Safari/537.36 ' \
                          '(compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html)'

    @property
    def catalog(self) -> CatalogType:
        return api.CInterval(self.name, 3.)

    def execute(self, mode: int, content: Union[CatalogType, TargetType]) -> List[
        Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = [content]
        links = list()
        counter = 0
        for element in etree.HTML(self.provider.get(self.link,
                                                    headers={'user-agent': self.user_agent}, proxy=True
                                                    )).xpath('//div[@class="GridItem-imageContainer"]/a'):
            if element.get('href') is None:
                continue
            if counter == 5:
                break
            if 'nike' in element.get('href') or 'jordan' \
                    in element.get('href') or 'yeezy' in element.get('href'):
                links.append([api.Target('https://extrabutterny.com' + str(element.get('href')), self.name, 0),
                              'https://extrabutterny.com' + str(element.get('href'))])
            counter += 1
        if len(links) == 0:
            return result
        for link in links:
            try:
                if HashStorage.check_target(link[0].hash()):
                    try:
                        get_content = self.provider.get(link[1], headers={'user-agent': self.user_agent}, proxy=True)
                        page_content: etree.Element = etree.HTML(get_content)
                        available_sizes = list(
                            i.current_value['sku'].split('-')[-1] for i in Path.parse_str('$.offers.*')
                            .match(loads(page_content.xpath('//script[@type="application/ld+json"]')
                                         [0].text))
                            if i.current_value['availability'] == 'https://schema.org/InStock')
                        sizes_data = Path.parse_str('$.product.variants.*').match(
                            loads(findall(r'var meta = {.*}', get_content)[0]
                                  .replace('var meta = ', '')))
                    except etree.XMLSyntaxError:
                        raise etree.XMLSyntaxError('Exception XMLDecodeError')
                    except JSONDecodeError:
                        raise JSONDecodeError('Exception JSONDecodeError')
                    except IndexError:
                        HashStorage.add_target(link[0].hash())
                        continue
                    name = page_content.xpath('//title')[0].text.split(' [')[0]
                    HashStorage.add_target(link[0].hash())
                    sizes = [api.Size(str(size_data.current_value['public_title'].split(' ')[-1]) + ' US',
                                      'https://extrabutterny.com/cart/' + str(size_data.current_value['id']) + ':1')
                             for size_data in sizes_data
                             if size_data.current_value['public_title'].split(' ')[-1] in available_sizes]
                    result.append(IRelease(
                        link[1],
                        'shopify-filtered',
                        name,
                        page_content.xpath('//meta[@property="og:image:secure_url"]')[0].get('content'),
                        '',
                        api.Price(
                            api.CURRENCIES['USD'],
                            float(page_content.xpath('//meta[@property="og:price:amount"]')[0].get('content'))
                        ),
                        api.Sizes(api.SIZE_TYPES[''], sizes),
                        [
                            FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                       name.replace(' ', '%20')),
                            FooterItem('Cart', 'https://extrabutterny.com/cart'),
                            FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                        ],
                        {'Site': 'Extra Butter NY'}
                    )
                    )
            except etree.XMLSyntaxError:
                raise etree.XMLSyntaxError('Exception XMLDecodeError')
        return result
