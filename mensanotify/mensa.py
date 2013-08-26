# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import re

from collections import defaultdict, namedtuple
from urllib import urlencode
from lxml import etree
from itertools import chain
from datetime import datetime
import json

from mensanotify import app
import mensanotify.date

Mensa = namedtuple('Mensa', ['char', 'name'])

MENSAE = [
    Mensa('z', 'Zentralmensa'),
    Mensa('t', 'Mensa am Turm'),
    Mensa('n', 'Nordmensa'),
    Mensa('i', 'Mensa Italia'),
    Mensa('h', 'Bistro HAWK'),
    ]
MENSA_CHARS = [m.char for m in MENSAE]
MENSA_NAMES = [m.name for m in MENSAE]


def _blacklisted(text):
    if not text:
        return True

    if u'vorlesungsfrei' in text:
        return True

    bl = [
        u'Im täglichen Wechsel:',
        u'Außerdem bieten wir Ihnen ein Salatbuffet in Selbstbedienung',
        u'Verschiedene Salat- und Nudelvariationen, in Selbstbedienung!',
        ]

    if text in bl:
        return True

    return False


def fetch_week(mensa, next_week=False):
    base = 'http://www.studentenwerk-goettingen.de/speiseplan.html?'
    params = {
        'no_cache': 1,
        'selectmensa': mensa,
        'day': 7,
        'push': int(next_week),
        }

    uri = base + urlencode(params)

    parser = etree.HTMLParser(encoding='utf-8', no_network=False)
    tree = etree.parse(uri, parser)
    for head in tree.xpath("//div[@class='speise-tblhead']"):
        menu = []
        date = mensanotify.date.from_string(head.text,
                                            '%A, %d. %B %Y',
                                            'de_DE')
        table = head.getnext()
        for row in table.iterchildren():
            ch = row.getchildren()
            ch = [x.getchildren() for x in row.getchildren()]
            ch = [x[0] for x in ch if x][:2]
            if (len(ch) != 2):
                continue
            cat, item = ch

            cat = unicode(cat.text)

            item, = item.xpath(".//strong")
            if not item.text:
                continue
            name = unicode(item.text)
            desc = unicode(item.tail.strip())

            #cat = cat.attrib['title']

            if not _blacklisted(name):
                menu.append({
                    'cat': cat,
                    'name': name,
                    'desc': desc,
                    })

        if menu:
            yield (date, menu)


def fetch_weeks(mensa):
    return chain(fetch_week(mensa, False), fetch_week(mensa, True))


class Data(object):
    def __init__(self, path):
        self.path = path
        if os.path.isfile(self.path):
            self._load()
        else:
            self.update()

    def _load(self):
        with open(self.path) as f:
            self._data = json.load(f)
        self.mtime = os.stat(self.path).st_mtime

    def __call__(self):
        if self.mtime != os.stat(self.path).st_mtime:
            self._load()
        return self._data

    def update(self):
        self._data = {m: dict(fetch_weeks(m)) for m in MENSA_NAMES}
        with open(self.path, 'w') as f:
            json.dump(self._data, f)
        self.mtime = os.stat(self.path).st_mtime


data = Data(os.path.join(app.config['DATA_ROOT'], 'mensa_data.json'))


def overview(mensae=MENSA_NAMES):
    d = data()
    return {m: d[m] for m in mensae if d[m]}


def search_many(queries, mensae=MENSA_NAMES):
    data = overview(mensae)
    if not queries:
        return data

    result = {}
    for mensa, week in data.items():
        found = defaultdict(list)
        for day, menu in week.items():
            for item in menu:
                s = (item['name'] + item['desc']).lower()
                for q in queries:
                    reg = re.compile(q, flags=re.IGNORECASE | re.UNICODE)
                    if q.lower() in s or reg.search(s):
                            found[day].append(item)
        if found:
            result[mensa] = dict(found)
    return result


def search(query, mensae=MENSA_NAMES):
    return search_many([query], mensae)
