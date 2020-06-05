from typing import List

from lxml import etree
from user_agent import generate_user_agent

from source import api
from source.api import IndexType, TargetType, StatusType
from source.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider, storage):
        super().__init__(name, log, provider, storage)
        self.catalog: str = 'https://www.hibbett.com/launch-calendar/?prefn1=dtLaunch&prefv1=30'
        self.interval: int = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 1200)

    def targets(self) -> List[TargetType]:
        links = list()
        counter = 0
        for element in etree.HTML(self.provider.get(url=self.catalog, proxy=True, mode=1)) \
                .xpath('//a[@class="name-link"]'):
            if counter == 5:
                break
            if 'dunk' in element.get('href') or 'yeezy' in element.get('href') or 'jordan' in element.get('href') \
                    or 'sacai' in element.get('href') or 'air' in element.get('href'):
                links.append(element.get('href'))
                    counter += 1
        return [
            api.TInterval(element.split('/')[-1],
                          self.name, element, self.interval)
            for element in links
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                content: etree.Element = etree.HTML(self.provider.get(url=target.data, proxy=True, mode=1))
                available_sizes = list()
                for element in content.xpath('//ul[@class="swatches size "]/li[@class="selectable"]/a'):
                    size = element.get('href').split('size=')[-1].split('&')[0].replace('0', '')
                    if len(size) == 2:
                        if size == '15':
                            size = '10.5 US'
                        else:
                            if size[-1] == '5':
                                size = f'{float(size) / 10} US'
                            else:
                                size = f'{size} US'
                    else:
                        if size == '1':
                            size = '10 US'
                        elif size[-1] == '5':
                            size = f'{float(size) / 10} US'
                        else:
                            size = f'{size} US'
                    available_sizes.append((size, element.get('href')))
                if len(available_sizes) == 0:
                    return api.SWaiting(target)
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        name = content.xpath('//title')[0].text
        data_for_image = target.data.split('/')[0]
        return api.SSuccess(
            self.name,
            api.Result(
                name,
                target.data,
                'hibbett',
                f'https://i1.adis.ws/i/hibbett/{data_for_image.split(".html")[0]}'
                f'_{data_for_image.split("color=")[-1].split("&")[0]}_'
                f'right1?w=580&h=580&fmt=jpg&bg=rgb(255,255,255)&img404=404&v=0',
                '',
                (api.currencies['USD'], float(content.xpath('//span[@class="price-sales"]')[0].get('content'))),
                {'Site': 'Hibbett'},
                tuple(available_sizes),
                (('StockX', 'https://stockx.com/search/sneakers?s=' + content.xpath('//meta[@name="keywords"]')[0]
                  .get('content').replace(' ', '%20')),
                 ('Cart', 'https://www.hibbett.com/cart'),
                 ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
            )
        )
