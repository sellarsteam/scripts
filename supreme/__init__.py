from typing import List

from lxml import etree
from requests import get
from user_agent import generate_user_agent

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


# TODO: Add exception, when incorrectly scheme of xml


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.supremenewyork.com/shop/all'
        self.interval: float = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[4],
                          self.name, element.get('href'), self.interval)
            for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': self.user_agent}
            ).content).xpath('//a[@style="height:81px;"]')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: etree.Element = etree.HTML(
                    get(self.catalog.replace('/shop/all', '') + target.data, self.user_agent).content)
                if content.xpath('//input[@value="add to basket"]') != None:
                    available = True
                else:
                    return api.SFail(self.name, 'Unknown "publishType"')
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        if available:
            return api.SSuccess(
                self.name,
                api.Result(
                    content.xpath('//h1[@itemprop="name"]')[0].text,
                    self.catalog.replace('/shop/all', '') + target.data,
                    'supreme',
                    'https://' + content.xpath('//img[@itemprop="image"]')[0].get('src').replace('//', ''),
                    content.xpath('//p[@itemprop="description"]')[0].text,
                    (api.currencies['euro'], float(content.xpath('//span[@itemprop="price"]')[0].text.replace('€', ''))),
                    {'Цвет': content.xpath('//p[@itemprop="model"]')[0].text},
                    tuple(size.text for size in content.xpath('//option[@value]')),
                    ()
                )
            )
        else:
            return api.SWaiting(target)