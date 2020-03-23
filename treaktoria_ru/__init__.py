from typing import List

from lxml import etree
import re
from requests import get
from user_agent import generate_user_agent

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.traektoria.ru/wear/keds/brand-nike/?price__from=6000&THING_TYPE=%D0%92%D0%AB%D0%A1%D0%9E%D0%9A%D0%98%D0%95+%D0%9A%D0%95%D0%94%D0%AB%7E%D0%9A%D0%95%D0%94%D0%AB%7E%D0%9A%D0%A0%D0%9E%D0%A1%D0%A1%D0%9E%D0%92%D0%9A%D0%98%7E%D0%9D%D0%98%D0%97%D0%9A%D0%98%D0%95+%D0%9A%D0%95%D0%94%D0%AB'
        self.interval: float = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[2],
                          self.name, 'https://www.traektoria.ru' + element.get('href'), self.interval)
            for element in etree.HTML(get(
                self.catalog,
                headers={'user-agent': self.user_agent,
                         'connection': 'keep-alive', 'cache-control': 'max-age=0',
                         'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                         'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                         'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                         'sec-fetch-user': '?1',
                         'accept-language': 'en-US,en;q=0.9'}
            ).text).xpath('//a[@class="p_link"]')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: etree.Element = etree.HTML(get(
                    target.data,
                    headers={'user-agent': generate_user_agent(),
                             'connection': 'keep-alive', 'cache-control': 'max-age=0',
                             'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                             'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                             'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                             'sec-fetch-user': '?1',
                             'accept-language': 'en-US,en;q=0.9',
                             'referer': self.catalog
                             }).text)

                if content.xpath('//input[@class="btn buy kdxAddToCart"]') != []:
                    available = True
                else:
                    return api.SFail(self.name, 'Item is sold out')
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        if available:
            return api.SSuccess(
                self.name,
                api.Result(
                    content.xpath('//meta[@name="keywords"]')[0].get('content'),
                    target.data,
                    'traektoria_ru',
                    'https://www.traektoria.ru' + content.xpath('//a[@class="jqzoom"]')[0].get('href').replace('\'', ''),
                    '',
                    (api.currencies['ruble'], float(content.xpath('//div[@class="price"]')[0].text.replace('\t', '').replace('\n', '').replace('\xa0', ''))),
                    {},
                    tuple(size.text + ' US' for size in content.xpath('//span[@class="choose_size"]')),
                    ()
                )
            )
        else:
            return api.SWaiting(target)
