# sgmdxfparser - copyright (C) 2017, Etienne MORO 
# and copyright (C) 2012, Manfred Moitzi (mozman)
# Purpose: blocks section
# Created: 2012-08-09
# Updated: 2017-02-06
# License: MIT-License

from __future__ import unicode_literals
__author__ = "emoro - mozman"

from itertools import islice

from .tags import TagGroups
from .entitysection import build_entities


class BlocksSection(object):
    name = 'blocks'

    def __init__(self):
        self._blocks = dict()

    @staticmethod
    def from_tags(tags, drawing):
        blocks_section = BlocksSection()
        if drawing.grab_blocks:
            blocks_section._build(tags)
        return blocks_section

    def _build(self, tags):
        if len(tags) == 3:  # empty block section
            return
        groups = list()
        for group in TagGroups(islice(tags, 2, len(tags)-1)):
            groups.append(group)
            if group[0].value == 'ENDBLK':
                entities = build_entities(groups)
                block = entities[0]
                block.set_entities(entities[1:-1])
                self._add(block)
                groups = list()

    def _add(self, block):
        self._blocks[block.name] = block

    # start of public interface
    def __len__(self):
        return len(self._blocks)

    def __iter__(self):
        return iter(self._blocks.values())

    def __contains__(self, name):
        return name in self._blocks

    def __getitem__(self, name):
        return self._blocks[name]

    def get(self, name, default=None):
        return self._blocks.get(name, default)
