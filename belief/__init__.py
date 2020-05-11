from typing import List

from lxml import etree
from requests import get

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://beliefmoscow.com/collection/obuv'
        self.interval: int = 1

    def index(self) -> IndexType:
        return api.IInterval(self.name, 1)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[4],
                          self.name, 'https://beliefmoscow.com' + element.get('href'), self.interval)
            for element in etree.HTML(get(
                url=self.catalog, headers={'user-agent': 'Mozilla/5.0 (compatible; YandexAccessibilityBot/3.0; '
                                                         '+http://yandex.com/bots)'}
            ).text).xpath('//a[@class="product_preview-image\n                product_preview-image--cover"]')
            if 'nike' in element.get('href') or 'yeezy' in element.get('href') or 'jordan' in element.get('href')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                content: etree.Element = etree.HTML(get(url=target.data,
                                                        headers={
                                                            'user-agent': 'Mozilla/5.0 (compatible; '
                                                                          'YandexAccessibilityBot/3.0; '
                                                                          '+http://yandex.com/bots)'}).text)
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
                'russian-retailers',
                content.xpath('//meta[@property="og:image"]')[0].get('content'),
                '',
                (api.currencies['RUB'],
                 float(content.xpath('//div[@class="product-page__price"]')[0].text.replace('₽', '').replace('\n', '')
                       .replace(' ', ''))),
                {},
                tuple(
                    (
                        size_data.text
                    ) for size_data in content.xpath('//select[@id="variant-select"]')[0].xpath('option')
                ),
                (('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                 ('Cart', 'https://beliefmoscow.com/cart'),
                 ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
            )
        )
