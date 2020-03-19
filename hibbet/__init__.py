from typing import List

from lxml import etree
from requests import get
import re
from user_agent import generate_user_agent
from requests.exceptions import ReadTimeout

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.hibbett.com/launch-calendar/?prefn1=dtLaunch&prefv1=-120&srule=launch-date-desc'
        self.interval: float = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[3],
                          self.name, element.get('href'), self.interval)
            for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': self.user_agent,
                         'connection': 'keep-alive', 'cache-control': 'max-age=0',
                         'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                         'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                         'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                         'sec-fetch-user': '?1',
                         'accept-language': 'en-US,en;q=0.9'}
            ).text).xpath('//a[@class="name-link"]')
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
                             'referer': self.catalog
                             }, timeout=3).text)
                

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
                    'hibbet',
                    content.xpath('//a[@class="swatchanchor"]')[0].get('data-thumb').split('"')[3].replace(' ', ''),
                    '',
                    (api.currencies['dollar'], float(content.xpath('//span[@class="price-sales"]')[0].get('content'))),
                    {},
                    tuple((str(int(re.findall(r'size=....', size.get('href'))[0].split('=')[1]) / 10) + ' US',
                           size.get('href'))
                           for size in content.xpath('//a[@class="swatchanchor"]') if 'size' in size.get('href')),
                    ()
                )
            )
        else:
            return api.SWaiting(target)

