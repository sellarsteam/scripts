from datetime import datetime
from json import loads, JSONDecodeError
from typing import List

from jsonpath2 import Path
from requests import get
from user_agent import generate_user_agent

from core import api
from core.api import IndexType, TargetType, StatusType

class Parser(api.Parser):
    catalog: str = 'https://api.retailrocket.net/api/2.0/recommendation/popular/55379e776636b417f47acd68/?&categoryIds=56&categoryPaths=&session=5e67c3c66116160001f6cdaf&pvid=953289517825957&isDebug=false&format=json'
    pattern: str = '%Y-%m-%dT%H:%M:%S.%fZ'
    interval: float = 1
    name: str = 'sneakerhead_ru'

    def index(self) -> IndexType:
        return api.IInterval(self.name, 120)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(i.current_value['Model'], self.name,
                          i.current_value, self.interval)
            for i in Path.parse_str('$[*]').match(
                loads(get(self.catalog, headers={'user-agent': generate_user_agent()}).text)
            )
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: dict = target.data
                if content['CategoryNames'][2] == 'Кроссовки':
                    available = True
            else:
                return api.SFail(self.name, 'Unknown target type')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')
        except KeyError:
            return api.SFail(self.name, 'Wrong scheme')
        if available:
            return api.SSuccess(
                self.name,
                api.Result(
                    content['Model'],
                    content['Url'],
                    content['PictureUrl'],
                    content['Description'],
                    content['Price'],
                    tuple('all sizes'),
                    ()
                )
            )
