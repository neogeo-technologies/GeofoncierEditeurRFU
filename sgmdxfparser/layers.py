# sgmdxfparser - copyright (C) 2017, Etienne MORO 
# and copyright (C) 2012, Manfred Moitzi (mozman)
# Purpose: handle layers
# Created: 2012-07-21
# Updated: 2017-02-06
# License: MIT License

__author__ = "emoro - mozman"

from .tags import TagGroups
from .tags import Tags
from .color import TrueColor

LOCK = 0b00000100
FROZEN = 0b00000001


class Layer(object):
    def __init__(self, tags):
        self.name = ""
        self.color = 7
        self.true_color = None
        self.linetype = ""
        self.locked = False
        self.frozen = False
        self.on = True
        for code, value in tags.plain_tags():
            if code == 2:
                self.name = value
            elif code == 70:
                self.frozen = bool(value & FROZEN)
                self.locked = bool(value & LOCK)
            elif code == 62:
                if value < 0:
                    self.on = False
                    self.color = abs(value)
                else:
                    self.color = value
            elif code == 420:
                self.true_color = TrueColor(abs(value))
            elif code == 6:
                self.linetype = value


class Table(object):

    def __init__(self):
        self._table_entries = dict()

    # start public interface

    def get(self, name, default=KeyError):
        try:
            return self._table_entries[name]
        except KeyError:
            if default is KeyError:
                raise
            else:
                return default

    def __getitem__(self, item):
        return self.get(item)

    def __contains__(self, name):
        return name in self._table_entries

    def __iter__(self):
        return iter(self._table_entries.values())

    def __len__(self):
        return len(self._table_entries)

    def names(self):
        return sorted(self._table_entries.keys())

    # end public interface

    def entry_tags(self, tags):
        groups = TagGroups(tags)
        assert groups.get_name(0) == 'TABLE'
        assert groups.get_name(-1) == 'ENDTAB'
        for entrytags in groups[1:-1]:
            yield Tags(entrytags)


class LayerTable(Table):
    name = 'layers'

    @staticmethod
    def from_tags(tags):
        layers = LayerTable()
        for entrytags in layers.entry_tags(tags):
            layer = Layer(entrytags)
            layers._table_entries[layer.name] = layer
        return layers

