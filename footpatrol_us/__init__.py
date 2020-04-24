import re
from typing import List

from lxml import etree
from cfscrape import create_scraper
from requests import ReadTimeout

from scripts.proxy import get_proxy
from user_agent import generate_user_agent
from scripts.proxy import get_proxy
import time
from random import choice

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.footpatrol.com/campaign/New+In/brand/nike,jordan,adidas-originals/latest/?facet-new=latest&fp_sort_order=latest'
        self.interval: int = 1
        self.scrapper = create_scraper()
        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/79.0.3945.130 Chrome/79.0.3945.130 Safari/537.36'

    def index(self) -> IndexType:
        return api.IInterval(self.name, 5)

    def targets(self) -> List[TargetType]:
        try:
            return [
                api.TInterval(element.get('href').split('/')[2],
                              self.name, 'https://www.footpatrol.com' + element.get('href'), self.interval)
                for element in etree.HTML(self.scrapper.get(
                    self.catalog, headers={'user-agent': choice(['Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                                                                 '(KHTML, like Gecko) Ubuntu Chromium/79.0.3945.130 '
                                                                 'Chrome/79.0.3945.130 Safari/537.36',
                                                                 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.11 ('
                                                                 'KHTML, like Gecko) Ubuntu/14.04.6 Chrome/81.0.3990.0 '
                                                                 'Safari/537.36', 'Mozilla/5.0 (X11; U; Linux x86_64; en-US) AppleWebKit/540.0 (KHTML, like Gecko) Ubuntu/10.10 Chrome/9.1.0.0 Safari/540.0', 'Mozilla/5.0 (X11; U; Linux x86_64; en-US) AppleWebKit/540.0 (KHTML, like Gecko) Ubuntu/10.10 Chrome/8.1.0.0 Safari/540.0'])}, proxies=get_proxy(),
                    timeout=3).text).xpath(
                    '//a[@data-e2e="product-listing-name"]') if
                'yeezy' in element.get('href') or
                'jordan' in element.get('href') or
                'air' in element.get('href') or
                'sacai' in element.get('href') or
                'zoom' in element.get('href') or
                'dunk' in element.get('href')
            ]
        except ReadTimeout:
            return []

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: etree.Element = etree.HTML(self.scrapper.get(target.data, headers={
                    'user-agent': self.user_agent}).text)

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
