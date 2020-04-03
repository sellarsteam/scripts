import urllib.parse
from datetime import datetime
from typing import List

import pytz

from core.api import Result

currencies: tuple = ('£', '$', '€', '₽', '¥', 'kr', '₴', 'Br', 'zł')
sizes_column_size = 5


def build(item: Result) -> dict:
    embed = {
        'author': {
            'name': '{0.scheme}://{0.netloc}/'.format(urllib.parse.urlparse(item.url)),
            'url': item.url
        },
        'footer': {
            'text': 'Sellars Monitor',
            'icon_url': 'https://www.gravatar.com/avatar/6ad5eb9719955fc8ff9021f50b91b9f0?d=retro'
        },
        'title': item.name,
        'timestamp': datetime.utcnow().replace(tzinfo=pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'fields': [],
        'url': item.url
    }

    if item.description:
        embed['description'] = item.description
    if item.image:
        embed['thumbnail'] = {'url': item.image}
    if item.price and 2 <= item.price.__len__() <= 3:
        embed['fields'].append({
            'name': 'Цена',
            'value': f'{item.price[1]}{currencies[item.price[0]]}' if
            item.price.__len__() == 2 or item.price.__len__() == 3 and item.price[2] == 0 else
            f'~~{item.price[2]}~~ {item.price[1]}{currencies[item.price[0]]}'
        })
    if item.fields:
        for k, v in item.fields.items():
            if isinstance(k, str) and isinstance(v, (str, int, float)):
                embed['fields'].append({
                    'name': k,
                    'value': v
                })
    if item.sizes:
        sizes: List[str] = []
        for i, v in enumerate(item.sizes):
            if sizes.__len__() < (i // sizes_column_size) + 1:
                sizes.append('')
            if isinstance(v, (tuple, list)) and v.__len__() == 2:
                sizes[i // sizes_column_size] += f'[{v[0]}]({v[1]})\n'
            elif isinstance(v, str):
                sizes[i // sizes_column_size] += f'{v}\n'
        embed['fields'].append({
            'name': 'Размеры',
            'value': sizes[0],
            'inline': True
        })
        for i in sizes[1:]:
            embed['fields'].append({
                'name': '\u200e',
                'value': i,
                'inline': True
            })
    if item.footer:
        footer_items: tuple = ()
        for i in item.footer:
            if i.__len__() == 2:
                footer_items += (f'[{i[0]}]({i[1]})',)
        embed['fields'].append({
            'name': 'Ссылки',
            'value': ' | '.join(footer_items)
        })
    return embed
