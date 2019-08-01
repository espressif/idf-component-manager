"""Classes to work with component sources"""

from .errors import SourceError
from .idf import IDFSource
from .local import LocalSource
from .web_service import WebServiceSource

KNOWN_SOURCES = [IDFSource, LocalSource, WebServiceSource]


class SourceBuilder(object):
    def __init__(self, name, details):
        self.details = details
        self.name = name

    def build(self):
        for source_class in KNOWN_SOURCES:
            source = source_class.build_if_me(self.name, self.details)

            if source:
                return source
            else:
                continue

        raise SourceError('Unknown source for component: %s' % self.name)
