from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from requests import exceptions
from user_agent import generate_user_agent

from scripts.keywords_finding import check_name
from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, ScriptStorage
from source.tools import LinearSmart


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://sneakerhead.ru/isnew/shoes/sneakers/'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=1, microsecond=0, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:

            ok, response = self.provider.request(self.link, headers={'user-agent': self.user_agent})

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.)]
                else:
                    raise response

            for element in etree.HTML(response.text).xpath('//a[@class="product-card__link"]'):
                if check_name(element.get('title').lower()):

                    try:
                        if HashStorage.check_target(
                                api.Target('https://sneakerhead.ru' + element.get('href'), self.name, 0).hash()):

                            ok, page_content = self.provider.request('https://sneakerhead.ru' + element.get('href'),
                                                                     headers={'user-agent': self.user_agent})

                            if not ok:
                                if isinstance(response, exceptions.Timeout):
                                    return [api.CInterval(self.name, 600.)]
                                else:
                                    raise response

                            page_content = etree.HTML(page_content.text)
                            sizes = [
                                size.text.replace('\n', '').replace(' ', '') + '+'
                                + f'http://static.sellars.cf/links?site=sneakerhead&id={size.get("data-id")}'
                                for size in page_content.xpath('//ul[@class="product-sizes__list '
                                                               'is-visible"]/li/button')
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
                                        FooterItem('Urban QT',
                                                   f'https://autofill.cc/api/v1/qt?storeId=sneakerhead&monitor={"https://sneakerhead.ru" + element.get("href")}'),
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
