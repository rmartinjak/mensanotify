# -*- coding: utf-8 -*-

import os.path
import json
import itertools
import UserDict
import weakref


class JsonObj(object):
    def __init__(self, path):
        self._path = path
        self._data = {}
        self._load()
        self._deleted = False

    def __eq__(self, other):
        return self._path == other._path

    def _load(self):
        try:
            with open(self._path) as f:
                tmp = json.load(f)
            self._data.update(tmp)
        except:
            pass

    def _store(self):
        if not self._deleted:
            with open(self._path, 'w') as f:
                json.dump(self._data, f)

    def _update(self, other):
        self._data.update(other._data)

    def __getattr__(self, name):
        return self._data[name]

    def __setattr__(self, name, value):
        if (name[0] == '_'):
            self.__dict__.update({name: value})
        else:
            self._data.update({name: value})
            self._store()

    def __repr__(self):
        return 'JsonObj({}, {})'.format(self._path, repr(self._data))

    def __html__(self):
        return "asdf"


class JsonObjDict(UserDict.DictMixin):
    def __init__(self, path='users'):
        self.path = path
        self._refs = {}

    def _obj_path(self, key):
        return os.path.join(self.path, key)

    def __getitem__(self, key):
        if not key:
            raise KeyError
        item = self._refs.get(key, lambda: None)()
        if item is not None:
            return item
        item = JsonObj(self._obj_path(key))
        self._refs[key] = weakref.ref(item)
        return item

    def __delitem__(self, key):
        item = self._refs.get(key, lambda: None)()
        if item is not None:
            item._deleted = True
        os.remove(self._obj_path(key))

    def __setitem__(self, key, value):
        item = self[key]
        item._data = value._data

    def __contains__(self, item):
        return os.path.isfile(self._obj_path(item))

    def __iter__(self):
        return iter(os.listdir(self.path))

    def keys(self):
        return list(self.iterkeys())
