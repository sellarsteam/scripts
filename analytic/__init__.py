import sqlite3
import threading

from ujson import dumps

from source import api
from source import logger
from source.tools import ScriptStorage


class EventsExecutor(api.EventsExecutor):
    db: sqlite3.Connection
    lock: threading.RLock

    def __init__(self, name: str, log: logger.Logger, storage: ScriptStorage):
        super().__init__(name, log, storage)
        self.lock = threading.RLock()

        if not self.storage.check('data.db'):
            self.storage.file('data.db', 'w+')
        self.db = sqlite3.connect(self.storage.path + '/data.db', 1, check_same_thread=False)

        self.check()

    def check(self):
        with self.lock, self.db as c:
            c.executescript('create table if not exists items (id integer primary key autoincrement,'
                            'hash blob not null unique, url text not null, channel text not null, name text not null, '
                            'image text not null, description text, price real not null, currency integer not null, '
                            'sizes text not null, publish_date real not null, timestamp real not null);'
                            'create table if not exists announces (id integer primary key autoincrement,'
                            'hash blob not null unique, url text not null, channel text not null, name text not null, '
                            'image text not null, description text, price real not null, currency integer not null, '
                            'sizes text not null, publish_date real not null, timestamp real not null);')

    def e_item(self, item: api.ItemType) -> None:
        if isinstance(item, (api.IRelease, api.IAnnounce)):
            with self.lock, self.db as c:
                try:
                    c.execute(
                        f"INSERT INTO {'items' if isinstance(item, api.IRelease) else 'announces'} "
                        f"VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        [
                            item.hash(4), item.url, item.channel, item.name, item.image, item.description,
                            item.price.current, item.price.currency, dumps(item.sizes.export()), item.publish_date,
                            item.timestamp
                        ]
                    )
                except sqlite3.IntegrityError:
                    self.log.error('Trying to insert non-unique item')
