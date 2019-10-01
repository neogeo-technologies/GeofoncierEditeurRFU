# sgmdxfparser - copyright (C) 2017, Etienne MORO 
# and copyright (C) 2012, Manfred Moitzi (mozman)
# Purpose: handle default chunk
# Created: 2012-07-21
# Updated: 2017-02-06
# License: MIT License

from __future__ import unicode_literals
__author__ = "emoro - mozman"

from .tags import Tags, DXFTag


class DefaultChunk(object):
    def __init__(self, tags):
        assert isinstance(tags, Tags)
        self.tags = tags

    @staticmethod
    def from_tags(tags, drawing):
        return DefaultChunk(tags)

    @property
    def name(self):
        return self.tags[1].value.lower()


def iterchunks(tagreader, stoptag='EOF', endofchunk='ENDSEC'):
    while True:
        tag = next(tagreader)
        if tag == DXFTag(0, stoptag):
            return

        tags = Tags([tag])
        append = tags.append
        end_tag = DXFTag(0, endofchunk)
        while tag != end_tag:
            tag = next(tagreader)
            append(tag)
        yield tags
