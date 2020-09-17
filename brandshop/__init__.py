from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from user_agent import generate_user_agent
import yaml
from scripts.keywords_finding import check_name

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem, \
    IAnnounce
from source.cache import HashStorage
from source.library import SubProvider
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://brandshop.ru/New/'
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
                    .xpath('//div[@class="product"]/a[@class="product-image"]'):

                if element.get('href') == 'javascript:void(0);':
                    result.append(IAnnounce(
                        'https://brandshop.ru/New/',
                        'brandshop',
                        element.xpath('img')[0].get('alt'),
                        element.xpath('img')[0].get('src'),
                        'Подробности скоро',
                        api.Price(api.CURRENCIES['RUB'], float(0)),
                        api.Sizes(api.SIZE_TYPES[''], []),
                        [
                            FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                       element.xpath('img')[0].get('alt')
                                       .replace(' ', '%20').replace('"', '').replace('\n', '').replace(' ', '')),
                            FooterItem('Cart', 'https://brandshop.ru/cart'),
                            FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                        ],
                        {'Site': 'Brandshop'}
                    ))

                elif check_name(element.xpath('img')[0].get('alt').lower(), self.absolute_keywords,
                                self.positive_keywords, self.negative_keywords):

                    try:
                        if HashStorage.check_target(api.Target(element.get('href'), self.name, 0).hash()):
                            page_content = etree.HTML(
                                self.provider.request(element.get('href'), headers={'user-agent': self.user_agent}).text
                            )
                            sizes = [api.Size(size.text) for size in page_content.xpath('//div[@class="sizeselect"]')]
                            name = page_content.xpath('//span[@itemprop="name"]')[0].text
                            HashStorage.add_target(api.Target(element.get('href'), self.name, 0).hash())
                            try:
                                is_only_offline = \
                                    page_content.xpath('//button[@class="btn btn-fluid btn-transparent"]')[0].text \
                                    == 'Доступен только в офлайн-магазине'
                            except Exception:
                                is_only_offline = False

                            if is_only_offline:
                                result.append(
                                    IRelease(
                                        element.get('href'),
                                        'brandshop-offline',
                                        name,
                                        page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                                        '',
                                        api.Price(
                                            api.CURRENCIES['RUB'],
                                            float(page_content.xpath('//meta[@itemprop="price"]')[0].get('content'))
                                        ),
                                        api.Sizes(api.SIZE_TYPES[''], sizes),
                                        [
                                            FooterItem('Cart', 'https://brandshop.ru/cart'),
                                            FooterItem('Login', 'https://brandshop.ru/login')
                                        ],
                                        {
                                            'Site': 'Brandshop',
                                            'Location': page_content.xpath('//div[@class="access"]')[0].text
                                        }
                                    )
                                )

                            else:
                                result.append(
                                    IRelease(
                                        element.get('href'),
                                        'brandshop',
                                        name,
                                        page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                                        '',
                                        api.Price(
                                            api.CURRENCIES['RUB'],
                                            float(page_content.xpath('//meta[@itemprop="price"]')[0].get('content'))
                                        ),
                                        api.Sizes(api.SIZE_TYPES[''], sizes),
                                        [
                                            FooterItem('Cart', 'https://brandshop.ru/cart'),
                                            FooterItem('Login', 'https://brandshop.ru/login')
                                        ],
                                        {'Site': 'Brandshop'}
                                    )
                                )

                    except etree.XMLSyntaxError:
                        raise etree.XMLSyntaxError('XMLDecodeEroor')
            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
