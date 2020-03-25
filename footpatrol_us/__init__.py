from typing import List

from lxml import etree
import re
from requests import get
from user_agent import generate_user_agent
from requests.exceptions import ReadTimeout

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.footpatrol.com/campaign/New+In/brand/nike,jordan,adidas-originals/latest/?facet-new=latest&fp_sort_order=latest'
        self.interval: float = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[2],
                          self.name, 'https://www.footpatrol.com' + element.get('href'), self.interval)
            for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': self.user_agent,
                         'connection': 'keep-alive', 'cache-control': 'max-age=0',
                         'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                         'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                         'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                         'sec-fetch-user': '?1',
                         'accept-language': 'en-US,en;q=0.9'}
            ).text).xpath('//a[@data-e2e="product-listing-name"]')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: etree.Element = etree.HTML(get(
                    target.data,
                    headers={'user-agent': generate_user_agent(),
                             'connection': 'keep-alive', 'cache-control': 'max-age=0',
                             'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                             'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                             'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                             'sec-fetch-user': '?1',
                             'accept-language': 'en-US,en;q=0.9',
                             'referer': 'https://www.footpatrol.com/campaign/New+In/brand/nike,jordan,adidas-originals/latest/?facet-new=latest&fp_sort_order=latest'
                             }).text)

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
                    'footpatrol',
                    content.xpath('//img[@id=""]')[0].get('src'),
                    '',
                    (api.currencies['pound'], float(content.xpath('//span[@class="pri"]')[0].get('content').replace('£', ''))),
                    {},
                    tuple(size.replace('"', '') + ' UK' for size in re.findall(r'("\d.\d"|"\d{1}"|"\d\d.\d"|"\d\d")',content.xpath('//script[@type="text/javascript"]')[2].text)),
                    (('StockX', 'https://stockx.com/search/sneakers?s=' + content.xpath('//h1[@itemprop="name"]')[0].text.replace(' ', '%20')),
                    ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
                )
            )
        else:
            return api.SWaiting(target)

