from datetime import datetime, timedelta, timezone
from typing import List, Union

from lxml import etree
from pycurl_requests import exceptions

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage, kw: Keywords):
        super().__init__(name, log, provider_, storage, kw)
        self.link: str = 'https://sneaker-street.ru/obuv?bfilter=brand[adidas,jordan,nike]/gender[women,men]'
        self.user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'

    @property
    def catalog(self) -> CatalogType:
        return api.CSmart(self.name, LinearSmart(self.time_gen(), 12, 5))

    @staticmethod
    def time_gen() -> float:
        return (datetime.utcnow() + timedelta(minutes=1)) \
            .replace(second=0, microsecond=250000, tzinfo=timezone.utc).timestamp()

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = []
        if mode == 0:

            counter = 0

            ok, resp = self.provider.request(self.link, headers={
             'authority': 'sneaker-street.ru',
             'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
             'cookie': '__cfduid=d9a01863207abbcce699545a9b7b05e0a1612450592; language=ru-ru; currency=RUB; rrpvid=215717844730303; rcuid=601825c6879c1300010f138c; _fbp=fb.1.1612450595524.113975469; rrlevt=1612450595637; _gcl_au=1.1.1815891103.1612450597; _ym_uid=1612450597759136351; _ym_d=1612450597; OCSESSID=36c1c255e3b089caec1d0f8c3b; __cf_bm=078fe7cafb0217e064022e9a50ed067928e1680b-1613827735-1800-AZVIoQxNVOfccNrm4QHweyrsHFSNJijU5Qa0Oiv4pf1uAJnaQT6Dp0EbfnsT4Vd1ymHR3KTmLVI4yausjgiRx7z1RIz3CelX7Y3Y9Obv1khU/byl65VipHUvymHi5GOqmA==; _ym_isad=2; _gid=GA1.2.2115282813.1613827756; _gat_UA-26560353-3=1; _ga_0F22SN37CV=GS1.1.1613827752.2.1.1613827941.56; _ga=GA1.1.138548856.1612450595',
             'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36'
            })

            if not ok:
                if isinstance(resp, exceptions.Timeout):
                    raise Exception('Timeout')
                else:
                    result.append(content)
                    return result

            lxml_resp = etree.HTML(resp.text)
            catalog = [element for element in lxml_resp.xpath('//div[@class="pli"]')]

            if not catalog:
                result.append(api.MAlert('Catalog is empty', self.name))

            for item in catalog:
                link = item.xpath('a[@class="pli__main"]')[0].get('href')

                counter = counter + 1
                name = item.xpath('a[@class="pli__main"]/span[@class="pli__main__brand"]')[0].text + ' ' + \
                       item.xpath('a[@class="pli__main"]/span[@class="pli__main__name"]')[0].text

                if self.kw.check(name.lower()):

                    if HashStorage.check_target(
                            api.Target(link, self.name, 0).hash()):
                        HashStorage.add_target(
                            api.Target(link, self.name, 0).hash())
                        additional_columns = {'Site': '[Sneaker Street](https://sneaker-street.ru/)'}
                    else:
                        additional_columns = {'Site': '[Sneaker Street](https://sneaker-street.ru/)',
                                              'Type': 'Restock'}

                    image = item.xpath('a/span[@class="pli__main__image"]/img')[0].get('src')

                    try:
                        price = api.Price(api.CURRENCIES['RUB'],
                                          float(item.xpath('a/span[@class="pli__main__price"]')[0]
                                                .text.replace(' ', '').replace('\n', '').replace('₽', '')))
                    except ValueError:
                        price = api.Price(api.CURRENCIES['RUB'],
                                          float(item.xpath('a/span[@class="pli__main__price"]'
                                                           '/span[@class="pli__main__price__new"]')
                                                [0].text.replace(' ', '').replace('\n', '').replace('₽', '')),
                                          float(item.xpath('a/span[@class="pli__main__price"]'
                                                           '/span[@class="pli__main__price__old"]')
                                                [0].text.replace(' ', '').replace('\n', '').replace('₽', '')))

                    raw_sizes = [api.Size(size.text.replace('\n', ''),
                                          "http://static.sellars.cf/links?site=sneakerstreet&product_id=" +
                                          size.get('onclick').split('add(')[-1].replace(')', '').split(', ')[0] +
                                          '&option1='
                                          + size.get('onclick')
                                          .split('add(')[-1]
                                          .replace(')', '')
                                          .split(', ')[-1].split(':')[0].replace('{', '').replace('\"', '')
                                          + '&option2=' + size.get('onclick').split('add(')[-1].replace(')', '')
                                          .split(', ')[-1].split(':')[-1].replace('}', '').replace('\"', ''))
                                 for size in item.xpath('div[@class="pli__options"]/button')]

                    sizes = api.Sizes(api.SIZE_TYPES[''], raw_sizes)

                    stockx_link = f'https://stockx.com/search/sneakers?s={name.replace(" ", "%20")}'

                    result.append(
                        IRelease(
                            link + f'?shash={sizes.hash().hex()}&sprice={price.hash().hex()}',
                            'sneakerstreet',
                            name,
                            image,
                            '',
                            price,
                            sizes,
                            [
                                FooterItem('StockX', stockx_link),
                                FooterItem('Cart', 'https://sneaker-street.ru/checkout/')
                            ],
                            additional_columns
                        )
                    )

            if isinstance(content, api.CSmart):
                if result or content.expired:
                    content.gen.time = self.time_gen()
                    content.expired = False
                result.append(content)
            else:
                result.extend([self.catalog, api.MAlert('Script is awake', self.name)])

        return result
