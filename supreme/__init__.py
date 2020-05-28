from typing import List, Union

from lxml import etree
from requests.exceptions import SSLError
from user_agent import generate_user_agent

from source import logger
from source import api
from source.cache import HashStorage
from source.api import CatalogType, TargetType, CInterval, IRelease, RestockTargetType, ItemType, TargetEndType, \
    FooterItem
from source.library import SubProvider


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://www.supremenewyork.com/shop/all'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CInterval:
        return api.CInterval(self.name, 5)

    def execute(self, mode: int, content: Union[CatalogType, TargetType]) -> List[
        Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        if mode == 0:
            links = [[api.Target(element.get('href'), self.name, 0), element.get('href')] for element in etree.HTML(self.provider.get(
                        self.link,
                        headers={'user-agent': self.user_agent}
                )).xpath('//a[@style="height:81px;"]') if len(element.xpath('div[@class="sold_out_tag"]')) == 0]
            result = [content, ]
            try:
                for link in links:
                    if HashStorage.check_target(link[0].hash()):
                        item_link = link[1]
                        page_content = etree.HTML(self.provider.get(item_link,
                                                                    headers={'user-agent': self.user_agent}))
                        if 'jackets' in item_link or 'tops_sweaters' in item_link or 'shirts' in item_link or 'sweatshirts'\
                                in item_link or 't-shirts' in item_link:
                            sizes = list()
                            for size in page_content.xpath('//option[@value]'):
                                value = size.text
                                if value == 'XSmall':
                                    value_float = 1.0
                                elif value == 'Small':
                                    value_float = 2.0
                                elif value == 'Medium':
                                    value_float = 3.0
                                elif value == 'Large':
                                    value_float = 4.0
                                elif value == 'XLarge':
                                    value_float = 5.0
                                elif value == 'XXLarge':
                                    value_float = 6.0
                                else:
                                    value_float = 7.0
                                sizes.append(api.Size(value_float, ))
                            result_sizes = api.Sizes(api.SIZE_TYPES['C-U-W'], sizes)
                        elif 'shoes' in item_link:
                            result_sizes = api.Sizes(api.SIZE_TYPES['S-US-M'], (api.Size(float(size.text)) for size in
                                                                                content.xpath('//option[@value]')))
                        elif 'pants' in item_link or 'shorts' in item_link:
                            sizes = list()
                            first_size = page_content.xpath('option[@value]')[0].text
                            if first_size == 'XSmall' or first_size == 'Small' or first_size == 'Medium' or first_size == 'Large':
                                for size in page_content.xpath('//option[@value]'):
                                    value = size.text
                                    if value == 'XSmall':
                                        value_float = 1.0
                                    elif value == 'Small':
                                        value_float = 2.0
                                    elif value == 'Medium':
                                        value_float = 3.0
                                    elif value == 'Large':
                                        value_float = 4.0
                                    elif value == 'XLarge':
                                        value_float = 5.0
                                    elif value == 'XXLarge':
                                        value_float = 6.0
                                    else:
                                        value_float = 7.0
                                    sizes.append(api.Size(value_float, ))
                                result_sizes = api.Sizes(api.SIZE_TYPES['C-U-W'], sizes)
                            elif first_size.isdigit():
                                result_sizes = api.Sizes(api.SIZE_TYPES['P-M-W'], [api.Size(float(size.text)) for size in
                                                                                   content.xpat('//option[@value]')])
                            else:
                                result_sizes = api.Sizes(api.SIZE_TYPES[''], [api.Size(float(1)), ])
                        else:
                            result_sizes = api.Sizes(api.SIZE_TYPES[''], [api.Size(float(1)), ])
                        result.append(
                            IRelease(
                                self.name,
                                item_link,
                                'supreme-nyc',
                                'https://' + page_content.xpath('//img[@itemprop="image"]')[0].get('src').replace('//', ''),
                                page_content.xpath('//p[@itemprop="description"]')[0].text,
                                api.Price(api.CURRENCIES['EUR'],
                                          float(page_content.xpath('//span[@itemprop="price"]')[0].text
                                                .replace('€', ''))),
                                result_sizes,
                                [
                                    FooterItem('StockX', 'https://stockx.com/search?s=' +
                                               page_content.xpath('//h1[@itemprop="name"]')
                                               [0].text.replace(' ', '%20').replace(
                                                   '®', '')),
                                    FooterItem('Cart', 'https://www.supremenewyork.com/shop/cart'),
                                    FooterItem('Mobile', 'https://www.supremenewyork.com/mobile#products/' +
                                               page_content.xpath('//form[@class="add"]')[0].get('action').split('/')[2]),
                                    FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                ],
                                {'Site': 'Supreme'}
                            )
                        )
                        HashStorage.add_target(link[0].hash())
                    else:
                        continue
            except SSLError:
                raise SSLError('Site is down')
            except etree.XMLSyntaxError:
                raise etree.XMLSyntaxError('Exception XMLDecodeError')
            return result

