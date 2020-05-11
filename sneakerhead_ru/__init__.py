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
        self.catalog: str = 'https://sneakerhead.ru/isnew/'
        self.user_agent = generate_user_agent()
        self.interval: int = 1

    def index(self) -> IndexType:
        return api.IInterval(self.name, 1)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(
                element.get('href').split('/')[3],
                self.name,
                f'https://sneakerhead.ru/{element.get("href")}', self.interval
            )
            for element in etree.HTML(get(self.catalog, headers={'user-agent': self.user_agent}).text)
                .xpath('//a[@class="product-card__link"]')
            if ('Кроссовки' in element.text
                or 'Обувь' in element.text) and ('Yeezy' in element.text or 'Jordan'
                                                 in element.text or 'Nike' in element.text)
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: etree.Element = etree.HTML(
                    get(target.data, self.user_agent).content)
                if content.xpath('//div[@class="sizes-chart-item selected"]') != () and \
                        content.xpath('//a[@class="size_range_name "]') != []:
                    available = True
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        except KeyError:
            return api.SFail(self.name, 'Wrong scheme')
        if available:
            return api.SSuccess(
                self.name,
                api.Result(
                    content.xpath('//meta[@itemprop="name"]')[0].get('content'),
                    target.data,
                    'russian-retailers',
                    content.xpath('//meta[@itemprop="image"]')[0].get('content'),
                    '',
                    (api.currencies['RUB'], float(content.xpath('//meta[@itemprop="price"]')[0].get('content'))),
                    {},
                    tuple((size.text.replace('\n', '')).replace(' ', '') for size in (content.xpath(
                        '//div[@class="flex-row sizes-chart-items-tab"]'))[0].xpath(
                        'div[@class="sizes-chart-item selected" or @class="sizes-chart-item"]')),
                    (
                        (
                            'StockX',
                            'https://stockx.com/search/sneakers?s=' + target.name.replace('Кроссовки', '')
                                .replace(' ', '%20')
                        ),
                        ('Cart', 'https://sneakerhead.ru/cart'),
                        ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    )
                )
            )
        else:
            return api.SSuccess(
                self.name,
                api.Result(
                    'Sold out',
                    target.data,
                    'tech',
                    '',
                    '',
                    (api.currencies['USD'], 1),
                    {},
                    tuple(),
                    (('StockX', 'https://stockx.com/search/sneakers?s='),
                     ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
                )
            )
