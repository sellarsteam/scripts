from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from requests import exceptions
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem, \
    IAnnounce
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = 'https://brandshop.ru/New/'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 6, 10))

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

            ok, response = self.provider.request(self.link, headers={'user-agent': self.user_agent})

            if not ok:

                if isinstance(response, exceptions.Timeout) or isinstance(response, exceptions.ConnectionError):
                    return [api.CInterval(self.name, 300)]

                else:
                    raise response

            for element in etree.HTML(response.text) \
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

                elif Keywords.check(element.xpath('img')[0].get('alt').lower()):

                    try:
                        if HashStorage.check_target(api.Target(element.get('href'), self.name, 0).hash()):

                            ok, response_item = self.provider.request(element.get('href'),
                                                                      headers={'user-agent': self.user_agent})

                            if not ok:

                                if isinstance(response, exceptions.Timeout) \
                                        or isinstance(response, exceptions.ConnectionError):
                                    return [api.CInterval(self.name, 300)]

                                else:
                                    raise response

                            page_content = etree.HTML(
                                response_item.text
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
                                location = page_content.xpath('//div[@class="access"]')[0].text
                                if 'петров' in location.lower():
                                    taxi_link = 'https://3.redirect.appmetrica.yandex.com/route?end-lat=55.767851&end' \
                                                '-lon=37.618764&appmetrica_tracking_id=1178268795219780156&app_code=3'
                                elif 'полян' in location.lower():
                                    taxi_link = 'https://3.redirect.appmetrica.yandex.com/route?end-lat=55.730548&end' \
                                                '-lon=37.623233&appmetrica_tracking_id=1178268795219780156&app_code=3'
                                else:
                                    taxi_link = 'https://3.redirect.appmetrica.yandex.com/route?end-lat=55.730548&end' \
                                                '-lon=37.623233&appmetrica_tracking_id=1178268795219780156&app_code=3'

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
                                            'Location': location,
                                            'Taxi': f"[Вызов такси до магазина]({taxi_link}) 🚕"
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
