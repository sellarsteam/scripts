from typing import List, Union

from lxml import etree
from pycurl_requests import exceptions
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
        return api.CInterval(self.name, 120)

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:
            result.append(api.TInterval('lamoda_1', self.name, ['https://www.lamoda.ru/c/5972/shoes-muzhkedy/?ajax=1&brands=29193&sort=default'], 3))
            result.append(api.TInterval('lamoda_2', self.name, [
                'https://www.lamoda.ru/c/5972/shoes-muzhkedy/?ajax=1&brands=2047&sort=new'], 3))
            result.append(api.TInterval('lamoda_3', self.name, [
                'https://www.lamoda.ru/c/5855/shoes-zhenkedy/?ajax=1&brands=29193'], 3))
            result.append(api.TInterval('lamoda_4', self.name, [
                'https://www.lamoda.ru/c/5855/shoes-zhenkedy/?ajax=1&brands=2047'], 3))
        if mode == 1:
            ok, response = self.provider.request(content.data[0], headers={'user-agent': generate_user_agent()})

            if not ok:
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.), api.MAlert('Script go to sleep', self.name)]
                else:
                    raise response

            html_response = etree.HTML(response.text)

            counter = 0

            names = [name.text.replace('\n', '') for name in
                     html_response.xpath('//span[@class="products-list-item__type"]')]
            prices = [api.Price(api.CURRENCIES['RUB'], float(price.text.replace(' ', ''))) for price in
                      html_response.xpath('//span[@class="price__action js-cd-discount" or @class="price__actual"]')]
            images = ['https:' + image.get('data-image') for image in html_response.xpath('//div[@data-image]')]
            data_links_for_sizes = []
            for data_link in html_response.xpath('//a[@class="products-list-item__size-item link"]'):
                data_link = data_link.get('data-link')
                if data_link in data_links_for_sizes:
                    pass
                else:
                    data_links_for_sizes.append(data_link)
            links = ['https://www.lamoda.ru' + link.get('href')
                     for link in html_response.xpath('//a[@class="products-list-item__link link"]')]
            for element in range(len(names)):

                link = links[counter]
                name = names[counter]

                if self.kw.check(name.lower()):
                    target = api.Target(link, self.name, 0)

                    if HashStorage.check_target(target.hash()):
                        HashStorage.add_target(target.hash())
                        additional_columns = {'Site': '[Lamoda](https://www.lamoda.ru)'}
                    else:
                        additional_columns = {'Site': '[Lamoda](https://www.lamoda.ru)', 'Type': 'Restock'}

                    price = prices[counter]
                    image = images[counter]

                    sizes = api.Sizes(api.SIZE_TYPES[''], [api.Size(size.text)
                                                           for size in
                                                           html_response.xpath(
                                                               f'//a[@data-link="{data_links_for_sizes[counter]}"]')])
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
                counter += 1

        result.append(content)
        return result
