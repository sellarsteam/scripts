from typing import List

from lxml import etree
from requests import get
from requests.exceptions import SSLError
from user_agent import generate_user_agent

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.supremenewyork.com/shop/all'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 60)

    def targets(self) -> List[TargetType]:
        try:
            return [
                api.TInterval(element.get('href').split('/')[4],
                              self.name, element.get('href'), self.interval)
                for element in etree.HTML(get(
                    self.catalog,
                    headers={'user-agent': self.user_agent}
                ).content).xpath('//a[@style="height:81px;"]') if len(element.xpath('div[@class="sold_out_tag"]')) == 0
            ]
        except SSLError:
            raise api.ScriptError('Site is down')

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                content: etree.Element = etree.HTML(
                    get(self.catalog.replace('/shop/all', '') + target.data, self.user_agent).content)
            else:
                return api.SFail(self.name, 'Unknown target type')
        except SSLError:
            return api.SFail(self.name, 'Site is down')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        return api.SSuccess(
            self.name,
            api.Result(
                content.xpath('//h1[@itemprop="name"]')[0].text,
                self.catalog.replace('/shop/all', '') + target.data,
                'supreme-nyc',
                'https://' + content.xpath('//img[@itemprop="image"]')[0].get('src').replace('//', ''),
                content.xpath('//p[@itemprop="description"]')[0].text,
                (api.currencies['EUR'], float(content.xpath('//span[@itemprop="price"]')[0].text.replace('€', ''))),
                {'Цвет': content.xpath('//p[@itemprop="model"]')[0].text},
                tuple(size.text for size in content.xpath('//option[@value]')),
                (
                    ('StockX', 'https://stockx.com/search?s=' +
                     content.xpath('//h1[@itemprop="name"]')[0].text.replace(' ', '%20').replace('®', '')),
                    ('Mobile', 'https://www.supremenewyork.com/mobile#products/' +
                     content.xpath('//form[@class="add"]')[0].get('action').split('/')[2]),
                    ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                )
            )
        )
