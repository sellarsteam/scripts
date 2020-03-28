from typing import List

from lxml import etree
from requests import get
from user_agent import generate_user_agent

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger

def get_sizes(url, content) -> tuple:
    sizes = list()
    last_size = 0.0
    for size in content.xpath('//form[@method="post"]//select[@name="id"]//option[@value]'):
        size_for_list = size.text.split(' /')[0].replace('\n', '').replace(' ', '')
        if content.xpath('//meta[@name="twitter:description"]')[0].get('content').split(' ')[2] in size.text:
            if last_size < float(str(size_for_list.replace('C', '').replace('W', '').replace('Y', ''))):
                sizes.append((size_for_list, url + '?variant=' + size.get('value')))
                last_size = float(str(size_for_list.replace('C', '').replace('W', '').replace('Y', '')))
            else:
                break
    return tuple(sizes)


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://packershoes.com/collections/new-arrivals/sneakers?page=1'
        self.interval: float = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[4],
                          self.name, 'https://packershoes.com' + element.get('href'), self.interval)
            for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': self.user_agent,
                         'connection': 'keep-alive', 'cache-control': 'max-age=0',
                         'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                         'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                         'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                         'sec-fetch-user': '?1',
                         'accept-language': 'en-US,en;q=0.9'}
            ).text).xpath('//a[@class="grid-product__meta"]') if 'nike' in element.get('href').split('/')[4] or
                           'jordan' in element.get('href').split('/')[4] or 'yeezy' in element.get('href').split('/')[4]
                           or 'force' in element.get('href').split('/')[4]
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                content: etree.Element = etree.HTML(get(
                    target.data,
                    headers={'user-agent': self.user_agent,
                             'connection': 'keep-alive', 'cache-control': 'max-age=0',
                             'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                             'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                             'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                             'sec-fetch-user': '?1',
                             'accept-language': 'en-US,en;q=0.9',
                             'referer': self.catalog
                             }).text)
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        name = content.xpath('//meta[@property="og:title"]')[0].get('content')
        return api.SSuccess(
            self.name,
            api.Result(
                name,
                target.data,
                'shopify-filtered',
                content.xpath('//meta[@property="og:image"]')[0].get('content').split('?')[0],
                '',
                (api.currencies['dollar'], float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content').replace(',',''))),
                {},
                get_sizes(target.data, content),
                (('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
            )
        )