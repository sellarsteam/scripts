from json import JSONDecodeError
from typing import List, Union

import yaml
from ujson import loads
from user_agent import generate_user_agent

from source import api
from source import logger
from source.api import CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType, IRelease, FooterItem
from source.cache import HashStorage
from source.library import SubProvider
from source.tools import ScriptStorage

vk_merchants = (
    ('507698109', 'Ren Chris'),
    ('564747202', 'Isn Resale'),
    ('279312075', 'Ярослав Арефьев'),
    ('416361025', 'Heng Jian'),
    ('196746875', 'Даниил Бабаев'),
    ('562275038', 'Игорь Чжан'),
    ('368686985', 'Аньчжоу Цуй'),
    ('466245764', 'Su Yingshuo'),
    ('561114731', 'Лао Бэн'),
    ('562914497', 'Мао Миша'),
    ('536404559', 'Viiii Vika'),
    ('548261318', '铭 小茗'),
    ('526566071', 'Ьин Бин'),
    ('354212266', 'Юй Чжаодоп'),
    ('435773397', '唐新宇 唐新宇'),
    ('521130049', 'Синьли Мен'),
    ('491969248', 'Pan Jingwei'),
    ('90213067', 'Александр Бабурин'),
    ('60234368', 'Виктор Гусев'),
    ('583009195', 'Diễm Kiều Nguyễn Phi'),
    ('567080917', 'Phi Long'),
    ('517519146', 'Vladimir Korolev'),
    ('569650181', 'Ivan Igorevich'),
    ('238537400', 'Глеб Казаков'),
    ('536388419', 'Аврора Пань')
)


def key_words():
    for i in 'надо', 'дай', 'беру', 'куплю', 'need', 'ищу', 'есть', 'пиши':
        for j in range(3):
            if j == 0:
                yield i
            elif j == 1:
                yield i.capitalize()
            elif j == 2:
                yield i.upper()


def get_post_id(merchant_id, token, provider):
    ok, content = provider.request(
        f'https://api.vk.com/method/wall.get?owner_id={merchant_id[0]}&count=2&access_token={token}&v=5.52')

    if not ok:
        raise content

    content = loads(content.content)

    try:
        if content['response']['items'][0]['is_pinned']:
            return f"{merchant_id[0]}_{content['response']['items'][1]['id']}"
        else:
            return f"{merchant_id[0]}_{content['response']['items'][0]['id']}"
    except KeyError:
        try:
            return f"{merchant_id[0]}_{content['response']['items'][0]['id']}"
        except KeyError:
            return 0


class Parser(api.Parser):
    def __init__(self, name: str, log: logger.Logger, provider_: SubProvider, storage: ScriptStorage):
        super().__init__(name, log, provider_, storage)
        self.user_agent = generate_user_agent()
        self.counter = 0
        self.number_of_token = 0
        self.interval: int = 1
        if self.storage.check('secret.yaml'):
            raw = yaml.safe_load(self.storage.file('secret.yaml'))
            if isinstance(raw, dict):
                if isinstance(raw['token'], list):
                    self.tokens = raw['token']
                else:
                    self.log.error('secret.yaml must contain tokens')
            else:
                self.log.error('secret.yaml must contain dict')
        else:
            self.log.error('secret.yaml doesn\'t exist')
            raise FileNotFoundError

    @property
    def catalog(self) -> CatalogType:
        return api.CInterval(self.name, 1200.)

    def execute(
            self,
            mode: int,
            content: Union[CatalogType, TargetType]
    ) -> List[Union[CatalogType, TargetType, RestockTargetType, ItemType, TargetEndType]]:
        result = [content]
        if mode == 0:
            targets = []
            try:
                for merchant_id in vk_merchants:
                    if self.counter == 5000:
                        self.number_of_token += 1
                        if self.number_of_token == len(self.tokens):
                            self.number_of_token = 0
                        self.counter = 0
                    token = self.tokens[self.number_of_token]
                    post_id = get_post_id(merchant_id, token, self.provider)
                    target = api.Target(str(post_id), self.name, 0)
                    if HashStorage.check_target(target.hash()):
                        if post_id != 0:
                            targets.append([target, merchant_id[1]])
                            HashStorage.add_target(target.hash())
                    self.counter += 1
            except JSONDecodeError as e:
                raise e
            try:
                for target in targets:
                    if self.counter == 5000:
                        self.number_of_token += 1
                        if self.number_of_token == len(self.tokens):
                            self.number_of_token = 0
                        self.counter = 0
                    token = self.tokens[self.number_of_token]
                    ok, resp = self.provider.request(
                        f'https://api.vk.com/method/wall.getById?posts={target[0].name}&access_token={token}&v=5.52')

                    if not ok:
                        if isinstance(resp, ConnectionError):
                            return [api.CInterval(self.name, 600.)]
                        else:
                            raise resp

                    try:
                        content = loads(resp.content)

                    except ValueError:
                        return [api.CInterval(self.name, 600.)]

                    self.counter += 1
                    text = content['response'][0]['text']
                    available = False
                    for key_word in key_words():
                        if key_word in text:
                            available = True
                            break
                    if available:
                        try:
                            photo = content['response'][0]['attachments'][0]['photo']['photo_1280']
                        except KeyError:
                            photo = ''
                        result.append(IRelease(
                            f"https://vk.com/id{target[0].name.split('_')[0]}",
                            'vk-merchants',
                            target[1],
                            photo,
                            text,
                            api.Price(api.CURRENCIES['USD'], float(0)),
                            api.Sizes(api.SIZE_TYPES[''], []),
                            [
                                FooterItem('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'),
                            ]
                        )
                        )
            except JSONDecodeError as e:
                raise e
            result.append(content)
        return result
