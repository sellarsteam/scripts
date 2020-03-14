from datetime import datetime
from json import loads, JSONDecodeError
from typing import List

from jsonpath2 import Path
from requests import get
from user_agent import generate_user_agent

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


# TODO: Optimize execute url
# TODO: Checking for discount


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://api.nike.com/product_feed/threads/v2/?count=24&filter=marketplace%28RU%29&filter=language%28ru%29&filter=upcoming%28true%29&filter=channelId%28010794e5-35fe-4e32-aaff-cd2c74f89d61%29&filter=exclusiveAccess%28true%2Cfalse%29&sort=effectiveStartSellDateAsc&fields=active&fields=id&fields=productInfo'
        self.channel: str = '010794e5-35fe-4e32-aaff-cd2c74f89d61'
        self.pattern: str = '%Y-%m-%dT%H:%M:%S.%fZ'
        self.interval: float = 1

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:  # TODO: Error handling support
        return [
            api.TInterval(i.current_value['productInfo'][0]['productContent']['title'], self.name,
                          i.current_value['id'], self.interval)
            for i in Path.parse_str('$.objects[*][?(@.productInfo[0].availability.available = true)]').match(
                loads(get(self.catalog, headers={'user-agent': generate_user_agent()}).text)
            )
        ]

    def execute(self, target: api.TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: dict = loads(
                    get(
                        f'https://api.nike.com/product_feed/threads/v2/{target.data}?channelId={self.channel}&marketplace=RU&language=ru',
                        headers={'user-agent': generate_user_agent()}
                    ).text
                )
                if content['productInfo'][0]['merchProduct']['publishType'] == 'FLOW':
                    if datetime.strptime(content['productInfo'][0]['merchProduct']['commerceStartDate'],
                                         self.pattern).timestamp() < datetime.utcnow().timestamp():
                        available = True
                elif content['productInfo'][0]['merchProduct']['publishType'] == 'LAUNCH':
                    if datetime.strptime(content['productInfo'][0]['launchView']['startEntryDate'],
                                         self.pattern).timestamp() < datetime.utcnow().timestamp():
                        available = True
                else:
                    return api.SFail(self.name, 'Unknown "publishType"')
            else:
                return api.SFail(self.name, 'Unknown target type')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')
        except KeyError:
            return api.SFail(self.name, 'Wrong scheme')
        if available:
            skus = [i.current_value for i in Path.parse_str('$.productInfo[0].availableSkus[*].id').match(content)]
            return api.SSuccess(
                self.name,
                api.Result(
                    content['productInfo'][0]['productContent']['title'],
                    f'https://nike.com/ru/launch/t/{content["publishedContent"]["properties"]["seo"]["slug"]}',
                    'nike-snkrs',
                    content['productInfo'][0]['imageUrls']['productImageUrl'],
                    content['productInfo'][0]['productContent']['descriptionHeading'],
                    (api.currencies['ruble'], content['productInfo'][0]['merchPrice']['currentPrice']),
                    {},
                    tuple(
                        (
                            i['countrySpecifications'][0]['localizedSize'],
                            f'https://www.nike.com/ru/launch/t/{content["productInfo"][0]["productContent"]["slug"]}'
                            f'/?productId={content["productInfo"][0]["merchPrice"]["productId"]}'
                            f'&size={i["countrySpecifications"][0]["localizedSize"].split(" ")[0]}'
                        ) for i in content['productInfo'][0]['skus'] if i['id'] in skus),
                    ()
                )
            )
        else:
            return api.SWaiting(target)
