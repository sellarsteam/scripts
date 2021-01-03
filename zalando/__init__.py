import os

from datetime import datetime, timedelta, timezone
from typing import List, Union

from ujson import loads
import subprocess

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.library import SubProvider, Keywords
from source.tools import LinearSmart, ScriptStorage


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.link: str = "curl -s 'https://en.zalando.de/api/catalog/articles?brands=JOC&categories=mens-shoes&limit=84" \
                         "&offset=0' -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 " \
                         "Firefox/71.0' -H 'Accept: */*' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H " \
                         "'Referer: https://en.zalando.de/mens-shoes/jordan.nike-sb/' -H 'x-zalando-octopus-tests: " \
                         "%5B%7B%22testName%22%3A%22cyberweek-gradient%22%2C%22testVariant%22%3A%22Without%20gradient" \
                         "%20background%22%2C%22testFeedbackId%22%3A%2200000000-0000-0000-0000-000000000000" \
                         "%3A__EMPTY__%22%7D%2C%7B%22testName%22%3A%22blackfriday-gradient%22%2C%22testVariant%22%3A" \
                         "%22WITHOUT_GRADIENT_BACKGROUND%22%2C%22testFeedbackId%22%3A%2200000000-0000-0000-0000" \
                         "-000000000000%3A__EMPTY__%22%7D%2C%7B%22testName%22%3A%22native-image-lazy-loading%22%2C" \
                         "%22testVariant%22%3A%22LAZY_LOADING%22%2C%22testFeedbackId%22%3A%220e15aaf1-8c5c-4be2-98bf" \
                         "-6eda22d1c358%3A%22%7D%5D' -H 'x-zalando-catalog-nakadi-context: " \
                         "%7B%22previous_categories%22%3A%5B%22mens-shoes%22%5D%2C%22previous_selected_filters%22%3A" \
                         "%5B%7B%22key%22%3A%22brands%22%2C%22values%22%3A%5B%22JOC%22%2C%22NS4%22%5D%2C%22kind%22%3A" \
                         "%22values%22%7D%5D%2C%22preselected_filters%22%3A%5B%5D%7D' -H 'x-zalando-catalog-label: " \
                         "true' -H 'x-xsrf-token: " \
                         "AAAAAKVFPSKQbLoY9slxgLjTdvO4wf6nVTXgrLB7qronkrUXo8fCRJhVtOBtae3Tf2jsciYlVLC_" \
                         "-5I7X33IWuv3QvfbgU671tCNLipYnkEllUWpgsPVfrwCXmq0F_cGgjhtOkeNAnKow-HIf8cJIA==' -H " \
                         "'Connection: keep-alive' -H 'Cookie: " \
                         "_abck=8EDC4D85739098B4B56F8B29D951C55B~-1~YAAQRVzaF913FRV2AQAAgHxZnwUIh5GqYypFE0cOft" \
                         "+4kIRcgixi1OtyYsLSQBumjvMytgW0Ktu1b2K1AjR" \
                         "+ESknVgayoOXcWHkT8GHgKkjt7T0jewxKUqbLlgjpMrMWXNBxwHsNxefMKgU7GFr" \
                         "+tFQvYZjZJDmgfJJiJGdUW0Q368wPv/+jlBOJ10cDz34kSjivg2sr5LCFZSohoSzfnXE/6/GnvOehyycCcDFqc" \
                         "/hjBIDPG6PjZgz6wX73jGHMmGUL5JHXrw1C0S/EjCFiG" \
                         "/XKOGOteGhOq2ImDaklwDs9GiDB898w2pvr8MkfQ98yT2CYD1uOoSkqNzz" \
                         "++Q9ZAWPBlCDNAyuMP15jGrPSseJWaX7zWOf1yi3wf8rZYdijg/2AB+Fuadlcspm6BwYPtdxaa91gNEl8QFxpynfLp" \
                         "/w+YT4JEt0tVDQAm61IT73V4EVPXmJl2osvp4qiRA/TpLTOmXcQDw==~-1~-1~-1; fvgs_ml=mosaic; " \
                         "Zalando-Client-Id=bc8569bb-299b-49a0-8251-e027ab41b4b9; language-preference=en; ncx=m; " \
                         "_gcl_au=1.1.1962197817.1608985864; sqt_cap=1608985020007; _ga=GA1.2.1549890469.1608985865; " \
                         "_gid=GA1.2.189735221.1608985865; _fbp=fb.1.1608985865643.72093230; " \
                         "bm_sz=2373E9DF86CE7CCBBA2F878B5F0345F0" \
                         "~YAAQRVzaFyFnFRV2AQAAv5dNnwqDTEvt7NcHf4Iu408IItUFveDFKLtab6ohnyX9KxIOa3Ydj1b9Jo7TmTE9Y" \
                         "GB5gL9jYSgHVDCIm+3im7V1WZGOuY4+L0RnJEmwhWHBtZyWCO/kLWouRMAjOyOCM+Wimqqo2vzFH3sz87sNwz9+g" \
                         "mvUVvbcqAWNI7eiJnQ/q504m28UB4LZ2/20SDQN9qBvMbSz9VPcv9efyq7RP6RTFMVqfbw82FUOHGg3izark9oSC" \
                         "V8lTZ1nk8USN9D6sx1nIwFB9j3ZRpLI0IQ=; frsx=AAAAAKVFPSKQbLoY9slxgLjTdvO4wf6nVTXgrLB7qronkrU" \
                         "Xo8fCRJhVtOBtae3Tf2jsciYlVLC_-5I7X33IWuv3QvfbgU671tCNLipYnkEllUWpgsPVfrwCXmq0F_cGgjhtOkeN" \
                         "AnKow-HIf8cJIA==; mpulseinject=false; _gat_zalga=1' -H 'If-None-Match: W/\"11ff0-l+72Tcif" \
                         "t2oJYz5HQOCT8dzbNIo\"' -H 'TE: Trailers' "

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
            output = subprocess.Popen(self.link, shell=True, stdout=subprocess.PIPE, bufsize=-1,
                                      stdin=None, stderr=None)
            response = output.communicate()[0]

            catalog = loads(response)

            if len(catalog) == 0:
                raise Exception('Catalog is empty')

            for element in catalog['articles']:

                link = f'https://en.zalando.de/{element["url_key"]}.html'
                name = element["name"]
                if Keywords.check(element["url_key"], divider='-') or Keywords.check(element["name"]):
                    price = api.Price(api.CURRENCIES['EUR'],
                                      float(element['price']['original'].replace(' ', '')
                                            .replace(',', '.').replace('€', '')))
                    image = 'https://img01.ztat.net/article/' + element['media'][0]['path']
                    sizes = api.Sizes(api.SIZE_TYPES[''],
                                      [
                                          api.Size(size)
                                          for size in element['sizes']
                                      ]
                                      )
                    result.append(
                        IRelease(
                            link + f'?shash={sizes.hash().hex()}',
                            'zalando',
                            name,
                            image,
                            'Russian IP can be blocked',
                            price,
                            sizes,
                            [
                                FooterItem('Cart', 'https://en.zalando.de/cart/'),
                                FooterItem('Login', 'https://en.zalando.de/login?target=/myaccount/')
                            ],
                            {'Site': '[Zalando](https://en.zalando.de)'}
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
