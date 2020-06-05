import os
from json import loads, JSONDecodeError
from typing import List

import yaml
from user_agent import generate_user_agent

from source import api
from source.api import IndexType, TargetType, StatusType
from source.logger import Logger

vk_merchants = (
    ('507698109', 'Ren Chris'),
    ('467787089', 'Уожу Мзй-Линь'),
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
    ('240373496', 'Вадим Толмац'),
    ('435212744', '吴 晨浩'),
    ('526566071', 'Ьин Бин'),
    ('354212266', 'Юй Чжаодоп'),
    ('435773397', '唐新宇 唐新宇'),
    ('521130049', 'Синьли Мен'),
    ('491969248', 'Pan Jingwei'),
    ('180322689', 'Илья Царёв👨‍💻'),
    ('90213067', 'Александр Бабурин'),
    ('60234368', 'Виктор Гусев'),
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
    content = loads(provider.get(
        f'https://api.vk.com/method/wall.get?owner_id={merchant_id[0]}&count=2&access_token={token}&v=5.52'))
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
    def __init__(self, name: str, log: Logger, provider: api.SubProvider, storage):
        super().__init__(name, log, provider, storage)
        self.user_agent = generate_user_agent()
        self.counter = 0
        self.number_of_token = 0
        self.interval: int = 1
        if os.path.isfile(os.path.dirname(os.path.realpath(__file__)) + '/secret.yaml'):
            raw = yaml.safe_load(open(os.path.dirname(os.path.realpath(__file__)) + '/secret.yaml'))
            if isinstance(raw, dict):
                if isinstance(raw['token'], list):
                    self.tokens = raw['token']
                    self.active = True
                else:
                    self.log.error('secret.yaml must contain tokens')
            else:
                self.log.error('secret.yaml must contain dict')
        else:
            self.log.error('secret.yaml doesn\'t exist')

    def index(self) -> IndexType:
        return api.IInterval(self.name, 10)

    def targets(self) -> List[TargetType]:
        targets = list()
        for merchant_id in vk_merchants:
            if self.counter == 5000:
                self.number_of_token += 1
                if self.number_of_token == len(self.tokens):
                    self.number_of_token = 0
                self.counter = 0
            token = self.tokens[self.number_of_token]
            post_id = get_post_id(merchant_id, token, self.provider)
            if post_id != 0:
                targets.append(api.TInterval(merchant_id[1], self.name, post_id, self.interval))
            self.    counter += 1
        return targets

    def execute(self, target: TargetType) -> StatusType:
        if self.counter == 5000:
            self.number_of_token += 1
            if self.number_of_token == len(self.tokens):
                self.number_of_token = 0
            self.counter = 0
        token = self.tokens[self.number_of_token]
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content = loads(self.provider.get(f"https://api.vk.com/method/wall.getById?posts={target.data}"
                                                  f"&access_token={token}&v=5.52"))
                self.    counter += 1
                text = content['response'][0]['text']
                for key_word in key_words():
                    if key_word in text:
                        available = True
                        break
            else:
                return api.SFail(self.name, 'Unknown target type')
        except JSONDecodeError:
            return api.SFail(self.name, 'Exception JSONDecodeError')

        if available:
            try:
                photo = content['response'][0]['attachments'][0]['photo']['photo_1280']
            except KeyError:
                photo = ''
            return api.SSuccess(
                self.name,
                api.Result(
                    target.name,
                    f"https://vk.com/id{target.data.split('_')[0]}",
                    'vk-merchants',
                    photo,
                    text,
                    (api.currencies['USD'], 0),
                    {},
                    (),
                    (('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'),)
                )
            )
        else:
            return api.SSuccess(  # TODO Return SFail if post is wrong
                self.name,
                api.Result(
                    'Post is wrong',
                    f"https://vk.com/id{target.data.split('_')[0]}",
                    'tech',
                    '',
                    text,
                    (api.currencies['USD'], 0),
                    {},
                    (),
                    (('Feedback', 'https://forms.gle/9ZWFdf1r1SGp9vDLA'),)
                )
            )
