from datetime import datetime, timedelta, timezone
from re import findall
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
        self.link: str = 'https://www.footpatrol.com/campaign/New+In/?facet:new=latest&sort=latest'
        self.interval: int = 1
        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu ' \
                          'Chromium/79.0.3945.130 Chrome/79.0.3945.130 Safari/537.36 '

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, self.time_gen(), 21, 5, 1.2)

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=1, microsecond=0, tzinfo=timezone.utc).timestamp()

    def execute(self, mode: int, content: Union[CatalogType, TargetType]) -> List[
        Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = [content]
        if mode == 0:
            links = list()
            counter = 0
            for element in etree.HTML(self.provider.get(self.link, headers={'user-agent': self.user_agent}, mode=1
                                                        )).xpath('//a[@data-e2e="product-listing-name"]'):
                if counter == 200:
                    break
                if 'yeezy' in element.get('href') or 'air' in element.get('href') or 'sacai' in element.get('href') \
                        or 'dunk' in element.get('href') or 'retro' in element.get('href'):
                    links.append([api.Target('https://www.footpatrol.com' + element.get('href'), self.name, 0),
                                  'https://www.footpatrol.com' + element.get('href')])
                    counter += 1
            for link in links:
                try:
                    if HashStorage.check_target(link[0].hash()):
                        get_content = self.provider.get(link[1], headers={'user-agent': self.user_agent}, mode=1)
                        page_content: etree.Element = etree.HTML(get_content)
                        name = page_content.xpath('//meta[@name="title"]')[0].get('content').split(' |')[0]
                        sizes = [api.Size(size.replace('name:', '').replace('"', '') + ' UK')
                                 for size in findall(r'name:".*"', get_content)]
                        print(page_content.xpath('//meta[@name="twitter:data1"]')[0].get('content'))
                        HashStorage.add_target(link[0].hash())
                        result.append(IRelease(
                            link[1],
                            'footsites',
                            name,
                            page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                            '',
                            api.Price(
                                api.CURRENCIES['GBP'],
                                float(page_content.xpath('//meta[@name="twitter:data1"]')[0].get('content'))
                            ),
                            api.Sizes(api.SIZE_TYPES[''], sizes),
                            [
                                FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                           name.replace(' ', '%20')),
                                FooterItem('Cart', 'https://www.footpatrol.com/cart'),
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            {'Site': 'Footpatrol-UK'}
                        )
                        )
                except etree.XMLSyntaxError:
                    raise etree.XMLSyntaxError('Exception XMLDecodeError')
            if result or content.expired:
                content.timestamp = self.time_gen()
                content.expired = False

            result.append(content)
        return result
