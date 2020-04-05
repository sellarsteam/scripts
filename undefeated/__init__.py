from json import loads, JSONDecodeError
from re import findall
from typing import List

from jsonpath2 import Path
from lxml import etree
from requests import get
from user_agent import generate_user_agent
from random import choice

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger

proxies = ['http 46.48.170.175:8080',
           'http 62.33.207.196:3128',
           'http 95.156.125.190:41870',
           'http 81.5.103.14:8081',
           'http 195.182.152.238:38178',
           'http 217.174.184.234:8081',
           'http 62.33.207.201:80',
           'http 193.106.94.106:8080',
           'http 62.33.207.201:3128',
           'http 109.195.194.79:57657',
           'http 62.33.207.196:80']

class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://undefeated.com/collections/mens-footwear'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 10)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element[0].xpath('a')[0].get('href').split('/')[4],
                          self.name, 'https://undefeated.com' + element[0].xpath('a')[0].get('href'), self.interval)
            for element in etree.HTML(get(self.catalog,
                                          headers={'user-agent': generate_user_agent()}
                                          ).text).xpath('//div[@class="grid-product__wrapper"]')
            if 'air' in element[0].xpath('a')[0].get('href') or 'yeezy' in element[0].xpath('a')[0].get('href')
               or 'aj' in element[0].xpath('a')[0].get('href') or 'dunk' in element[0].xpath('a')[0].get('href')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                proxy = choice(proxies)
                get_content = get(target.data, headers={'user-agent': generate_user_agent()},
                        proxies={str(proxy.split(' ')[0]): str(proxy.split(' ')[1])}).text
                content: etree.Element = etree.HTML(get_content)

                if content.xpath('//span[@class="btn__text"]')[0].text.replace(' ', '').replace('\n', '') != 'SoldOut':
                    available = True
                else:
                    return api.SWaiting(target)
                sizes_data = Path.parse_str('$.product.variants.*').match(
                    loads(findall(r'var meta = {.*}', get_content)[0]
                          .replace('var meta = ', '')))
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')
        except IndexError:
            return api.SWaiting(target)
        if available:
            try:
                name = content.xpath('//meta[@property="og:title"]')[0].get('content')
                return api.SSuccess(
                    self.name,
                    api.Result(
                        name,
                        target.data,
                        'undefeated',
                        content.xpath('//meta[@property="og:image:secure_url"]')[0].get('content').split('?')[0],
                        '',
                        (
                            api.currencies['USD'],
                            float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content')
                                  .replace('.', '').replace(',', '.'))
                        ),
                        {},
                        tuple(
                            (
                                str(size_data.current_value['public_title'].split(' ')[-1]) + ' US',
                                'https://undefeated.com/cart/' + str(size_data.current_value['id']) + ':1'
                            ) for size_data in sizes_data
                        ),
                        (
                            ('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                            ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                        )
                    )
                )
            except JSONDecodeError:
                return api.SFail(self.name, 'Exception JSONDecodeError')
        else:
            return api.SWaiting(target)

if __name__ == '__main__':
    proxy = choice(proxies)
    get_content = get('https://undefeated.com/collections/mens-footwear/products/blazer-mid-77-vintage-white-lightbone-sail?variant=31324508749897'
                      , headers={'user-agent': generate_user_agent()},
                      proxies={str(proxy.split(' ')[0]): str(proxy.split(' ')[1])}).text
    content: etree.Element = etree.HTML(get_content)
    sizes_data = Path.parse_str('$.product.variants.*').match(
        loads(findall(r'var meta = {.*}', get_content)[0]
              .replace('var meta = ', '')))
    s = tuple(
                            (
                                str(size_data.current_value['public_title'].split(' ')[-1]) + ' US',
                                'https://undefeated.com/cart/' + str(size_data.current_value['id']) + ':1'
                            ) for size_data in sizes_data
                        )
    print(s)