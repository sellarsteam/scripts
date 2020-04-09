import re
from typing import List

from lxml import etree
from cfscrape import create_scraper
from scripts.proxy import get_proxy

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.footpatrol.com/campaign/New+In/brand/nike,jordan,adidas-originals/latest/?facet-new=latest&fp_sort_order=latest'
        self.interval: int = 1
        self.scrapper = create_scraper()


    def index(self) -> IndexType:
        return api.IInterval(self.name, 10)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[2],
                          self.name, 'https://www.footpatrol.com' + element.get('href'), self.interval)
            for element in etree.HTML(self.scrapper.get(
                self.catalog, proxies=get_proxy()).text).xpath('//a[@data-e2e="product-listing-name"]') if 'yeezy' in element.get('href') or
                                                                                      'jordan' in element.get('href') or
                                                                                      'air' in element.get('href') or
                                                                                      'sacai' in element.get('href') or
                                                                                      'zoom' in element.get('href') or
                                                                                      'dunk' in element.get('href')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: etree.Element = etree.HTML(self.scrapper.get(target.data, proxies=get_proxy()).text)

                if content.xpath('//button[@id="addToBasket"]') != []:
                    available = True
                else:
                    return api.SFail(self.name, 'Item is sold out')
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        if available:
            return api.SSuccess(
                self.name,
                api.Result(
                    content.xpath('//h1[@itemprop="name"]')[0].text,
                    target.data,
                    'footsites',
                    content.xpath('//img[@id=""]')[0].get('src'),
                    '',
                    (
                        api.currencies['GBP'],
                        float(content.xpath('//span[@class="pri"]')[0].get('content').replace('£', ''))
                    ),
                    {},
                    tuple(size.replace('"', '') + ' UK' for size in re.findall(
                        r'("\d.\d"|"\d{1}"|"\d\d.\d"|"\d\d")',
                        content.xpath('//script[@type="text/javascript"]')[2].text)),
                    (
                        ('StockX', 'https://stockx.com/search/sneakers?s=' + content.xpath(
                            '//h1[@itemprop="name"]'
                        )[0].text.replace(' ', '%20')),
                        ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    )
                )
            )
        else:
            return api.SWaiting(target)


