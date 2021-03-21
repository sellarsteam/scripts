import re
from datetime import datetime, timedelta, timezone
from time import time
from typing import List, Union

from lxml import etree

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, \
    TargetEndType, IRelease, FooterItem, IAnnounce
from source.library import SubProvider, Keywords
from source.tools import ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.link: str = 'https://www.revolveclothing.ru/r/BrandsContent.jsp?&aliasURL=new%2Fshoes%2Fbr%2F9127db&s=c&c=Shoes&n=n&designer=adidas%20Originals&designer=Jordan&designer=Nike&filters=designer'

        self.interval: int = 1
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        }

    @property
    def catalog(self) -> CatalogType:
        return api.CInterval(self.name, 10)

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
            result.append(content)

            ok, response = self.provider.request(self.link, headers=self.headers, proxy=True)

            if not ok:
                return [content, api.MAlert('Connection is lost, Script go to sleep!', self.name)]

            catalog = etree.HTML(response.text).xpath(
                '//div[@class="plp_image_wrap u-center"]/a')

            if len(catalog) == 0:
                return [content, api.MAlert('Catalog is empty', self.name)]

            for element in catalog:
                name = element.xpath('div[@class="product-name u-margin-t--lg js-plp-name"]')[0].text

                href = element.get('href')
                link_to_request = f'https://www.revolveclothing.ru/r/dialog/QuickView.jsp?fmt=plp&code={href.split("/")[3]}&callBackAfterAddToBag='
                price = float(re.sub("[^0-9]", "", element.xpath('div/div[@class="price js-plp-prices-div"]/span')[0].text))

                if self.kw.check(name + ' ' + href.split('?')[0]):
                    result.append(result.append(api.TScheduled(href.split("/")[3], self.name, [link_to_request, href, name, price], time())))
        if mode == 1:

            try:
                ok, page_response = self.provider.request(
                    content.data[0],
                    headers=self.headers, proxy=True)

                if not ok:
                    return [api.MAlert('Connection is lost', self.name)]

                page_content = etree.HTML(page_response.text)
                try:
                    sizes = [api.Size(f"{size.get('value')} [{size.get('data-qty')}]")
                             for size in page_content.xpath('//input[@class="size-options__radio '
                                                            'size-clickable"]')
                             if int(size.get('data-qty')) > 0]
                except AttributeError:
                    sizes = []
                try:
                    image = page_content.xpath('//div[@class="js-carousel__track"]/div/img')[0].get('src')
                except AttributeError:
                    image = 'https://im0-tub-ru.yandex.net/i?id=03847b9f73ea6873edecf9d7a292d766&n=13'

                if sizes:
                    sizes = api.Sizes(api.SIZE_TYPES[''], sizes)
                    result.append(
                        IRelease(
                            'https://www.revolveclothing.ru/sellars' + content.data[1].split('?')[0] +
                            f'?shash={sizes.hash().hex()}',
                            'revolveclothing',
                            content.data[2],
                            image,
                            'DELIVERY FROM $100 IS FREE',
                            api.Price(
                                api.CURRENCIES['USD'],
                                content.data[3] / 100
                            ),
                            sizes,
                            [
                                FooterItem('Cart', 'https://www.revolveclothing.ru/r/ShoppingBag.jsp'),
                                FooterItem('Login', 'https://www.revolveclothing.ru/r/SignIn.jsp')
                            ],
                            {'Site': '[Revolve Clothing](https://www.revolveclothing.ru)'}
                        )
                    )
                else:
                    sizes = api.Sizes(api.SIZE_TYPES[''], [])
                    result.append(
                        IAnnounce(
                            'https://www.revolveclothing.ru/sellars' + content.data[1].split('?')[0] +
                            f'?shash={sizes.hash().hex()}',
                            'revolveclothing',
                            content.data[2],
                            image,
                            'DELIVERY FROM $100 IS FREE',
                            api.Price(
                                api.CURRENCIES['USD'],
                                content.data[3] / 100
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

        return result
