import re
from typing import List

from lxml import etree
from user_agent import generate_user_agent

from source import api
from source.api import IndexType, TargetType, StatusType
from source.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider):
        super().__init__(name, log, provider)
        self.catalog: str = 'https://www.farfetch.com/ru/sets/men/new-in-this-week-eu-men.aspx?view=180&scale=284' \
                            '&category=136361&designer=214504|1664|1205035 '
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 10)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[-1],
                          self.name, 'https://www.farfetch.com/' + element.get('href'), self.interval)
            for element in etree.HTML(self.provider.get(
                self.catalog,
                headers={'user-agent': self.user_agent,
                         'connection': 'keep-alive', 'cache-control': 'max-age=0',
                         'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                         'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,'
                                   '*/*;q=0.8',
                         'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                         'sec-fetch-user': '?1',
                         'accept-language': 'en-US,en;q=0.9'}
            )).xpath('//a[@itemprop="itemListElement"]')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                for_content = self.provider.get(
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
                content: etree.Element = etree.HTML(for_content)
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
                re.findall(r'(https?://[\S]+jpg)', str(for_content))[19].split('"600":"')[-1],
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
                    ('Cart', 'https://www.farfetch.com/cart'),
                    ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                )
            )
        )
