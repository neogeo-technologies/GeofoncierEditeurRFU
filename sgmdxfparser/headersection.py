# sgmdxfparser - copyright (C) 2017, Etienne MORO 
# and copyright (C) 2012, Manfred Moitzi (mozman)
# Purpose: handle header section
# Created: 2012-07-21
# Updated: 2017-02-06
# License: MIT License

from __future__ import unicode_literals
__author__ = "emoro - mozman"

from .tags import TagGroups, DXFTag


class HeaderSection(dict):
    name = "header"

    def __init__(self):
        super(HeaderSection, self).__init__()
        self._create_default_vars()

    @staticmethod
    def from_tags(tags):
        header = HeaderSection()
        if tags[1] == DXFTag(2, 'HEADER'):  # DXF12 without a HEADER section is valid!
            header._build(tags)
        return header

    def _create_default_vars(self):
        self['$ACADVER'] = 'AC1009'
        self['$DWGCODEPAGE'] = 'ANSI_1252'

    def _build(self, tags):
        if len(tags) == 3:  # empty header section!
            return
        groups = TagGroups(tags[2:-1], split_code=9)
        for group in groups:
            self[group[0].value] = group[1].value
