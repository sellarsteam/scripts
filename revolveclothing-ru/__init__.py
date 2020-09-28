from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from requests import exceptions
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
        self.link: str = 'https://www.revolveclothing.ru/shoes-sneakers/br/2aec17/?navsrc=subshoes&filters=designer' \
                         '&sortBy=newest&designer=adidas%20Originals&designer=Jordan&designer=Nike'
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
                if isinstance(response, exceptions.Timeout):
                    return [api.CInterval(self.name, 600.)]
                else:
                    raise response

            for element in etree.HTML(response.text) \
                    .xpath('//a[@class="u-text-decoration--none js-plp-pdp-link2 product-link"]'):

                link = element.get('href')
                name = link.split('/')[1]

                if check_name(name.lower(), self.absolute_keywords,
                              self.positive_keywords, self.negative_keywords):

                    try:
                        if HashStorage.check_target(api.Target('https://www.revolveclothing.ru' +
                                                               link, self.name, 0).hash()):

                            ok, page_response = self.provider.request(
                                'https://www.revolveclothing.ru' + element.get('href'),
                                headers={'user-agent': self.user_agent})

                            if not ok:
                                if isinstance(response, exceptions.Timeout):
                                    return [api.CInterval(self.name, 600.)]
                                else:
                                    raise response

                            page_content = etree.HTML(page_response.text)

                            sizes = [api.Size(f"{size.get('value')} [{size.get('data-qty')}]")
                                     for size in page_content.xpath('//ul[@class="size-options"]/li/input')
                                     if int(size.get('data-qty')) > 0]
                            name = page_content.xpath('//meta[@name="twitter:title"]')[0].get('content')

                            HashStorage.add_target(api.Target('https://www.revolveclothing.ru'
                                                              + link, self.name, 0).hash())

                            if sizes:
                                result.append(
                                    IRelease(
                                        'https://www.revolveclothing.ru' + link,
                                        'revolveclothing-ru',
                                        name,
                                        page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                                        'БЕСПЛАТНАЯ ДОСТАВКА ЗАКАЗОВ ОТ 100$',
                                        api.Price(
                                            api.CURRENCIES['USD'],
                                            float(page_content.xpath('//meta[@property="wanelo:product:price"]')[0].get(
                                                'content'))
                                        ),
                                        api.Sizes(api.SIZE_TYPES[''], sizes),
                                        [
                                            FooterItem('Cart', 'https://www.revolveclothing.ru/r/ShoppingBag.jsp'),
                                            FooterItem('Login', 'https://www.revolveclothing.ru/r/SignIn.jsp')
                                        ],
                                        {'Site': '[Revolve Clothing](https://www.revolveclothing.ru) 🇷🇺'}
                                    )
                                )

                    except etree.XMLSyntaxError:
                        raise etree.XMLSyntaxError('XMLDecodeEroor')
            if result or content.expired:
                content.gen.time = self.time_gen()
                content.expired = False

            result.append(content)
        return result
