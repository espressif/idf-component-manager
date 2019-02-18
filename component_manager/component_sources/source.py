from .errors import SourceError
from .local import LocalSource
from .service import ServiceSource

KNOWN_SOURCES = [LocalSource, ServiceSource]


class Source(object):
    def __init__(self, source_name, details):
        self._source_name = source_name
        self._details = details


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

        raise SourceError("Unknown source for component: %s" % self.name)
