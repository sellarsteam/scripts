from typing import List, Union

from lxml import etree

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.library import SubProvider


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider):
        super().__init__(name, log, provider_)
        self.link: str = 'https://www.solebox.com/en_RU/c/new'
        self.interval: int = 1
        self.headers = {'authority': 'www.solebox.com',
                        'scheme': 'https',
                        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,'
                                  '*/*;q=0.8,application/signed-exchange;v=b3',
                        'accept-encoding': 'gzip, deflate, br',
                        'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
                        'cache-control': 'max-age=0',
                        'upgrade-insecure-requests': '1',
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
                                      'like Gecko) Chrome/73.0.3683.103 Safari/537.36'}

    @property
    def catalog(self) -> CatalogType:
        return api.CInterval(self.name, 1200.)

    def execute(self, mode: int, content: Union[CatalogType, TargetType]) -> List[
        Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = [content]
        if mode == 0:
            page_content = etree.HTML(self.provider.get(
                self.link, headers=self.headers, proxy=True, mode=1, timeout=60
            ))
            for element in page_content.xpath('//a[@class="b-product-tile-image-link js-product-tile-link"]'):
                if 'yeezy' in element.get('href') or 'air' in element.get('href') or 'sacai' in element.get('href') \
                        or 'dunk' in element.get('href') or 'retro' in element.get('href'):
                    result.append(api.TInterval('https://www.solebox.com' + element.get('href'), self.name, 0, 3.))
            return result
        elif mode == 1:
            page_content: etree.Element = etree.HTML(
                self.provider.get(content.name, headers=self.headers,
                                  proxy=True, mode=1, timeout=60))
            try:
                name = page_content.xpath('//span[@class="b-breadcrumb-text"]')[0].text
            except IndexError:
                name = ''
            try:
                date = page_content.xpath('//button[@class="f-pdp-button f-pdp-button--release js-btn-release"]')[
                    0].text
            except IndexError:
                date = 'Date not indicated'
            try:
                if page_content.xpath(
                        '//button[@class="f-pdp-button f-pdp-button-coming-soon f-pdp-button--lowercase"]') \
                        or page_content.xpath('//button[@class="f-pdp-button f-pdp-button--release js-btn-release"]'):
                    result.append(
                        api.IAnnounce(
                            content.name,
                            'solebox',
                            name,
                            page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                            '',
                            api.Price(api.CURRENCIES['EUR'], float(
                                page_content.xpath('//span[@class="b-product-tile-price-item"]')[0].text.replace('€',
                                                                                                                 '').replace(
                                    '\n', '').replace(' ', '').split(',')[0])),
                            api.Sizes(api.SIZE_TYPES[''], []),
                            [
                                FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                           name.replace(' ', '%20').replace('"', '').replace('\n', '')),
                                FooterItem('Cart', 'https://www.solebox.com/cart'),
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            {'Site': 'Solebox', 'Date': date}
                        )
                    )
                else:
                    sizes = [api.Size(size.get('data-value') + ' EU', size.get('href'))
                             for size in
                             page_content.xpath('//a[@class="js-pdp-attribute-btn b-pdp-swatch-link '
                                                'js-pdp-attribute-btn--size"]')]
                    name = content.name.split('/')[5].split('%')[0].replace('_', ' ').upper()
                    if sizes:
                        result.append(IRelease(
                            content.name,
                            'solebox',
                            name,
                            page_content.xpath('//meta[@property="og:image"]')[0].get('content'),
                            '',
                            api.Price(api.CURRENCIES['EUR'], float(
                                page_content.xpath('//span[@class="b-product-tile-price-item"]')[0].text.replace('€',
                                                                                                                 '').replace(
                                    '\n', '').replace(' ', '').split(',')[0])),
                            api.Sizes(api.SIZE_TYPES[''], sizes),
                            [
                                FooterItem('StockX', 'https://stockx.com/search/sneakers?s=' +
                                           name.replace(' ', '%20').replace('"', '').replace('\n', '')),
                                FooterItem('Cart', 'https://www.solebox.com/cart/cart'),
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                            ],
                            {'Site': 'Solebox'}
                        )
                        )
                        result.append(api.TESuccess(content, 'Item was Released'))

            except etree.XMLSyntaxError:
                raise etree.XMLSyntaxError('XMLDecodeError')
        return result
