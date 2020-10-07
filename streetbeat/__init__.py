from datetime import datetime, timedelta, timezone
from json import loads, JSONDecodeError
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
        self.link: str = 'https://street-beat.ru/cat/man/krossovki/nike;jordan;adidas-originals/?sort=create&order=desc'
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=1, microsecond=250000, tzinfo=timezone.utc).timestamp()

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

            for element in etree.HTML(response.text).xpath('//div[@class="col-xl-3 col-md-4 col-xs-6 view-type_"]'):
                if check_name(element[0].xpath('a[@class="link link--no-color catalog-item__title '
                                               'ddl_product_link"]/span')[0].text.lower()):

                    link = element[0] \
                        .xpath('a[@class="link link--no-color catalog-item__title ddl_product_link"]')[0].get('href')
                    try:
                        if HashStorage.check_target(
                                api.Target('https://street-beat.ru' + link, self.name, 0).hash()):
                            try:

                                ok, page_content = self.provider.request('https://street-beat.ru' + link,
                                                                         headers={'user-agent': self.user_agent})

                                if not ok:
                                    if isinstance(response, exceptions.Timeout):
                                        return [api.CInterval(self.name, 600.)]
                                    else:
                                        raise response

                                page_content: etree.Element = etree.HTML(page_content.text)
                                json_content = loads(page_content
                                                     .xpath('//script[@type="application/ld+json"]')[1].text)
                            except etree.XMLSyntaxError:
                                raise etree.XMLSyntaxError('Exception XMLDecodeError')
                            except JSONDecodeError as e:
                                raise e
                            available_sizes = []
                            for size in page_content.xpath('//ul[@class="sizes__table current"]//li'):
                                if size.get('class') == 'last':
                                    available_sizes.append(api.Size(f'{str(size.xpath("label")[0].text)} RU [LAST]',
                                                                    'http://static.sellars.cf/links?site=streetbeat&id='
                                                                    + size.xpath("input")[0].get('data-sku-id')))
                                elif size.get('class') == 'missing':
                                    continue
                                else:
                                    available_sizes.append(api.Size(f'{str(size.xpath("label")[0].text)} RU',
                                                                    'http://static.sellars.cf/links?site=streetbeat&id='
                                                                    + size.xpath("input")[0].get('data-sku-id')))

                            name = page_content \
                                .xpath('//h1[@class="product-heading"]/span')[0].text.split('кроссовки ')[-1]
                            HashStorage.add_target(api.Target('https://street-beat.ru' + link
                                                              , self.name, 0).hash())
                            result.append(
                                IRelease(
                                    'https://street-beat.ru' + link,
                                    'streetbeat',
                                    name,
                                    json_content['image'],
                                    '',
                                    api.Price(
                                        api.CURRENCIES['RUB'],
                                        float(json_content['offers']['price'])
                                    ),
                                    api.Sizes(api.SIZE_TYPES[''], available_sizes),
                                    [
                                        FooterItem(
                                            'StockX',
                                            'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20').
                                            replace('"', '').replace('\n', '').replace(' ', '')
                                        ),
                                        FooterItem('Urban QT',
                                                   f'https://autofill.cc/api/v1/qt?storeId=streetbeat&monitor={"https://street-beat.ru" + link}'),
                                        FooterItem('Cart', 'https://street-beat.ru/cart'),
                                        FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                                    ],
                                    {'Site': 'Street-Beat'}
                                )
                            )
                    except etree.XMLSyntaxError:
                        raise etree.XMLSyntaxError('XMLDecodeError')
            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
