from typing import List

from lxml import etree
import re
from requests import get
from user_agent import generate_user_agent
from requests.exceptions import ReadTimeout

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://www.farfetch.com/ru/sets/men/new-in-this-week-eu-men.aspx?view=180&scale=284&category=136361&designer=214504|1664|1205035'
        self.interval: float = 1
        self.user_agent = generate_user_agent()

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:
                return [
                    api.TInterval(element.get('href').split('/')[-1],
                                  self.name, 'https://www.farfetch.com/' + element.get('href'), self.interval)
                    for element in etree.HTML(get(
                        self.catalog,
                        headers={'user-agent': self.user_agent,
                                 'connection': 'keep-alive', 'cache-control': 'max-age=0',
                                 'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                                 'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                                 'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                                 'sec-fetch-user': '?1',
                                 'accept-language': 'en-US,en;q=0.9'}
                    ).text).xpath('//a[@itemprop="itemListElement"]')
                ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                for_content = get(
                    target.data,
                    headers={'user-agent': self.user_agent,
                             'connection': 'keep-alive', 'cache-control': 'max-age=0',
                             'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
                             'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                             'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
                             'sec-fetch-user': '?1',
                             'accept-language': 'en-US,en;q=0.9',
                             'referer': self.catalog
                             })
                content: etree.Element = etree.HTML(for_content.text)
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        return api.SSuccess(
            self.name,
            api.Result(
                str(content.xpath('//span[@itemprop="name"]')[0].text) + ' ' + str(content.xpath('//span[@data-tstid="cardInfo-description"]')[0].text),
                target.data,
                'farfetch_ru',
                re.findall(r'(https?://[\S]+jpg)', str(for_content.content))[19].split('"600":"')[-1],
                '',
                (api.currencies['ruble'], float(content.xpath('//span[@data-tstid="priceInfo-original"]')[0].text.replace('₽', '').replace('\xa0', ''))),
                {},
                tuple(size.text + 'US' for size in content.xpath('//span[@data-tstid="sizeDescription"]')),
                ()
            )
        )
# 

# if __name__ == '__main__':
#     for_content = get(
#                 'https://www.farfetch.com/ru/shopping/men/nike-adapt-huarache-item-15246739.aspx?storeid=11218',
#                 headers={'user-agent': generate_user_agent(),
#                          'connection': 'keep-alive', 'cache-control': 'max-age=0',
#                          'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
#                          'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
#                          'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
#                          'sec-fetch-user': '?1',
#                          'accept-language': 'en-US,en;q=0.9',
#                          'referer': 'https://www.farfetch.com/ru/sets/men/new-in-this-week-eu-men.aspx?view=180&scale=284&category=136361&designer=214504|1664|1205035'
#                          })
#     content: etree.Element = etree.HTML(for_content.text)
#     # print(get(
#     #             'https://www.farfetch.com/ru/shopping/men/off-white-odsy-item-14811166.aspx?storeid=9359',
#     #             headers={'user-agent': generate_user_agent(),
#     #                      'connection': 'keep-alive', 'cache-control': 'max-age=0',
#     #                      'upgrade-insecure-requests': '1', 'sec-fetch-dest': 'document',
#     #                      'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
#     #                      'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate',
#     #                      'sec-fetch-user': '?1',
#     #                      'accept-language': 'en-US,en;q=0.9',
#     #                      'referer': 'https://www.farfetch.com/ru/sets/men/new-in-this-week-eu-men.aspx?view=180&scale=284&category=136361&designer=214504|1664|1205035'
#     #                      }).text)
#     print(str(content.xpath('//span[@itemprop="name"]')[0].text) + ' ' + str(content.xpath('//span[@data-tstid="cardInfo-description"]')[0].text))
#     print(re.findall(r'(https?://[\S]+jpg)', str(for_content.content))[19].split('"600":"')[-1])
#     print(int(content.xpath('//span[@data-tstid="priceInfo-original"]')[0].text.replace('₽', '').replace('\xa0', '')))
#     s = tuple(size.text for size in content.xpath('//span[@data-tstid="sizeDescription"]'))
#     print(s)