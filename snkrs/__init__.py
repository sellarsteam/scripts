from datetime import datetime, timezone
from json import loads, JSONDecodeError
from time import mktime, strptime, time
from typing import List, Union

from user_agent import generate_user_agent

from source import api
from source.api import CURRENCIES, SIZE_TYPES, CatalogType, TargetType, RestockTargetType, TargetEndType, ItemType, \
    Price, Sizes, Size
from source.cache import HashStorage
from source.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger, provider: api.SubProvider):
        super().__init__(name, log, provider)
        self.url = 'https://www.nike.com/ru/launch/t/'
        self.api = 'https://api.nike.com/product_feed/threads/v2/'
        self.filter: str = '&filter=marketplace(RU)&filter=language(ru)' \
                           '&filter=channelId(010794e5-35fe-4e32-aaff-cd2c74f89d61)'
        self.catalog_filter: str = '?count=36&filter=upcoming(true)&fields=publishedContent.properties.seo.slug'
        self.item_filter: str = '?fields=productInfo.merchProduct,productInfo.merchPrice,productInfo.productContent,p' \
                                'roductInfo.imageUrls,productInfo.launchView,productInfo.skus,productInfo.availableSkus'
        self.pattern: str = '%Y-%m-%dT%H:%M:%S.%fZ'

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
            result.append(content)
            result.extend([
                api.TInterval(i['publishedContent']['properties']['seo']['slug'], self.name, 0, 0) for i in
                loads(self.provider.get(f'{self.api}{self.catalog_filter}{self.filter}',
                                        headers={'user-agent': generate_user_agent()}))['objects']
                if not i['publishedContent']['properties']['seo']['slug'].count('test')
            ])
            return result
        elif mode == 1:
            has_announce = False

            try:
                try:
                    items = loads(self.provider.get(
                        f'{self.api}{self.item_filter}&filter=seoSlugs({content.name}){self.filter}',
                        headers={'user-agent': generate_user_agent()}
                    ))['objects'][0]['productInfo']
                except JSONDecodeError:
                    self.log.error(f'Bad json: {content.name}')
                    return [api.TEFail(content, f'Bad json\n{content.hash()}')]

                for i in items:
                    data = [
                        f'{self.url}{content.name}',
                        'nike-snkrs',
                        i['productContent']['fullTitle'],
                        i['imageUrls']['productImageUrl'],
                        i["productContent"]["descriptionHeading"],
                        Price(CURRENCIES['RUB'], i['merchPrice']['currentPrice'],
                              i['merchPrice']['fullPrice'] if i['merchPrice']['discounted'] else 0),
                        Sizes(SIZE_TYPES[''], (
                            Size(
                                f'{s["nikeSize"]} [{i["availableSkus"][j]["level"]}]',
                                f'{self.url}{content.name}/?productId={i["merchPrice"]["productId"]}'
                                f'&size={s["nikeSize"].partition(" ")[0]}'
                            ) for j, s in enumerate(i['skus'])
                        )),
                        [
                            api.FooterItem('StockX', f'https://stockx.com/search/sneakers?s=' +
                                           i['productContent']['title'].replace('"', '').replace("'", '')
                                           .replace('“', '').replace('”', '').replace(' ', '%20')),
                            api.FooterItem('Cart', 'https://www.nike.com/cart'),
                            api.FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA')
                        ]
                    ]

                    date = mktime(strptime(i['launchView']['startEntryDate'] if 'launchView' in i else
                                           i['merchProduct']['commerceStartDate'], self.pattern))

                    if date < time():
                        item = api.IRelease(*data)
                        if HashStorage.check_item(item.hash(4)):
                            result.append(item)
                    else:
                        has_announce = True
                        item = api.IAnnounce(*data)
                        item.fields['Attention'] = 'Size of stocks may be changed at release'
                        item.fields['Release date'] = datetime.fromtimestamp(date).strftime('%H:%M %d/%m/%Y')
                        if HashStorage.check_item(item.hash(4)):
                            result.append(item)

            except KeyError:
                self.log.error(f'Bad schema: {content.name}')
                return [api.TEFail(content, f'Bad schema\n{content.hash()}')]

            if result or has_announce:
                if isinstance(content, api.TSmart):
                    content.timestamp = date + 1
                    result.append(content)
                else:
                    result.append(
                        api.TSmart(content.name, self.name, 0, date + 1, 100)
                    )

                return result
            else:
                HashStorage.add_target(api.TInterval(content.name, self.name, 0, 0.).hash())
                return [api.TESuccess(content, 'No more products')]
