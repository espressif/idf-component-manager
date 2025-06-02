# SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import sys
import typing as t
import warnings
from functools import total_ordering
from string import Template

from pydantic import (
    AfterValidator,
    AliasChoices,
    BeforeValidator,
    ConfigDict,
    Field,
    FileUrl,
    GetCoreSchemaHandler,
    HttpUrl,
    PrivateAttr,
    TypeAdapter,
    ValidationError,
    model_validator,
)
from pydantic import BaseModel as _BaseModel
from pydantic_core import CoreSchema, ErrorDetails, PydanticCustomError, core_schema

from . import debug
from .build_system_tools import get_env_idf_target
from .constants import COMPILED_COMMIT_ID_RE
from .errors import ManifestError, RunningEnvironmentError
from .hash_tools.calculate import hash_object
from .manager import ManifestManager
from .semver import Version

if t.TYPE_CHECKING:
    from idf_component_tools.manifest import ComponentRequirement, Manifest

if sys.version_info < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Any, Literal  # noqa

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated  # noqa

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self  # noqa

if sys.version_info < (3, 11):
    from typing_extensions import NotRequired
else:
    from typing import NotRequired  # noqa

if sys.version_info < (3, 12):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict  # noqa

###############################################################
# pydantic models, union discriminators, and helper functions #
###############################################################
# pydantic HttpUrl and FileUrl are not string
# so we need to convert them to string
_http_url_adapter = TypeAdapter(HttpUrl)
UrlField = Annotated[
    # return with trailing slash
    str, BeforeValidator(lambda value: str(_http_url_adapter.validate_python(value)))
]

_file_url_adapter = TypeAdapter(FileUrl)
UrlOrFileField = t.Union[
    Annotated[str, BeforeValidator(lambda value: str(_http_url_adapter.validate_python(value)))],
    Annotated[str, BeforeValidator(lambda value: str(_file_url_adapter.validate_python(value)))],
]


def _validate_unique_list_of_str(v: t.List[str]) -> t.List[str]:
    _known_values = set()
    for _v in v:
        _v = _v.lower()  # case insensitive
        if _v in _known_values:
            raise PydanticCustomError(
                'unique_list', f'List must be unique. Duplicate value: "{_v}"'
            )
        _known_values.add(_v)

    return v


UniqueStrListField = Annotated[
    t.List[str],
    AfterValidator(_validate_unique_list_of_str),
    Field(json_schema_extra={'uniqueItems': True}),
]
UniqueTagListField = Annotated[
    t.List[Annotated[str, Field(pattern=r'^[A-Za-z0-9\_\-]{3,32}$')]],
    AfterValidator(_validate_unique_list_of_str),
    Field(json_schema_extra={'uniqueItems': True}),
]

STR_MARKER = '__str__'
DICT_MARKER = '__dict__'
BOOL_MARKER = '__bool__'
DEFAULT_MARKER = '__default__'
NONE_MARKER = '__none__'
LIST_MARKER = '__list__'

ALL_MARKERS = [STR_MARKER, DICT_MARKER, BOOL_MARKER, DEFAULT_MARKER, NONE_MARKER, LIST_MARKER]


def str_dict_discriminator(v: t.Any) -> t.Optional[str]:
    if isinstance(v, str):
        return STR_MARKER

    if isinstance(v, dict):
        return DICT_MARKER

    return None


def bool_str_discriminator(v: t.Any) -> t.Optional[str]:
    if isinstance(v, str):
        return STR_MARKER

    if isinstance(v, bool):
        return BOOL_MARKER

    return None


def default_or_str_or_none_discriminator(v: t.Any) -> t.Optional[str]:
    if v is None:
        return NONE_MARKER

    if isinstance(v, str):
        if v == 'default':
            return DEFAULT_MARKER

        return STR_MARKER

    return None


def default_or_str_or_list_or_none_discriminator(v: t.Any) -> t.Optional[str]:
    if v is None:
        return NONE_MARKER

    if isinstance(v, str):
        if v == 'default':
            return DEFAULT_MARKER

        return STR_MARKER

    if isinstance(v, list):
        return LIST_MARKER

    return None


def str_or_list_or_none_discriminator(v: t.Any) -> t.Optional[str]:
    if v is None:
        return NONE_MARKER

    if isinstance(v, str):
        return STR_MARKER

    if isinstance(v, list):
        return LIST_MARKER

    return None


class BaseModel(_BaseModel):
    """
    Some general notes about pydantic models

    - Optional[str] DOES NOT mean this field is not required. It means that the field can be None.
    - str = None means that this field is not required, but if it is present, it must be a string.
    - sequence matters,
        the order of fields in the model is the order in which they will be serialized.
    - On each field, only the first validation error is raised.
    """

    FIELD_NAME: t.ClassVar[str] = ''
    ALLOW_EXTRA_FIELDS: t.ClassVar[bool] = True

    _manifest_manager: t.Optional[ManifestManager] = PrivateAttr(None)

    model_config = ConfigDict(
        str_min_length=1,
        validate_assignment=True,  # validate when assigning values to fields
    )

    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)

        self._manifest_manager = kwargs.pop('manifest_manager', None)

    def __hash__(self) -> int:
        return hash(hash_object(self.serialize()))

    @classmethod
    def fromdict(cls, d: t.Dict[str, t.Any]) -> Self:
        return cls.model_validate(dict_drop_none(d))

    def serialize(self) -> t.Dict[str, t.Any]:
        return self.model_dump()

    def model_dump(
        self,
        **kwargs,
    ) -> t.Dict[str, t.Any]:
        # default to True unless explicitly set
        exclude_none = kwargs.pop('exclude_none', True)
        by_alias = kwargs.pop('by_alias', True)

        return super().model_dump(
            exclude_none=exclude_none,
            by_alias=by_alias,
            **kwargs,
        )

    @model_validator(mode='before')
    def warn_unknown_fields(cls, v):
        if not isinstance(v, dict):
            return v

        known_keys: t.Set[str] = set()
        for _k, _v in cls.model_fields.items():
            known_keys.add(_k)
            if _v.alias:
                known_keys.add(_v.alias)
            if _v.validation_alias:
                if isinstance(_v.validation_alias, str):
                    known_keys.add(_v.validation_alias)
                elif isinstance(_v.validation_alias, AliasChoices):
                    for _alias in _v.validation_alias.choices:
                        known_keys.add(_alias)

        for _k, _v in cls.__private_attributes__.items():
            known_keys.add(_k.lstrip('_'))  # remove the leading underscore

        unknown_fields = sorted(set(v.keys()) - known_keys)
        if not unknown_fields:
            return v

        if cls.ALLOW_EXTRA_FIELDS:
            for k in unknown_fields:
                debug(f'Dropping unknown key: {k}={v.pop(k)}')

            return v

        raise ValueError(
            f'Unknown fields "{",".join(unknown_fields)}" '
            f'under "{cls.FIELD_NAME or cls.__name__.lower()}" field '
            f'that may affect build result'
        )


def dict_drop_none(d: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
    return {k: v for k, v in d.items() if v is not None}


class ComponentVersion(str):
    """
    Represents the version of a component
    """

    def __init__(self, version_string: str):
        """
        Args:
            version_string: can be `*`, git commit hash (hex, 160 bit),
                or valid semantic version string
        """
        self._version_string: str = version_string.strip().lower()
        self._semver: t.Optional[Version] = None

        # Setting flags:
        self.is_commit_id = bool(COMPILED_COMMIT_ID_RE.match(self._version_string))
        self.is_any = self._version_string == '*'
        self.is_semver = False

        # Checking format
        if not (self.is_any or self.is_commit_id):
            self._semver = Version(self._version_string)
            self.is_semver = True
            self._version_string = str(self._semver)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            other = ComponentVersion(other)
        elif not isinstance(other, ComponentVersion):
            return NotImplemented

        if self.is_semver and other.is_semver:
            return self._semver == other._semver
        else:
            return str(self) == str(other)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, str):
            other = ComponentVersion(other)
        elif not isinstance(other, ComponentVersion):
            return NotImplemented

        if not (self.is_semver and other.is_semver):
            return False  # must be exactly equal for not semver versions (e.g. commit id version)

        return self._semver < other._semver  # type: ignore

    def __gt__(self, other: object) -> bool:
        if isinstance(other, str):
            other = ComponentVersion(other)
        elif not isinstance(other, ComponentVersion):
            return NotImplemented

        if not (self.is_semver and other.is_semver):
            return False  # must be exactly equal for not semver versions (e.g. commit id version)

        return self._semver > other._semver  # type: ignore

    def __repr__(self):
        return 'ComponentVersion("{}")'.format(self._version_string)

    def __str__(self):
        return self._version_string

    @property
    def semver(self):  # type: () -> Version
        if self.is_semver and self._semver:
            return self._semver
        else:
            raise TypeError('Version is not semantic')

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: t.Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.str_schema(min_length=1)


@total_ordering
class HashedComponentVersion:
    def __init__(
        self,
        version_string: str,
        component_hash: t.Optional[str] = None,
        dependencies: t.List['ComponentRequirement'] = None,  # type: ignore
        targets: t.List[str] = None,  # type: ignore
        all_build_keys_known: bool = True,
    ) -> None:
        self.version = ComponentVersion(version_string)
        self.component_hash = component_hash
        self.dependencies = dependencies or []
        self.targets = targets or []
        self.all_build_keys_known = all_build_keys_known

    def __str__(self):
        return str(self.version)

    def __hash__(self):
        return hash(self.component_hash) if self.component_hash else hash(str(self))

    @staticmethod
    def _other_to_component_version(other):
        if isinstance(other, str):
            other = ComponentVersion(other)

        if isinstance(other, ComponentVersion):
            other_version = other
        elif isinstance(other, HashedComponentVersion):
            other_version = other.version
        else:
            return NotImplemented

        return other_version

    def __eq__(self, other: object) -> bool:
        return self.version == self._other_to_component_version(other)

    def __lt__(self, other: object) -> bool:
        return self.version < self._other_to_component_version(other)

    def __gt__(self, other: object) -> bool:
        return self.version > self._other_to_component_version(other)

    @property
    def text(self):
        return str(self)

    @property
    def semver(self):  # type: () -> Version
        if self.version.is_semver and self.version._semver:
            return self.version._semver
        else:
            raise TypeError('Version is not semantic')


class ComponentWithVersions:
    def __init__(self, name: str, versions: t.List[HashedComponentVersion]) -> None:
        self.versions = versions
        self.name = name.lower()

    def merge(self, cmp_with_versions: 'ComponentWithVersions') -> None:
        if self.name != cmp_with_versions.name:
            raise ValueError('Cannot merge different components')

        versions = self.versions.copy()
        for version in cmp_with_versions.versions:
            if version not in versions:
                versions.append(version)

        self.versions = sorted(versions)


class ProjectRequirements:
    """Representation of all manifests required by project"""

    def __init__(self, manifests: t.List['Manifest']) -> None:
        self.manifests = manifests

        self._manifest_hash = None  # type: str | None
        self._target = None  # type: str | None

    @property
    def target(self):  # type: () -> str
        if not self._target:
            self._target = get_env_idf_target()
        return self._target

    @property
    def manifest_hash(self):  # type: () -> str
        """Lazily calculate requirements hash"""
        if self._manifest_hash:
            return self._manifest_hash

        manifest_hashes = [manifest.manifest_hash for manifest in self.manifests]
        self._manifest_hash = hash_object(manifest_hashes)
        return self._manifest_hash

    @property
    def direct_dep_names(self) -> t.List[str]:
        return sorted(set(dep.name for manifest in self.manifests for dep in manifest.requirements))


def validation_error_to_str(error: ErrorDetails) -> str:
    """
    the original dict looks like
    - 'type': <correct type>
    - 'loc': (<field_name>, ... )
    - 'msg': <error message>
    - 'input': <input value>

    let's put the `input` field in the custom error message
    """
    msg = error['msg']
    loc = error['loc']

    # custom errors, remove the ValueError prefix
    eliminate_prefix = 'Value error, '
    if msg.startswith(eliminate_prefix):
        msg = msg[len(eliminate_prefix) :]

    fields: t.List[str] = []
    for _l in loc:
        if isinstance(_l, str):
            # these are just markers
            if _l in ALL_MARKERS:
                continue
            # lambdas...
            if 'lambda' in _l:
                continue
            fields.append(_l)
        elif isinstance(_l, int):
            fields.append(f'[{_l}]')  # index

    if not fields:
        if 'Invalid field ' not in msg:
            warnings.warn(
                f'Incomplete error message: {msg}. Please report this issue to the developers.'
            )
        field_msg = ''
    elif 'Invalid field ' not in msg:
        # better error message for custom errors
        field_msg = f'Invalid field "{":".join(fields)}": '
    else:
        field_msg = ''

    return field_msg + msg


def polish_validation_error(err: ValidationError):
    error_msgs = []
    for e in err.errors(include_url=False):
        new_msg = validation_error_to_str(e)
        if new_msg not in error_msgs:
            error_msgs.append(new_msg)

    return '\n'.join(error_msgs)


def subst_vars_in_str(s: str, env: t.Dict[str, t.Any] = None) -> str:  # type: ignore
    if env is None:
        env = os.environ

    try:
        return Template(s).substitute(env)
    except KeyError as e:
        raise RunningEnvironmentError(f'Environment variable "{e.args[0]}" is not set')
    except ValueError:
        raise ManifestError(
            'Invalid format of environment variable in the value: "{}".\n'
            'Note: you can use "$$" to escape the "$" character'.format(s)
        )
