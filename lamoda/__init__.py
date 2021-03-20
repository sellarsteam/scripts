from typing import List, Union

from lxml import etree
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    @property
    def catalog(self) -> api.CatalogType:
        return api.CInterval(self.name, 1200000)

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            result.append(api.TInterval('lamoda_1', self.name, [
                'https://www.lamoda.ru/c/5972/shoes-muzhkedy/?ajax=1&brands=29193&sort=default'], 5))
            result.append(api.TInterval('lamoda_2', self.name, [
                'https://www.lamoda.ru/c/5972/shoes-muzhkedy/?ajax=1&brands=2047&sort=new'], 5))
            result.append(api.TInterval('lamoda_3', self.name, [
                'https://www.lamoda.ru/c/5855/shoes-zhenkedy/?ajax=1&brands=29193'], 5))
            result.append(api.TInterval('lamoda_4', self.name, [
                'https://www.lamoda.ru/c/5855/shoes-zhenkedy/?ajax=1&brands=2047'], 5))
            result.append(api.TInterval('lamoda_5', self.name, [
                'https://www.lamoda.ru/catalogsearch/result/?ajax=1&q=dunk&from=button&submit=y&sort=price_asc'], 5))
            result.append(api.TInterval('lamoda_6', self.name, [
                'https://www.lamoda.ru/catalogsearch/result/?q=jordan%201%20%D0%BE%D0%B1%D1%83%D0%B2%D1%8C&from=button&submit=y&ajax=1'], 5))

        if mode == 1:
            try:
                ok, response = self.provider.request(content.data[0], headers={'user-agent': generate_user_agent()},
                                                     proxy=True)

                if not ok:
                    return [api.MAlert('Timeout: ' + content.name, self.name), content]

                html_response = etree.HTML(response.text)

                for element in html_response.xpath('//div[@class="products-list-item" or @class="products-list-item m_loading"]'):
                    link = 'https://www.lamoda.ru' + element.xpath('a[@class="products-list-item__link link"]') \
                    [0].get('href')

                    name = element.xpath('a[@class="products-list-item__link link"]'
                                        '/div[@class="products-list-item__brand"]/span')[0].text

                    if self.kw.check(name.lower() + ' ' + link):
                        target = api.Target(link, self.name, 0)

                        if HashStorage.check_target(target.hash()):
                            HashStorage.add_target(target.hash())
                            additional_columns = {'Site': '[Lamoda](https://www.lamoda.ru)'}
                        else:
                            additional_columns = {'Site': '[Lamoda](https://www.lamoda.ru)', 'Type': 'Restock'}
                        try:
                            price = api.Price(api.CURRENCIES['RUB'],
                                          float(element.xpath('a[@class="products-list-item__link link"]/div')[0]
                                                .get('data-price')))
                        except TypeError:
                            price = api.Price(api.CURRENCIES['RUB'], .0)
                        image = 'https:' + element.get('data-src')

                        sizes = api.Sizes(api.SIZE_TYPES[''], [api.Size(size.text, f'https://www.lamoda.ru{size.get("data-link")}')
                                                               for size in
                                                               element.xpath(
                                                                   f'div[@class="products-list-item__extra"]/div/div[@class="products-list-item__sizes"]/a')])
                        if True:
                            result.append(
                                IRelease(
                                    link + f'?shas="{sizes.hash().hex()}"',
                                    'lamoda',
                                    name,
                                    image,
                                    '',
                                    price,
                                    sizes,
                                    [
                                        FooterItem('Cart', 'https://www.lamoda.ru/checkout/cart/'),
                                        FooterItem('Login', 'https://www.lamoda.ru/login/')
                                    ],
                                    additional_columns
                                )
                            )
            except Exception:
                result.append(api.MAlert('Script is crashed!', self.name))
                pass

        result.append(content)
        return result
