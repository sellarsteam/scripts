from typing import List, Union

from lxml import etree
from pycurl_requests import exceptions
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem, \
    IAnnounce
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.link: str = 'https://brandshop.ru/sneakers/?utm_source=telegram&utm_medium=post&utm_campaign=sneakers_23nov'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> api.CatalogType:
        return api.CInterval(self.name, 10)

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:

            ok, response = self.provider.request(self.link, headers={'user-agent': self.user_agent}, proxy=True)

            if not ok:

                if isinstance(response, exceptions.Timeout) or isinstance(response, exceptions.ConnectionError):
                    return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]

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
                        {'Site': '[Brandshop](https://brandshop.ru)'}
                    ))
                elif self.kw.check(element.xpath('img')[0].get('alt').lower()):
                    result.append(api.TInterval(element.get('href'), self.name, 0, 1))

        if mode == 1:

            target = api.Target(content.name, self.name, 0)

            try:
                if HashStorage.check_target(target.hash()):
                    HashStorage.add_target(target.hash())
                    additional_columns = {'Site': '[Brandshop](https://brandshop.ru)'}
                else:
                    additional_columns = {'Site': '[Brandshop](https://brandshop.ru)', 'Type': 'Restock'}

                ok, response = self.provider.request(content.name,
                                                     headers={'user-agent': self.user_agent}, proxy=True)

                if not ok:

                    if isinstance(response, exceptions.Timeout) \
                            or isinstance(response, exceptions.ConnectionError):
                        return [api.CInterval(self.name, 300), api.MAlert('Script go to sleep', self.name)]

                    else:
                        raise response

                page_content = etree.HTML(
                    response.text
                )

                sizes = api.Sizes(api.SIZE_TYPES[''], [api.Size(size.text) for size in page_content.xpath('//div[@class="sizeselect"]')])
                name = page_content.xpath('//span[@itemprop="name"]')[0].text
                try:
                    is_only_offline = \
                        page_content.xpath('//button[@class="btn btn-fluid btn-transparent"]')[0].text \
                        == 'Доступен только в офлайн-магазине'
                except Exception:
                    is_only_offline = False

                if is_only_offline:
                    location = page_content.xpath('//div[@class="access"]')[0].text
                    if 'петров' in location.lower():
                        ya_taxi_link = 'https://3.redirect.appmetrica.yandex.com/route?end-lat=55.767851&end' \
                                       '-lon=37.618764&appmetrica_tracking_id=1178268795219780156&app_code=3'
                        ya_go_link = 'https://3.redirect.appmetrica.yandex.com/route?end-lat=55.767851&end' \
                                     '-lon=37.618764&appmetrica_tracking_id=1178268795219780156&app_code=2187871'
                    elif 'полян' in location.lower():
                        ya_taxi_link = 'https://3.redirect.appmetrica.yandex.com/route?end-lat=55.730548&end' \
                                       '-lon=37.623233&appmetrica_tracking_id=1178268795219780156&app_code=3'
                        ya_go_link = 'https://3.redirect.appmetrica.yandex.com/route?end-lat=55.730548&end' \
                                     '-lon=37.623233&appmetrica_tracking_id=1178268795219780156&app_code=2187871'
                    else:
                        ya_taxi_link = 'https://3.redirect.appmetrica.yandex.com/route?end-lat=55.730548&end' \
                                       '-lon=37.623233&appmetrica_tracking_id=1178268795219780156&app_code=3'
                        ya_go_link = 'https://3.redirect.appmetrica.yandex.com/route?end-lat=55.730548&end' \
                                     '-lon=37.623233&appmetrica_tracking_id=1178268795219780156&app_code=2187871'

                    result.append(
                        IRelease(
                            content.name + f'?shash={sizes.hash().hex()}&tp=offline',
                            'brandshop-offline',
                            name,
                            page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                            '',
                            api.Price(
                                api.CURRENCIES['RUB'],
                                float(page_content.xpath('//meta[@itemprop="price"]')[0].get('content'))
                            ),
                            sizes,
                            [
                                FooterItem('Cart', 'https://brandshop.ru/cart'),
                                FooterItem('Login', 'https://brandshop.ru/login')
                            ],
                            {
                                'Site': '[Brandshop](https://brandshop.ru)',
                                'Location': location,
                                'Taxi 🚕': f"[Yandex Taxi]({ya_taxi_link}) | [Yango]({ya_go_link})"
                            }
                        )
                    )

                else:

                    result.append(
                        IRelease(
                            content.name + f'?shash={sizes.hash().hex()}',
                            'brandshop',
                            name,
                            page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                            '',
                            api.Price(
                                api.CURRENCIES['RUB'],
                                float(page_content.xpath('//meta[@itemprop="price"]')[0].get('content'))
                            ),
                            sizes,
                            [
                                FooterItem('Cart', 'https://brandshop.ru/cart'),
                                FooterItem('Login', 'https://brandshop.ru/login')
                            ],
                            additional_columns
                        )
                    )

            except etree.XMLSyntaxError:
                raise etree.XMLSyntaxError('XMLDecodeError')

        result.append(content)
        return result
