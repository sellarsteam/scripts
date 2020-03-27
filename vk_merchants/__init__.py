from typing import List

from lxml import etree
from requests import get
from user_agent import generate_user_agent

from core import api
from core.api import IndexType, TargetType, StatusType
from core.logger import Logger

vk_merchants = (
    'https://vk.com/id507698109',
    'https://vk.com/id467787089',
    'https://vk.com/id564747202',
    'https://vk.com/id279312075',
    'https://vk.com/id416361025',
    'https://vk.com/babaevdd',
    'https://vk.com/id562275038',
    'https://vk.com/id368686985',
    'https://vk.com/id466245764',
    'https://vk.com/id561114731',
    'https://vk.com/id562914497',
    'https://vk.com/vika940222',
    'https://vk.com/id548261318',
    'https://vk.com/id240373496',
    'https://vk.com/id435212744',
    'https://vk.com/id526566071',
    'https://vk.com/id354212266',
    'https://vk.com/id435773397',
    'https://vk.com/id521130049',
    'https://vk.com/id491969248',
    'https://vk.com/id180322689',
    'https://vk.com/mymoneystackin',
    'https://vk.com/niggazzwithattitude',
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


def first_not_fixed_post(merchant_link):
    try:
        fixed_label = etree.HTML(get(merchant_link).content).xpath('//span[@class="explain"]')[0].text
        if fixed_label == 'запись закреплена':
            return 'https://vk.com' + etree.HTML(get(merchant_link).content).xpath('//a[@class="wi_date"]')[1].get(
                'href')
        else:
            return 'https://vk.com' + etree.HTML(get(merchant_link).content).xpath('//a[@class="wi_date"]')[0].get(
                'href')
    except IndexError:
        return 'https://vk.com' + etree.HTML(get(merchant_link).content).xpath('//a[@class="wi_date"]')[0].get('href')


class Parser(api.Parser):
    def __init__(self, name: str, log: Logger):
        super().__init__(name, log)
        self.user_agent = generate_user_agent()
        self.interval: int = 45

    def index(self) -> IndexType:
        return api.IInterval(self.name, 1200)

    def targets(self) -> List[TargetType]:
        return [
            api.TInterval(
                merchant_link.split('/')[3], self.name,
                first_not_fixed_post(merchant_link), self.interval)
            for merchant_link in vk_merchants
        ]

    def execute(self, target: TargetType) -> StatusType:
        try:
            if isinstance(target, api.TInterval):
                available: bool = False
                content: etree.Element = etree.HTML(get(target.data).text)
                try:
                    text = content.xpath('//div[@class="pi_text" or @class="pi_text zoom_text"]')[0].text
                except IndexError:
                    return api.SWaiting(target)

                for key_word in key_words():
                    if key_word in text:
                        available = True
                        break
            else:
                return api.SFail(self.name, 'Unknown target type')
        except etree.XMLSyntaxError:
            return api.SFail(self.name, 'Exception XMLDecodeError')

        if available:
            try:
                return api.SSuccess(
                    self.name,
                    api.Result(
                        content.xpath('//a[@class="pi_author"]')[0].text,
                        target.data,
                        'vk-merchants',
                        content.xpath(
                            '//div[@style]'
                        )[2].get('style').split('url(')[-1].replace(')', '').replace(';', ''),
                        text,
                        (api.currencies['dollar'], 0),
                        {},
                        (),
                        ()
                    )
                )
            except IndexError:
                return api.SSuccess(
                    self.name,
                    api.Result(
                        content.xpath('//a[@class="pi_author"]')[0].text,
                        target.data,
                        'vk_merchants',
                        '',
                        text,
                        (api.currencies['dollar'], 0),
                        {},
                        (),
                        ()
                    )
                )
        else:
            return api.SWaiting(target)


if __name__ == '__main__':
    print(get('https://vk.com/egorovvanya').text)
    merchant_link = 'https://vk.com/egorovvanya'
    # print(etree.HTML(get(merchant_link).content).xpath('//span[@class="explain"]')[0].text)
