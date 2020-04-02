from json import loads
from typing import List

from jsonpath2 import Path
from lxml import etree
from requests import get
from user_agent import generate_user_agent

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://brandshop.ru/new/'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 30)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(
                element.xpath('div[@class="product" or @class="product outofstock"]')[0].get('data-product-id'),
                self.name,
                element.xpath(
                    'div[@class="product" or @class="product outofstock"]'
                )[0].xpath('a[@href]')[0].get('href'), self.interval)
            for element in etree.HTML(
                get(
                    self.catalog,
                    headers={'user-agent': self.user_agent}
                ).text
            ).xpath('//div[@class="product-container"]')
            if 'krossovki' in element.xpath(
                'div[@class="product" or @class="product outofstock"]'
            )[0].xpath('a[@href]')[0].get('href')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                content = etree.HTML(get(target.data, self.user_agent).content)
                if content.xpath('//button[@title="Добавить в корзину"]') is not None:
                    return api.SSuccess(
                        self.name,
                        api.Result(
                            content.xpath('//span[@itemprop="brand"]')[0].text +
                            content.xpath('//span[@itemprop="name"]/text()[2]')[0],
                            target.data,
                            'russian-retailers',
                            content.xpath('//img[@itemprop="image"]')[0].get('src'),
                            '',
                            (
                                api.currencies['RUB'],
                                float(content.xpath('//meta[@itemprop="price"]')[0].get('content'))
                            ),
                            {},
                            tuple(size.current_value for size in Path.parse_str('$.*.name').match(loads(
                                get(
                                    f'https://brandshop.ru/getproductsize/{target.data.split("/")[4]}/',
                                    headers={'user-agent': generate_user_agent(), 'referer': target.data}
                                ).content))),
                            (
                                (
                                    'StockX',
                                    'https://stockx.com/search/sneakers?s=' + (
                                            content.xpath('//span[@itemprop="brand"]')[0].text +
                                            content.xpath('//span[@itemprop="name"]/text()[2]')[0]
                                    ).replace(' ', '%20').replace('\xa0', '%20')),
                                ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            )
                        )
                    )
                else:
                    return api.SFail(self.name, 'Unknown "publishType"')
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
