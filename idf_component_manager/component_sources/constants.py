from .git import GitSource
from .idf import IDFSource
from .local import LocalSource
from .web_service import WebServiceSource

KNOWN_SOURCES = [IDFSource, GitSource, LocalSource, WebServiceSource]
