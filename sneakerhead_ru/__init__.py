from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from user_agent import generate_user_agent
import yaml
from scripts.keywords_finding import check_name

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://sneakerhead.ru/isnew/shoes/sneakers/'
        self.interval: int = 1

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
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 3, 15))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=7, microsecond=0, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            for element in etree.HTML(self.provider.request(self.link, headers={'user-agent': self.user_agent}).text) \
                    .xpath('//a[@class="product-card__link"]'):
                if check_name(element.get('title').lower(),
                              self.absolute_keywords, self.positive_keywords, self.negative_keywords):
                    try:
                        if HashStorage.check_target(
                                api.Target('https://sneakerhead.ru' + element.get('href'), self.name, 0).hash()):
                            page_content = etree.HTML(
                                self.provider.request('https://sneakerhead.ru' + element.get('href'),
                                                      headers={'user-agent': self.user_agent}).text)
                            sizes = [
                                size.text.replace('\n', '').replace(' ', '') + '+'
                                + f'http://static.sellars.cf/links?site=sneakerhead&id={size.get("data-id")}'
                                for size in
                                page_content.xpath('//div[@class="flex-row sizes-chart-items-tab"]')[0].xpath(
                                    'div[@class="sizes-chart-item selected" or @class="sizes-chart-item"]')
                            ]
                            name = page_content.xpath('//meta[@itemprop="name"]')[0].get('content')
                            HashStorage.add_target(api.Target('https://sneakerhead.ru' + element.get('href')
                                                              , self.name, 0).hash())
                            try:
                                if sizes[0][-1].split('+')[0].isdigit():
                                    symbol = ' US'
                                else:
                                    symbol = ''
                            except IndexError:
                                symbol = ''
                            result.append(
                                IRelease(
                                    'https://sneakerhead.ru' + element.get('href'),
                                    'sneakerhead',
                                    name,
                                    page_content.xpath('//meta[@itemprop="image"]')[0].get('content'),
                                    '',
                                    api.Price(
                                        api.CURRENCIES['RUB'],
                                        float(page_content.xpath('//meta[@itemprop="price"]')[0].get('content'))
                                    ),
                                    api.Sizes(api.SIZE_TYPES[''], [api.Size(size.split('+')[0] + symbol,
                                                                            size.split('+')[-1])
                                                                   for size in sizes]),
                                    [
                                        FooterItem(
                                            'StockX',
                                            'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20').
                                            replace('"', '').replace('\n', '').replace(' ', '')
                                        ),
                                        FooterItem('Cart', 'https://sneakerhead.ru/cart'),
                                        FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                    ],
                                    {'Site': 'Sneakerhead'}
                                )
                            )
                    except etree.XMLSyntaxError:
                        raise etree.XMLSyntaxError('XMLDecodeEroor')
            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
