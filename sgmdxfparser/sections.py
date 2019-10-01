# sgmdxfparser - copyright (C) 2017, Etienne MORO 
# and copyright (C) 2012, Manfred Moitzi (mozman)
# Purpose: handle dxf sections
# Created: 2012-07-21
# Updated: 2017-02-06
# License: MIT License

from __future__ import unicode_literals
__author__ = "emoro - mozman"

from .codepage import toencoding
from .defaultchunk import DefaultChunk, iterchunks
from .headersection import HeaderSection
from .tablessection import TablesSection
from .entitysection import EntitySection, ObjectsSection
from .blockssection import BlocksSection
from .acdsdata import AcDsDataSection


class Sections(object):
    def __init__(self, tagreader, drawing):
        self._sections = {}
        self._create_default_sections()
        self._setup_sections(tagreader, drawing)

    def __contains__(self, name):
        return name in self._sections

    def _create_default_sections(self):
        self._sections['header'] = HeaderSection()
        for cls in SECTIONMAP.values():
            section = cls()
            self._sections[section.name] = section

    def _setup_sections(self, tagreader, drawing):
        def name(section):
            return section[1].value

        bootstrap = True
        for section in iterchunks(tagreader, stoptag='EOF', endofchunk='ENDSEC'):
            if bootstrap:
                new_section = HeaderSection.from_tags(section)
                drawing.dxfversion = new_section.get('$ACADVER', 'AC1009')
                codepage = new_section.get('$DWGCODEPAGE', 'ANSI_1252')
                drawing.encoding = toencoding(codepage)
                bootstrap = False
            else:
                section_name = name(section)
                if section_name in SECTIONMAP:
                    section_class = get_section_class(section_name)
                    new_section = section_class.from_tags(section, drawing)
                else:
                    new_section = None
            if new_section is not None:
                self._sections[new_section.name] = new_section

    def __getattr__(self, key):
        try:
            return self._sections[key]
        except KeyError:
            raise AttributeError(key)

SECTIONMAP = {
    'TABLES': TablesSection,
    'ENTITIES': EntitySection,
    'OBJECTS': ObjectsSection,
    'BLOCKS': BlocksSection,
    'ACDSDATA': AcDsDataSection,
}


def get_section_class(name):
    return SECTIONMAP.get(name, DefaultChunk)
