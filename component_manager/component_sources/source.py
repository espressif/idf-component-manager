from .errors import SourceError
from .local import LocalSource
from .service import ServiceSource


class SourceBuilder(object):
    KNOWN_SOURCES = [LocalSource, ServiceSource]

    def __init__(self, name, details):
        self.details = details
        self.name = name

    def build(self):
        for source_class in self.KNOWN_SOURCES:
            source = source_class.build_if_me(self.name, self.details)

            if source:
                return source
            else:
                continue

        raise SourceError("Unknown source for component: %s" % self.name)
