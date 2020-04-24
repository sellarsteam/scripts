import re
from typing import List

from lxml import etree
from user_agent import generate_user_agent
from cfscrape import create_scraper
from scripts.proxy import get_proxy

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.scraper = create_scraper()
        self.catalog: str = 'https://www.hibbett.com/launch-calendar/?prefn1=dtLaunch&prefv1=30'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 1200)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[3],
                          self.name, element.get('href'), self.interval)
            for element in etree.HTML(self.scraper.get(
                url=self.catalog, proxies=get_proxy()
            ).text).xpath('//a[@class="name-link"]') if 'dunk' in element.get('href') or 'yeezy' in element.get('href') or 'jordan' in element.get('href') or 'sacai' in element.get('href') or 'air' in element.get('href')
        ][0:5:]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: etree.Element = etree.HTML(self.scraper.get(url=target.data, proxies=get_proxy()).text)

                if len(content.xpath('//a[@class="swatchanchor"]')) > 0:
                    available = True
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        if available:
            return api.SSuccess(
                self.name,
                api.Result(
                    content.xpath('//meta[@name="keywords"]')[0].get('content'),
                    target.data,
                    'hibbett',
                    content.xpath('//a[@class="swatchanchor"]')[0].get('data-thumb').split('"')[3].replace(' ', ''),
                    '',
                    (api.currencies['USD'], float(content.xpath('//span[@class="price-sales"]')[0].get('content'))),
                    {},
                    tuple((str(int(re.findall(r'size=....', size.get('href'))[0].split('=')[1]) / 10) + ' US',
                           size.get('href'))
                          for size in content.xpath('//a[@class="swatchanchor"]') if 'size' in size.get('href')),
                    (('StockX', 'https://stockx.com/search/sneakers?s=' + content.xpath('//meta[@name="keywords"]')[0]
                      .get('content').replace(' ', '%20')),
                     ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
                )
            )
        else:
            return api.SWaiting(target)
