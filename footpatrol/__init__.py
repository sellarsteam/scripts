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
        self.catalog: str = 'https://www.footpatrol.com/footwear/brand/nike,jordan,adidas-originals,converse,adidas/latest/?fp_sort_order=latest'
        self.interval: float = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:
        while True:
            try:
                return [
                    api.TInterval(element.get('href').split('/')[2],
                                  self.name, 'https://www.footpatrol.com/product/' + element.get('href'), self.interval)
                    for element in etree.HTML(get(
                        self.catalog,
                        headers={'user-agent': self.user_agent,
                                 'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                                 'accept-language': 'en-US,en;q=0.8',
                                 'upgrade-insecure-requests': '1'}, timeout=1
                    ).text).xpath('//a[@data-e2e="product-listing-name"]')
                ]
            except ReadTimeout:
                pass

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                while True:
                    try:
                        content: etree.Element = etree.HTML(get(
                            'https://www.footpatrol.com/product/white-converse-x-the-soloist-all-star-disrupt/370322_footpatrolcom/',
                            headers={'user-agent': generate_user_agent(),
                                     'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                                     'accept-language': 'en-US,en;q=0.8',
                                     'upgrade-insecure-requests': '1',
                                     'referer': "https://www.footpatrol.com/footwear/brand/nike,jordan,adidas-originals,converse,adidas/latest/?fp_sort_order=latest"
                                     }, timeout=1).text)
                        break
                    except ReadTimeout:
                        pass

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
                    content.xpath('//source[@srcset]')[0].get('srcset').split('1x')[0],
                    '',
                    (api.currencies['pound'], float(content.xpath('//span[@class="pri"]')[0].get('content').replace('£', ''))),
                    {},
                    tuple(size.replace('"', '') + ' UK' for size in re.findall(r'("\d.\d"|"\d{1}"|"\d\d.\d"|"\d\d")',content.xpath('//script[@type="text/javascript"]')[2].text)),
                    ()
                )
            )
        else:
            return api.SWaiting(target)
