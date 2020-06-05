from typing import List, Union

from lxml import etree

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://www.slamjam.com/en_RU/man/new-in/this-week'
        self.interval: int = 1
        self.user_agent = 'Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko'

    @property
    def catalog(self) -> CatalogType:
        return api.CInterval(self.name, 3.)

    def execute(self, mode: int, content: Union[CatalogType, TargetType]) -> List[
        Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = [content]
        if mode == 0:
            links = list()
            counter = 0
            for element in etree.HTML(self.provider.get(self.link,
                                                        headers={'user-agent': self.user_agent}, proxy=True, mode=1)) \
                    .xpath('//div[@class="product "]'):
                if counter == 5:
                    break
                if 'air' in element.get('data-url') or 'yeezy' in element.get('data-url') or 'jordan' \
                        in element.get('data-url') or 'dunk' in element.get('data-url'):
                    links.append([api.Target('https://www.slamjam.com' + element.get('data-url'), self.name, 0),
                                  'https://www.slamjam.com' + element.get('data-url')])
                    counter += 1
            if len(links) == 0:
                return result
            for link in links:
                try:
                    if HashStorage.check_target(link[0].hash()):
                        page_content: etree.Element = etree.HTML(self.provider.get(link[1], mode=1, proxy=True,
                                                                                   headers={
                                                                                       'user-agent': self.user_agent}))
                        sizes = [api.Size(element.text + ' EU')
                                 for element in page_content.xpath('//select[@id="select-prenotation"]/option')
                                 if element.get('data-availability') == 'true']
                        name = page_content.xpath('//meta[@name="keywords"]')[0].get('content')
                        HashStorage.add_target(link[0].hash())
                        result.append(IRelease(
                            link[1],
                            'shopify-filtered',
                            name,
                            page_content.xpath('//div[@class="slider-data-large"]/div')[0].get('data-image-url'),
                            '',
                            api.Price(
                                api.CURRENCIES['RUB'],
                                float(page_content.xpath('//div[@itemprop="price"]')[0].text)
                            ),
                            api.Sizes(api.SIZE_TYPES[''], sizes),
                            [
                                FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                           name.replace(' ', '%20')),
                                FooterItem('Cart', 'https://www.slamjam.com/cart'),
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            {'Site': 'Slam Jam'}
                        )
                        )
                except etree.XMLSyntaxError:
                    raise etree.XMLSyntaxError('Exception XMLDecodeError')
        return result
