from typing import Tuple

from core.api import Result


def build(item: Result) -> str:
    compiled: str = ''
    if item.name:
        if item.url:
            compiled += f'<a href="{item.url}"><b>{item.name}</b></a>\n'
        else:
            compiled += f'<b>{item.name}</b>\n'
    if item.description:
        compiled += f'{item.description}\n'
    if item.price:
        if isinstance(item.price, float) or isinstance(item.price, int):
            compiled += f'Цена: {item.price} руб.\n'
        elif isinstance(item.price, tuple) or isinstance(item.price, list) and item.price.__len__() == 2:
            compiled += f'Цена: <s>{item.price[1]}</s>{item.price[0]} руб.\n'
    if item.sizes and isinstance(item.sizes, tuple):
        compiled += 'Размеры:\n'
        for i in item.sizes:
            if isinstance(i, tuple) and i.__len__() == 2:
                compiled += f'<a href="{i[1]}">{i[0]:<13}</a>'
            else:
                compiled += f'{i:<13}'
        compiled += '\n'
    if item.footer and isinstance(item.footer, tuple) or isinstance(item.footer, list):
        footer_items: Tuple[str] = ()
        for i in item.footer:
            if i.__len__() == 2:
                footer_items += (f'<a href="{i[1]}">{i[0]}</a>',)
        compiled += '|'.join(footer_items)
    return compiled

