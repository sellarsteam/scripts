from typing import Tuple

from core.api import Result

currencies: tuple = ('£', '$', '€', '₽', '¥', 'kr', '₴', 'Br', 'zł')


def build(item: Result) -> str:
    compiled: str = ''
    if item.url:
        compiled += f'<a href="{item.url}"><b>{item.name}</b></a>\n'
    else:
        compiled += f'<b>{item.name}</b>\n'
    if item.description:
        if item.description.__len__() > 512:
            item.description = item.description[:512] + '...'
        compiled += f'{item.description}\n'
    if 2 <= item.price.__len__() <= 3 and item.price[1]:
        if item.price.__len__() == 2 and item.price[0]:
            compiled += f'Цена: {item.price[1]}{currencies[item.price[0]]}\n'
        elif item.price.__len__() == 3 and item.price[0]:
            if item.price[2]:
                compiled += f'Цена: <s>{item.price[2]}{currencies[item.price[0]]}</s> {item.price[1]}{currencies[item.price[0]]}\n'
            else:
                compiled += f'Цена: {item.price[1]}{currencies[item.price[0]]}\n'
    if item.fields:
        for k, v in item.fields.items():
            compiled += f'{k}: {v}\n'
    if item.sizes:
        compiled += 'Размеры:\n'
        for i in item.sizes:
            if isinstance(i, tuple) and i.__len__() == 2:
                compiled += f'<a href="{i[1]}">{i[0]}</a>\n'
            else:
                compiled += f'{i[0] if isinstance(i, (tuple, list)) else i}\n'
        compiled += '\n'
    if item.footer:
        footer_items: tuple = ()
        for i in item.footer:
            if i.__len__() == 2:
                footer_items += (f'<a href="{i[1]}">{i[0]}</a>',)
        compiled += ' | '.join(footer_items)
    return compiled
