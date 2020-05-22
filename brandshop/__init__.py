from json import loads
from typing import List

from jsonpath2 import Path
from lxml import etree
from user_agent import generate_user_agent

from source import api
from source.api import IndexType, TargetType, StatusType
from source.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider):
        super().__init__(name, log, provider)
        self.catalog: str = 'https://brandshop.ru/New/'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 1200)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(
                element[0].get('href').split('/')[4],
                self.name,
                element[0].get('href'), self.interval)
            for element in etree.HTML(
                self.provider.get(
                    self.catalog,
                    headers={'user-agent': self.user_agent}
                )
            ).xpath('//div[@class="product"]')
            if 'krossovki' in element[0].get('href') and ('jordan' in element[0].get('href')
                                                          or 'yeezy' in element[0].get('href')
                                                          or 'air' in element[0].get('href')
                                                          or 'dunk' in element[0].get('href')
                                                          or 'force' in element[0].get('href')
                                                          or 'blaze' in element[0].get('href'))
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                content = etree.HTML(self.provider.get(target.data, headers={'user-agent': self.user_agent}))
                if len(content.xpath('//button')) != 0:
                    return api.SSuccess(
                        self.name,
                        api.Result(
                            content.xpath('//span[@itemprop="name"]')[0].text,
                            target.data,
                            'russian-retailers',
                            content.xpath('//meta[@property="og:image"]')[0].get('content'),
                            '',
                            (
                                api.currencies['RUB'],
                                float(content.xpath('//meta[@itemprop="price"]')[0].get('content'))
                            ),
                            {},
                            tuple(size.current_value for size in Path.parse_str('$.*.name').match(loads(
                                self.provider.get(
                                    f'https://brandshop.ru/getproductsize/{target.data.split("/")[4]}/',
                                    headers={'user-agent': generate_user_agent(), 'referer': target.data}
                                )))),
                            (
                                (
                                    'StockX',
                                    'https://stockx.com/search/sneakers?s=' + str(
                                        content.xpath('//span[@itemprop="brand"]')[0].text +
                                        content.xpath('//span[@itemprop="name"]')[0].text
                                    ).replace(' ', '%20').replace('\xa0', '%20')),
                                ('Cart', 'https://brandshop.ru/cart'),
                                ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            )
                        )
                    )
                else:
                    return api.SWaiting(target)
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
