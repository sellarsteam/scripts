from typing import List

from lxml import etree
from user_agent import generate_user_agent

from source import api
from source.api import IndexType, TargetType, StatusType
from source.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider):
        super().__init__(name, log, provider)
        self.catalog: str = 'https://www.net-a-porter.com/ru/en/d/Shop/Shoes/Sneakers?cm_sp=topnav-_-shoes-_-sneakers' \
                            '&pn=1&npp=60&image_view=product&dscroll=0&sortorder=new-in&sizescheme=IT '
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.xpath('div[@class="description"]/a[@data-position]')[0].get('title'),
                          self.name,
                          (element.xpath('div[@class="description"]/a[@data-position]')[0].get('href'),
                           element.xpath('div[@class="description"]/a[@data-position]')[0].get('title'),
                           element.xpath('div[@class="description"]/a[@data-position]')[0].get('href'),
                           element.xpath('div[@class="product-image"]/a[@data-position]/img[@height="270"]')[0]
                           .get('data-src'),
                           element.xpath('div[@class="description"]/span[@class="price "]')[0].text
                           .replace('\t', '').replace('\n', '').replace('£', '')
                           ),
                          self.interval)
            for element in etree.HTML(self.provider.get(
                self.catalog,
                headers={
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'accept-language': 'en-US,en;q=0.8',
                    'upgrade-insecure-requests': '1',
                    'user-agent': self.user_agent,
                    'referer': 'https://www.net-a-porter.com/ru/en/d/Shop/Shoes/All?pn=1&npp=60&image_view=product'
                               '&dscroll=0 '
                }, mode=1
            )).xpath('//li') if len(element.xpath('div[@class="description"]/a[@data-position]')) > 0
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: etree.Element = etree.HTML(
                    self.provider.get(
                        'https://www.net-a-porter.com' + target.data[0],
                        headers={
                            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                            'accept-language': 'en-US,en;q=0.8',
                            'upgrade-insecure-requests': '1',
                            'user-agent': self.user_agent,
                            'referer': self.catalog
                        }
                    ))
                if len(content.xpath('//div[@class="sold-out-details"]')) == 0:
                    available = True
                else:
                    return api.SFail(self.name, 'Product is sold out')
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        if available:
            return api.SSuccess(
                self.name,
                api.Result(
                    target.data[1],
                    'https://www.net-a-porter.com' + target.data[2],
                    'porter',
                    'https:' + target.data[3],
                    '',
                    (api.currencies['GBP'], float(target.data[4])),
                    {},
                    (),
                    (
                        ('StockX', 'https://stockx.com/search/sneakers?s=' + target.data[1].replace(' ', '%20')),
                        ('Cart', 'https://www.net-a-porter.com/cart'),
                        ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                    )
                )
            )
        else:
            return api.SWaiting(target)
