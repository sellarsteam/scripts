from json import loads, JSONDecodeError
from typing import List

from jsonpath2 import Path
from lxml import etree
from requests import get
from user_agent import generate_user_agent


from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.catalog: str = 'https://api.retailrocket.net/api/2.0/recommendation/popular/55379e776636b417f47acd68/?&categoryIds=56&categoryPaths=&session=5e67c3c66116160001f6cdaf&pvid=953289517825957&isDebug=false&format=json'
        self.user_agent = generate_user_agent()
        self.interval: float = 1

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(
                i.current_value['Model'],
                self.name,
                i.current_value['Url'], self.interval
            )
            for i in Path.parse_str('$[*]').match(
                loads(get(self.catalog, headers={'user-agent': self.user_agent}).text)
            ) if i.current_value['CategoryNames'][0] == 'Обувь' or i.current_value['CategoryNames'][1] == 'Обувь'
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: etree.Element = etree.HTML(
                    get(target.data, self.user_agent).content)
                if content.xpath('//div[@class="sizes-chart-item selected"]') != () and content.xpath('//a[@class="size_range_name "]') != []:
                    available = True
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')
        except KeyError:
            return api.SFail(self.name, 'Wrong scheme')
        if available:
            return api.SSuccess(
                self.name,
                api.Result(
                    content.xpath('//meta[@itemprop="name"]')[0].get('content'),
                    target.data,
                    'russian-retailer',
                    content.xpath('//meta[@itemprop="image"]')[0].get('content'),
                    content.xpath('//meta[@itemprop="description"]')[0].get('content'),
                    (api.currencies['ruble'], float(content.xpath('//meta[@itemprop="price"]')[0].get('content'))),
                    {},
                    tuple((size.text.replace('\n', '')).replace(' ', '') for size in (content.xpath(
                        '//div[@class="flex-row sizes-chart-items-tab"]'))[0].xpath(
                        'div[@class="sizes-chart-item selected" or @class="sizes-chart-item"]')),
                    ()
                )
            )
        else:
            return api.SWaiting(target)
