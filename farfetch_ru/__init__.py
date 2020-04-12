import re
from typing import List

from lxml import etree
from requests import get
from user_agent import generate_user_agent

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.farfetch.com/ru/sets/men/new-in-this-week-eu-men.aspx?view=180&scale=284&category=136361&designer=214504|1664|1205035'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 2)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[-1],
                          self.name, 'https://www.farfetch.com/' + element.get('href'), self.interval)
            for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': self.user_agent,
                         'connection': 'keep-alive', 'cache-control': 'max-age=0',
                         'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                         'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                         'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                         'sec-fetch-user': '?1',
                         'accept-language': 'en-US,en;q=0.9'}
            ).text).xpath('//a[@itemprop="itemListElement"]')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                for_content = get(
                    target.data,
                    headers={'user-agent': self.user_agent,
                             'connection': 'keep-alive', 'cache-control': 'max-age=0',
                             'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                             'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                             'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                             'sec-fetch-user': '?1',
                             'accept-language': 'en-US,en;q=0.9',
                             'referer': self.catalog
                             })
                content: etree.Element = etree.HTML(for_content.text)
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        name = content.xpath('//title')[0].text.replace('Кроссовки ', '').replace(' - Farfetch', '')
        return api.SSuccess(
            self.name,
            api.Result(
                name,
                target.data,
                'farfetch',
                re.findall(r'(https?://[\S]+jpg)', str(for_content.content))[19].split('"600":"')[-1],
                '',
                (
                    api.currencies['RUB'],
                    float(content.xpath(
                        '//span[@data-tstid="priceInfo-original"]'
                    )[0].text.replace('₽', '').replace('\xa0', ''))
                ),
                {},
                tuple(size.text + 'US' for size in content.xpath('//span[@data-tstid="sizeDescription"]')),
                (
                    ('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                    ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                )
            )
        )
