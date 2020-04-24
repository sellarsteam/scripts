from typing import List

from requests import get
from json import loads, JSONDecodeError
from user_agent import generate_user_agent

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger

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


def get_post_id(merchant_id, token):
    content = loads(get(f'https://api.vk.com/method/wall.get?owner_id={merchant_id[0]}&count=2&access_token={token}&v=5.52'
                        , headers={'user-agent': generate_user_agent()}).text)
    try:
        if content['response']['items'][0]['is_pinned']:
            return f"{merchant_id[0]}_{content['response']['items'][1]['id']}"
        else:
            return f"{merchant_id[0]}_{content['response']['items'][0]['id']}"
    except KeyError:
        return f"{merchant_id[0]}_{content['response']['items'][0]['id']}"


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.token = '8bc12e8f8bc12e8f8bc12e8fce8bb07efe88bc18bc12e8fd561ae191819697ceb653837'
        self.user_agent = generate_user_agent()
        self.interval: int = 1

    def index(self) -> IndexType:
        return api.IInterval(self.name, 1200)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(
                merchant_id[1], self.name,
                get_post_id(merchant_id, self.token), self.interval)
            for merchant_id in vk_merchants
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content = loads(get(f"https://api.vk.com/method/wall.getById?posts={target.data}"
                                    f"&access_token={self.token}&v=5.52").text)
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
                    ()
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
                    ()
                )
            )


