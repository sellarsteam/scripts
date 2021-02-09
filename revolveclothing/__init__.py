from datetime import datetime, timedelta, timezone
from typing import List, Union

import pycurl
from lxml import etree
from pycurl_requests import exceptions
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType,\
    TargetEndType, IRelease, FooterItem
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.link: str = 'https://www.revolveclothing.ru/r/BrandsContent.jsp?&aliasURL=shoes-sneakers%2Fbr%2F2aec17&sc=Sneakers&s=c&c=Shoes&navsrc=subshoes&designer=Jordan&designer=Nike&filters=designer'

        self.interval: int = 1
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=0, microsecond=750000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:

            ok, response = self.provider.request(self.link, headers={'user-agent': self.user_agent})

            if not ok:
                if isinstance(response, pycurl.error):
                    return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]
                else:
                    raise response

            catalog = etree.HTML(response.text).xpath(
                '//div[@class="plp_image_wrap u-center"]/a')

            if len(catalog) == 0:
                raise Exception('Catalog is empty')

            for element in catalog:

                href = element.get('href')
                link_to_request = f'https://www.revolveclothing.ru/r/dialog/QuickView.jsp?fmt=plp&code={href.split("/")[3]}'

                if self.kw.check(href.lower(), div='-'):
                    result.append(result.append(api.TInterval(href.split("/")[3], self.name, [link_to_request, href], 1)))
        if mode == 1:

            try:
                ok, page_response = self.provider.request(
                    content.data[0],
                    headers={'user-agent': self.user_agent})

                if not ok:
                    if isinstance(page_response, exceptions.Timeout):
                        return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]
                    else:
                        raise page_response

                page_content = etree.HTML(page_response.text)

                sizes = [api.Size(f"{size.get('value')} [{size.get('data-qty')}]")
                         for size in page_content.xpath('//input[@class="size-options__radio '
                                                        'size-clickable"]')
                         if int(size.get('data-qty')) > 0]

                if sizes:
                    sizes = api.Sizes(api.SIZE_TYPES[''], sizes)
                    result.append(
                        IRelease(
                            'https://www.revolveclothing.ru/sellars' + content.data[1].split('?')[0] +
                            f'?shash={sizes.hash().hex()}',
                            'revolveclothing',
                            page_content.xpath('//h2[@property="name"]')[0].text,
                            page_content.xpath('//div[@class="js-carousel__track"]/div/img')[0].get('src'),
                            'DELIVERY FROM $100 IS FREE',
                            api.Price(
                                api.CURRENCIES['RUB'],
                                float(page_content.xpath('/html/body/div/div[2]/div[2]/div[1]/div['
                                                         '2]/div/span')[0]
                                      .text[:-1].replace('₽', '').replace(',', ''))
                            ),
                            sizes,
                            [
                                FooterItem('Cart', 'https://www.revolveclothing.ru/r/ShoppingBag.jsp'),
                                FooterItem('Login', 'https://www.revolveclothing.ru/r/SignIn.jsp')
                            ],
                            {'Site': '[Revolve Clothing](https://www.revolveclothing.ru)'}
                        )
                    )

            except etree.XMLSyntaxError:
                raise etree.XMLSyntaxError('XMLDecodeEroor')

            if isinstance(content, api.CSmart):
                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False
                result.append(content)
            else:
                result.extend([self.catalog, api.MAlert('Script is awake', self.name)])

        return result
