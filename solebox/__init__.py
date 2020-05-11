from typing import List

from cfscrape import create_scraper
from lxml import etree

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.solebox.com/de_DE/c/new'
        self.interval: int = 1
        self.scraper = create_scraper()
        self.user_agent = 'Pinterest/0.2 (+https://www.pinterest.com/bot .html)Mozilla/5.0 (compatible; ' \
                          'Pinterestbot/1.0; +https://www.pinterest.com/bot.html)Mozilla/5.0 (Linux; Android 6.0.1; ' \
                          'Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.96 Mobile ' \
                          'Safari/537.36 (compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html) '

    def index(self) -> IndexType:
        return api.IInterval(self.name, 1)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(element.get('href').split('/')[3],
                          self.name, 'https://www.solebox.com' + element.get('href'), self.interval)
            for element in etree.HTML(self.scraper.get(
                url=self.catalog, headers={'user-agent': self.user_agent}
            ).text).xpath('//a[@class="b-product-tile-image-link js-product-tile-link"]')
            if 'nike' in element.get('href') or 'yeezy' in element.get('href') or 'jordan' in element.get('href')
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                content: etree.Element = etree.HTML(
                    self.scraper.get(url=target.data, headers={'user-agent': self.user_agent}).text)
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        try:
            if content.xpath('//button[@class="f-pdp-button f-pdp-button-coming-soon f-pdp-button--lowercase"]')[0].get(
                    'aria-label') == 'Coming Soon':
                return api.SWaiting(target)
        except IndexError:
            pass
        available_sizes = tuple(str(size.get('data-value')) + ' EU'
                                for size in content.xpath('//a[@class="js-pdp-attribute-btn b-pdp-swatch-link '
                                                          'js-pdp-attribute-btn--size"]'))
        name = target.data.split('/')[5].split('%')[0].replace('_', ' ').upper()
        if len(available_sizes) > 0:
            return api.SSuccess(
                self.name,
                api.Result(
                    name,
                    target.data.replace('de_DE', 'en_RU'),
                    'solebox',
                    content.xpath('//meta[@property="og:image"]')[0].get('content'),
                    '',
                    (api.currencies['EUR'], float(content.xpath('//span[@class="b-product-tile-price-item"]')[0].text
                                                  .replace('€', '').replace('\n', '').replace(' ', '').split(',')[0])),
                    {},
                    available_sizes,
                    (('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                     ('Cart', 'https://www.solebox.com/cart'),
                     ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
                )
            )
        else:  # TODO Fix when item is soldout
            return api.SSuccess(
                self.name,
                api.Result(
                    f'Sold Out {name}',
                    target.data,
                    'tech',
                    '',
                    '',
                    (api.currencies['EUR'], 1.0),
                    {},
                    tuple(),
                    (('StockX', 'https://stockx.com/search/sneakers?s=' + name.replace(' ', '%20')),
                     ('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'))
                )
            )
