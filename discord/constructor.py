import urllib.parse
from datetime import datetime
from typing import List, Union

import pytz

from source.api import IAnnounce, IRelease, IRestock

currencies: tuple = ('', '£', '$', '€', '₽', '¥', 'kr', '₴', 'Br', 'zł', '$(HKD)', '$(CAD)', '$(AUD)')
sizes_column_size = 5


def build(item: Union[IAnnounce, IRelease, IRestock]) -> dict:
    embed = {
        'author': {
            'name': '{0.scheme}://{0.netloc}/'.format(urllib.parse.urlparse(item.url)),
            'url': item.url
        },
        'footer': {
            'text': 'Sellars Monitors',
            'icon_url': 'https://vk.com/doc210515946_566140005?hash=278a5eb4b63e373dfe&dl=8e1637784bef33de38'
        },
        'title': ('[ANNOUNCE] ' if isinstance(item, IAnnounce) else
                  '[RESTOCK] ' if isinstance(item, IRestock) else '') + item.name,
        "color": ('31487' if isinstance(item, IRelease) else
                  '15396079' if isinstance(item, IRestock) else '15396079'),
        'timestamp': datetime.utcnow().replace(tzinfo=pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'fields': [],
        'url': item.url
    }

    if item.description:
        embed['description'] = item.description
    if item.image:
        embed['thumbnail'] = {'url': item.image}

    if item.price.current:
        embed['fields'].append({
            'name': 'Price',
            'value': f'~~{item.price.old}~~ {item.price.current}{currencies[item.price.currency]}'
            if item.price.old else f'{item.price.current}{currencies[item.price.currency]}'
        })

    if item.fields:
        for k, v in item.fields.items():
            embed['fields'].append({
                'name': k,
                'value': v
            })

    if item.sizes:
        columns: List[str] = []
        for i, v in enumerate(item.sizes):
            if len(columns) < (i // sizes_column_size) + 1:
                columns.append('')
            if v.url:
                columns[i // sizes_column_size] += f'[{v.size}]({v.url})\n'
            else:
                columns[i // sizes_column_size] += f'{v.size}\n'

        embed['fields'].append({
            'name': 'Sizes',
            'value': columns[0],
            'inline': True
        })

        for i in columns[1:]:
            embed['fields'].append({
                'name': '\u200e',
                'value': i,
                'inline': True
            })

    if item.footer:
        embed['fields'].append({
            'name': 'Links',
            'value': ' | '.join((f'[{i.text}]({i.url})' if i.url else i.text for i in item.footer))
        })

    return embed
