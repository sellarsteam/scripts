from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from user_agent import generate_user_agent
import yaml

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from requests import post
from source.library import SubProvider
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://www.itkkit.ru/ajax/RetailRocket.php'
        self.post_data = {"query": "UpSellItemToItems", "rr_params": [155660], "temp": 'new'}
        self.headers = {
            'Host': 'www.itkkit.ru',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Content-Length': '49',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }

        raw = yaml.safe_load(open('./scripts/keywords.yaml'))

        if isinstance(raw, dict):
            if 'absolute' in raw and isinstance(raw['absolute'], list) \
                    and 'positive' in raw and isinstance(raw['positive'], list) \
                    and 'negative' in raw and isinstance(raw['negative'], list):
                self.absolute_keywords = raw['absolute']
                self.positive_keywords = raw['positive']
                self.negative_keywords = raw['negative']
            else:
                raise TypeError('Keywords must be list')
        else:
            raise TypeError('Types of keywords must be in dict')
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=0, microsecond=500000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            try:
                response = post(url=self.link, data=self.post_data, headers=self.headers)

            except (ConnectionError, TimeoutError):
                return [api.CInterval(self.name, 300)]

            for element in etree.HTML(response.text).xpath(
                    '//div[@class="grid-row"]/div/a'):

                if 'Sold' not in element.xpath('div[@class="catalog-item__title"]')[0].xpath(
                        'div[@class="catalog-item__title-name"]')[0].text:
                    try:
                        if HashStorage.check_target(
                                 api.Target('https://www.itkkit.ru' + element.get('href'), self.name, 0).hash()):

                            sizes = api.Sizes(
                                api.SIZE_TYPES[''],
                                [
                                    api.Size(size.replace(' US', '') + ' US')
                                    for size in element.xpath('div[@class="catalog-item__img-wrapper"]'
                                                              '/div[@class="catalog-item__img-hover"]/div')[0].text
                                    .split(' US ')
                                ]
                            )

                            name = element.xpath('div[@class="catalog-item__title"]/div')[-1].text

                            image = 'https://www.itkkit.ru' + \
                                    element.xpath('div[@class="catalog-item__img-wrapper"]'
                                                  '/div[@class="catalog-item__img-list"]'
                                                  '/div[@class="catalog-item__img"]/picture/img')[0].get('data-lazy')

                            price = api.Price(api.CURRENCIES['EUR'],
                                              float(element.xpath(
                                                  'div[@class="catalog-item__price"]/div/div/span/span')
                                                    [0].text.replace(' ', '').split('.')[0]))
                            HashStorage.add_target(
                                api.Target('https://www.itkkit.ru' + element.get('href'), self.name, 0).hash())
                            result.append(
                                IRelease(
                                    'https://www.itkkit.ru' + element.get('href'),
                                    'itkkit',
                                    name,
                                    image,
                                    '',
                                    price,
                                    sizes,
                                    [
                                        FooterItem('Cart', 'https://www.itkkit.ru/checkout/'),
                                        FooterItem('QT Urban', 'https://autofill.cc/api/v1/qt?storeId=itkkit&monitor='
                                                   + 'https://www.itkkit.ru' + element.get('href'))
                                    ],
                                    {'Site': 'ITK Kit'}
                                )
                            )
                    except etree.XMLSyntaxError:
                        raise etree.XMLSyntaxError('XMLDecodeEroor')
            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
