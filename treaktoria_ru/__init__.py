from random import choice
from typing import List

from lxml import etree
from requests import get
from user_agent import generate_user_agent

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger

sizes_stock = ['[LOW]', '[HIGH]', '[MEDIUM]']


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.traektoria.ru/wear/keds/brand-nike/?price__from=6000&THING_TYPE=%D0%92%D0%AB%D0%A1%D0%9E%D0%9A%D0%98%D0%95+%D0%9A%D0%95%D0%94%D0%AB%7E%D0%9A%D0%95%D0%94%D0%AB%7E%D0%9A%D0%A0%D0%9E%D0%A1%D0%A1%D0%9E%D0%92%D0%9A%D0%98%7E%D0%9D%D0%98%D0%97%D0%9A%D0%98%D0%95+%D0%9A%D0%95%D0%94%D0%AB'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 30)

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
            available_sizes = []
            for size in content.xpath('//div[@class="choose_size_columns"]//span[@class="choose_size"]'):
                try:
                    last_size = available_sizes[-1].split(' ')[0]
                except IndexError:
                    last_size = 0
                if float(size.text) > float(last_size):
                    available_sizes.append(size.text + f' US {choice(sizes_stock)}')
                else:
                    break
            image = content.xpath('//a[@class="jqzoom"]')[0].get('href').replace('\'', '')
            if '.jfif' in image:
                image = 'https://ipadflava.com/wp-content/uploads/nike-sb-logo-21.jpg'
            else:
                image = 'https://www.traektoria.ru' + image.replace('\'', '')
            return api.SSuccess(
                self.name,
                api.Result(
                    content.xpath('//meta[@name="keywords"]')[0].get('content'),
                    target.data,
                    'russian-retailers',
                    image,
                    '',
                    (
                        api.currencies['RUB'],
                        float(content.xpath(
                            '//div[@class="price"]'
                        )[0].text.replace('\t', '').replace('\n', '').replace('\xa0', ''))
                    ),
                    {},
                    tuple(available_sizes),
                    (
                        ('StockX', 'https://stockx.com/search/sneakers?s=' +
                         content.xpath('//meta[@name="keywords"]')[0].get('content').replace(' ', '%20')
                         .replace('кеды', '').replace('Высокие', '').replace('Низкие', '')),
                        ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    )
                )
            )
        else:
            return api.SWaiting(target)
