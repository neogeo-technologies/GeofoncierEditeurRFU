# sgmdxfparser - copyright (C) 2017, Etienne MORO 
# and copyright (C) 2012, Manfred Moitzi (mozman)
# Purpose: handle linetypes table
# Created: 2014-01-06
# Updated: 2017-02-06
# License: MIT License

__author__ = "emoro - mozman"

from .layers import Table


class Linetype(object):
    def __init__(self, tags):
        self.name = ""
        self.description = ""
        self.length = 0  # overall length of the pattern
        self.pattern = []  # list of floats: value>0: line, value<0: gap, value=0: dot
        for code, value in tags.plain_tags():
            if code == 2:
                self.name = value
            elif code == 3:
                self.description = value
            elif code == 40:
                self.length = value
            elif code == 49:
                self.pattern.append(value)


class LinetypeTable(Table):
    name = 'linetypes'

    @staticmethod
    def from_tags(tags):
        styles = LinetypeTable()
        for entry_tags in styles.entry_tags(tags):
            style = Linetype(entry_tags)
            styles._table_entries[style.name] = style
        return styles

