from json import JSONDecodeError
from re import findall
from typing import List

from cfscrape import create_scraper
from lxml import etree

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger
from scripts.proxy import get_proxy


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.footpatrol.com/campaign/New+In/?facet:new=latest&sort=latest'
        self.interval: int = 1
        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu ' \
                          'Chromium/79.0.3945.130 Chrome/79.0.3945.130 Safari/537.36 '
        self.scraper = create_scraper()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 5)

    def targets(self) -> List[TargetType]:
        links = list()
        counter = 0
        for element in etree.HTML(create_scraper().get(self.catalog, headers={'user-agent': self.user_agent}).text)\
                .xpath('//a[@data-e2e="product-listing-name"]'):
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
                get_content = self.scraper.get(target.data, headers={
                    'user-agent': self.user_agent}, proxies=get_proxy()).text
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
