from json import JSONDecodeError
from re import findall
from typing import List

from lxml import etree

from source import api
from source.api import IndexType, TargetType, StatusType
from source.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider):
        super().__init__(name, log, provider)
        self.catalog: str = 'https://www.footpatrol.com/campaign/New+In/?facet:new=latest&sort=latest'
        self.interval: int = 1
        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu ' \
                          'Chromium/79.0.3945.130 Chrome/79.0.3945.130 Safari/537.36 '

    def index(self) -> IndexType:
        return api.IInterval(self.name, 5)

    def targets(self) -> List[TargetType]:
        links = list()
        counter = 0
        for element in etree.HTML(self.provider.get(self.catalog, headers={'user-agent': self.user_agent}, mode=1,
                                                    proxy=True)).xpath('//a[@data-e2e="product-listing-name"]'):
            if counter == 5:
                break
            if 'air' in element.get('href') or 'yeezy' in element.get('href') or 'jordan' in element.get(
                    'href') or 'dunk' in element.get('href'):
                links.append(element.get('href'))
            counter += 1
        return [
            api.TInterval(element.split('/')[-1],
                          self.name, 'https://www.footpatrol.com' + element, self.interval)
            for element in links
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                get_content = self.provider.get(target.data, headers={
                    'user-agent': self.user_agent}, mode=1, proxy=True)
                content: etree.Element = etree.HTML(get_content)
                if content.xpath('//meta[@name="twitter:data2"]')[0].get('content') == 'IN STOCK':
                    available = True
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')
        name = content.xpath('//meta[@name="title"]')[0].get('content').split(' |')[0]
        if available:
            return api.SSuccess(
                self.name,
                api.Result(
                    name,
                    target.data,
                    'footsites',
                    content.xpath('//meta[@property="og:image"]')[0].get('content'),
                    '',
                    (
                        api.currencies['GBP'],
                        float(content.xpath('//meta[@name="twitter:data1"]')[0].get('content'))
                    ),
                    {'Site': 'Footpatrol-UK'},
                    tuple(str(size.replace('name:', '').replace('"', '')) + ' UK'
                          for size in findall(r'name:".*"', get_content)),
                    (
                        ('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                        ('Cart', 'https://www.footpatrol.com/cart'),
                        ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    )
                )
            )
        else:
            return api.SSuccess(
                self.name,
                api.Result(
                    'Sold Out',
                    target.data,
                    'tech',
                    '',
                    '',
                    (
                        api.currencies['GBP'],
                        float(1)
                    ),
                    {},
                    tuple(),
                    (
                        ('StockX', 'https://stockx.com/search/sneakers?s='),
                        ('Cart', 'https://www.footpatrol.com/cart'),
                        ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    )
                )
            )
