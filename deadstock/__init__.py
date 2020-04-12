
from typing import List

from json import loads, JSONDecodeError
from lxml import etree
from re import findall
from user_agent import generate_user_agent
from requests import get
from scripts.proxy import get_proxy
from jsonpath2 import Path, match

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.deadstock.ca/collections/new-arrivals?sort_by=created-descending'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 5)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[4],
                          self.name, 'https://www.deadstock.ca' + element.get('href'), self.interval)
            for element in etree.HTML(get(
                url=self.catalog, headers={'user-agent': self.user_agent}, proxies=get_proxy()
            ).text).xpath('//a[@class=" grid-product__meta"]')
            if 'nike' in element.get('href') or 'yeezy' in element.get('href') or 'jordan' in element.get('href')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                get_content = get(url=target.data, headers={'headers': generate_user_agent()}, proxies=get_proxy()).text
                content: etree.Element = etree.HTML(get_content)
                available_sizes = tuple(size.get('for').split('-')[-1]
                                        for size in content.xpath('//fieldset[@id="ProductSelect-option-0"]')[0].xpath('label[@class=""]'))
                if len(available_sizes) > 0:
                    available = True
                sizes_data = Path.parse_str('$.product.variants.*').match(
                loads(findall(r'var meta = {.*}', get_content)[0]
                      .replace('var meta = ', '')))
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        if available:
            name = content.xpath('//meta[@property="og:title"]')[0].get('content')
            return api.SSuccess(
                self.name,
                api.Result(
                    name,
                    target.data,
                    'shopify-filtered',
                    content.xpath('//meta[@property="og:image"]')[2].get('content'),
                    '',
                    (api.currencies['USD'], float(content.xpath('//meta[@property="og:price:amount"]')[0].get('content'))),
                    {},
                    tuple(
                        (
                            str(size_data.current_value['public_title']) + ' US',
                            'https://www.deadstock.ca/cart/' + str(size_data.current_value['id']) + ':1'
                        ) for size_data in sizes_data if size_data.current_value['public_title'] in available_sizes
                    ),
                    (('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                     ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
                )
            )
        else:
            return api.SWaiting(target)