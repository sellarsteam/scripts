from datetime import datetime, timedelta, timezone
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
        self.link: str = 'https://www.bapeonline.com/bape/men/?prefn1=isNew&prefv1=true&srule=newest&start=0&sz=48'
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
            .replace(second=2, microsecond=250000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            links = []
            counter = 0
            catalog_links = etree.HTML(self.provider.get(self.link,
                                                         headers={'user-agent': self.user_agent}, proxy=True)) \
                .xpath('//a[@class="thumb-link"]')
            if not catalog_links:
                raise ConnectionResetError('Shopify banned this IP')
            for element in catalog_links:
                if counter == 5:
                    break
                if element.get('href')[0] != '/':
                    links.append(api.Target(element.get('href'), self.name, 0))
                    counter += 1

            for link in links:
                try:
                    if HashStorage.check_target(link.hash()):
                        get_content = self.provider.get(link.name, headers={'user-agent': self.user_agent}, proxy=True)
                        page_content = etree.Element = etree.HTML(get_content)
                        sizes = [
                            api.Size(size.text.replace(' ', '').replace('\n', ''), size.get('value'))
                            for size in page_content.xpath('//select[@class="variation-select"]/option')
                            if ('UNAVAILABLE' not in size.text or
                                'OUTOFSTOCK' not in size.text) and 'Select Size' not in size.text
                        ]
                        name = page_content.xpath('//meta[@property="og:title"]')[0].get('content')
                        HashStorage.add_target(link.hash())
                        result.append(IRelease(
                            link.name,
                            'bape',
                            name,
                            page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                            '',
                            api.Price(
                                api.CURRENCIES['USD'],
                                float(
                                    page_content.xpath('//div[@class="headline4 pdp-price-sales"]')[0]
                                        .text.split('$')[-1].replace(' ', '').replace('\n', '')
                                )
                            ),
                            api.Sizes(api.SIZE_TYPES[''], sizes),
                            [
                                FooterItem('StockX',
                                           'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                                FooterItem('Cart', 'https://www.bapeonline.com/cart'),
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            {'Site': 'Bape'}
                        ))
                    else:
                        continue
                except etree.XMLSyntaxError:
                    raise etree.XMLSyntaxError('Exception XMLDecodeError')
            if result or content.expired:
                content.timestamp = self.time_gen()
                content.expired = False

            result.append(content)
        result.append(content)
        return result
