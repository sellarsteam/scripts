from typing import List
from json import loads

from lxml import etree
from requests import get
from user_agent import generate_user_agent
from jsonpath2 import Path

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://brandshop.ru/new/'
        self.interval: float = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:
        for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': self.user_agent}
        ).content).xpath('//div[@class="product-container"]'):
            print(element.xpath('//h2/span')[0].text)
        return [
            api.TInterval(element.xpath('div[@class="product"]')[0].get('data-product-id'),
                          self.name, element.xpath('div[@class="product"]')[0].xpath('a[@href]')[0].get('href'), self.interval)
            for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': self.user_agent}
            ).content).xpath('//div[@class="product-container"]')
            if 'Кроссовки' in element.xpath('//h2/span')[0].text or 'кроссовки' in element.xpath('//h2/span')[0].text
               and element.xpath('div[@class="product"]')[0].xpath('a[@href]')[0].get('href') != 'javascript:void(0);'
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                content = etree.HTML(get(target.data, self.user_agent).content)
                if content.xpath('//button[@title="Добавить в корзину"]') is not None:
                    return api.SSuccess(
                        self.name,
                        api.Result(
                            content.xpath('//span[@itemprop="brand"]')[0].text,
                            target.data,
                            'brandshop',
                            content.xpath('//img[@itemprop="image"]')[0].get('src'),
                            '',
                            (api.currencies['ruble'], float(content.xpath('//meta[@itemprop="price"]')[0].get('content'))),
                            {},
                            tuple(size.current_value for size in Path.parse_str('$.*.name').match(loads(
                                get(f'https://brandshop.ru/getproductsize/{target.data.split("/")[4]}/',
                                    headers={'user-agent': generate_user_agent(), 'referer': target.data}).content))),
                            ()
                        )
                    )
                else:
                    return api.SFail(self.name, 'Unknown "publishType"')
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')