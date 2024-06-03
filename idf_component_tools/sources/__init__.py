# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t

from pydantic import Field

from idf_component_tools.utils import BaseModel

from .base import BaseSource
from .git import GitSource
from .idf import IDFSource
from .local import LocalSource
from .web_service import WebServiceSource

if t.TYPE_CHECKING:
    from idf_component_tools.manager import ManifestManager

KNOWN_SOURCES: t.List[t.Type[BaseSource]] = [
    IDFSource,
    GitSource,
    LocalSource,
    WebServiceSource,
]


class Source(BaseModel):
    source: t.Union[BaseSource, GitSource, IDFSource, LocalSource, WebServiceSource] = Field(
        discriminator='type'
    )

    @classmethod
    def from_dependency(
        cls,
        name: str,  # actually `type`...
        path: t.Optional[str] = None,
        git: t.Optional[str] = None,
        registry_url: t.Optional[str] = None,
        override_path: t.Optional[str] = None,
        pre_release: bool = None,  # type: ignore # None as unset by default
        manifest_manager: t.Optional['ManifestManager'] = None,
    ) -> BaseSource:
        d: t.Dict[str, t.Any] = {'manifest_manager': manifest_manager}

        if name == 'idf':
            return IDFSource.fromdict(d)
        elif git:
            d.update({'git': git, 'path': path})
            return GitSource.fromdict(d)
        elif path or override_path:
            d.update({'path': path, 'override_path': override_path})
            return LocalSource.fromdict(d)

        d.update({'registry_url': registry_url, 'pre_release': pre_release})
        return WebServiceSource.fromdict(d)

    @classmethod
    def from_dict(
        cls,
        d: t.Dict[str, t.Any],
    ) -> t.Union[BaseSource, GitSource, IDFSource, LocalSource, WebServiceSource]:
        return cls.model_validate({'source': d}).source


__all__ = [
    'Source',
    'BaseSource',
    'WebServiceSource',
    'LocalSource',
    'IDFSource',
    'GitSource',
    'KNOWN_SOURCES',
]
