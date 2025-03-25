# SPDX-FileCopyrightText: 2024-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t
import warnings
from contextvars import ContextVar
from copy import deepcopy

from pydantic import (
    AfterValidator,
    AliasChoices,
    Discriminator,
    Field,
    Tag,
    ValidationError,
    field_serializer,
    field_validator,
    model_serializer,
    model_validator,
)
from pydantic_core.core_schema import SerializerFunctionWrapHandler
from pyparsing import ParseException

from idf_component_tools.build_system_tools import (
    build_name,
    build_name_to_namespace_name,
)
from idf_component_tools.constants import (
    COMMIT_ID_RE,
    COMPILED_GIT_URL_RE,
    DEFAULT_NAMESPACE,
    IDF_COMPONENT_REGISTRY_URL,
)
from idf_component_tools.debugger import KCONFIG_CONTEXT
from idf_component_tools.errors import (
    InternalError,
    MetadataKeyError,
    MissingKconfigError,
    RunningEnvironmentError,
)
from idf_component_tools.hash_tools.calculate import hash_object
from idf_component_tools.logging import suppress_logging
from idf_component_tools.manager import UploadMode
from idf_component_tools.messages import debug, notice
from idf_component_tools.registry.api_models import DependencyResponse
from idf_component_tools.semver import Version
from idf_component_tools.sources import BaseSource, LocalSource, Source
from idf_component_tools.utils import (
    BOOL_MARKER,
    DICT_MARKER,
    STR_MARKER,
    Annotated,
    BaseModel,
    ComponentVersion,
    Literal,
    UniqueStrListField,
    UniqueTagListField,
    UrlField,
    bool_str_discriminator,
    polish_validation_error,
    str_dict_discriminator,
    validation_error_to_str,
)

from .constants import COMPILED_FULL_SLUG_REGEX, known_targets
from .if_parser import IfClause, parse_if_clause

# Context for model validation
_manifest_validation_context: ContextVar = ContextVar('manifest_validation_context', default={})


def set_validation_context(context: t.Dict[str, t.Any]):
    _manifest_validation_context.set(context)


def get_validation_context() -> t.Dict[str, t.Any]:
    return _manifest_validation_context.get()


class OptionalDependency(BaseModel):
    # use alias since `if` is a keyword
    if_clause: str = Field(alias='if')
    version: str = None  # type: ignore

    _if_clause_obj: IfClause = None  # type: ignore

    @field_validator('if_clause')
    @classmethod
    def validate_if_clause(cls, v: str):
        # the parse will call again later in `if_clause_obj`
        # trade off for better error messages
        try:
            obj = parse_if_clause(v)
            with suppress_logging():
                obj.get_value()
        except ParseException:
            raise ValueError('Invalid syntax: "{}"'.format(v))
        except RunningEnvironmentError as e:
            if get_validation_context().get('upload_mode') not in [
                UploadMode.example,
                UploadMode.false,
            ]:
                raise e
        except MissingKconfigError as e:
            # ignore missing kconfig
            debug(str(e))

        return v

    @property
    def if_clause_obj(self) -> IfClause:
        if self._if_clause_obj is None:
            self._if_clause_obj = parse_if_clause(self.if_clause)

        return self._if_clause_obj


class OptionalRequirement(BaseModel):
    matches: t.List[OptionalDependency] = []
    rules: t.List[OptionalDependency] = []

    def version_spec_if_meet_conditions(self, default_version_spec: str) -> t.Optional[str]:
        """
        Return version spec If
        - The first IfClause that is true among all the specified `matches`
          And
        - All the IfClauses that are true among all the specified `rules`

        :return:
            - if the optional dependency matches, return the version spec if specified,
                else return '*'
            - else, return None
        """
        if not self.matches and not self.rules:
            return default_version_spec

        res = None

        # ANY of the `matches`
        for optional_dependency in self.matches:
            if optional_dependency.if_clause_obj.get_value():
                res = optional_dependency.version or default_version_spec
                break

        # must match at least one `matches`
        if self.matches and res is None:
            return None

        # AND all the `rules`
        for optional_dependency in self.rules:
            if optional_dependency.if_clause_obj.get_value():
                res = optional_dependency.version or res or default_version_spec
            else:
                return None

        return res


class DependencyItem(BaseModel):
    FIELD_NAME: t.ClassVar[str] = 'dependencies'
    ALLOW_EXTRA_FIELDS: t.ClassVar[bool] = False

    version: str = None  # type: ignore
    public: bool = None  # type: ignore
    path: str = None  # type: ignore
    git: str = None  # type: ignore
    registry_url: str = Field(
        default=None,
        validation_alias=AliasChoices(
            'registry_url',
            'service_url',
        ),
    )  # type: ignore
    rules: t.List[OptionalDependency] = None  # type: ignore
    matches: t.List[OptionalDependency] = None  # type: ignore
    override_path: str = None  # type: ignore
    require: Annotated[
        t.Union[
            Annotated[Literal['public', 'private', 'no'], Tag(STR_MARKER)],
            Annotated[Literal[False], Tag(BOOL_MARKER)],
        ],
        Discriminator(
            bool_str_discriminator,
            custom_error_type='invalid_union_member',
            custom_error_message='Supported types for "require" field: "public,private,no,False"',
        ),
    ] = None  # type: ignore
    pre_release: bool = None  # type: ignore

    @field_validator('rules', 'matches')
    @classmethod
    def validate_optional_dependencies(cls, v: t.Optional[t.List[t.Dict[str, str]]]):
        if not v:
            return None

        # convert list of dict to list of OptionalDependency
        if not isinstance(v[0], dict):
            return v

        return [OptionalDependency.fromdict(item) for item in v]

    @property
    def version_spec(self) -> str:
        if self.optional_requirement:
            version_spec = self.optional_requirement.version_spec_if_meet_conditions(
                self.version or '*'
            )
            if version_spec is not None:
                return version_spec

        return self.version or '*'

    @property
    def optional_requirement(self) -> OptionalRequirement:
        return OptionalRequirement(
            matches=self.matches or [],
            rules=self.rules or [],
        )

    @property
    def is_public(self) -> bool:
        if self.public is not None:
            return self.public

        return self.require == 'public'

    @property
    def is_required(self) -> bool:
        if self.require in ['no', False]:
            return False

        return True


class ComponentRequirement(DependencyItem):
    name: str

    _source: t.Optional[BaseSource] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.validate_post_init()

    def __hash__(self):
        d = self.serialize()
        if self.source.type == 'service':
            if self.registry_url in [
                None,
                IDF_COMPONENT_REGISTRY_URL.rstrip('/'),
            ]:
                d['registry_url'] = IDF_COMPONENT_REGISTRY_URL
        return hash(hash_object(d))

    def validate_post_init(self) -> None:
        # validate version by source
        if not self.source.validate_version_spec(self.version):
            raise ValueError(
                f'Invalid field "dependencies:{self.name}:version": Invalid version specification "{self.version}"'
            )

        # validate version in optional dependencies
        for rule in self.optional_requirement.matches:
            if not self.source.validate_version_spec(rule.version or ''):
                raise ValueError(
                    f'Invalid field "dependencies:{self.name}:matches:{rule.if_clause}:version": '
                    f'Invalid version specification "{rule.version}"'
                )

        for rule in self.optional_requirement.rules:
            if not self.source.validate_version_spec(rule.version or ''):
                raise ValueError(
                    f'Invalid field "dependencies:{self.name}:rules:{rule.if_clause}:version": '
                    f'Invalid version specification "{rule.version}"'
                )

        # validate public/require
        if self.public is not None and self.require is not None:
            raise ValueError(
                f'Invalid field "dependencies:{self.name}: "public" and "require" fields must not set at the same time'
            )

        # name should be normalized
        self.name = self.source.normalized_name(self.name)

    @property
    def source(self) -> BaseSource:
        if self._source is None:
            self._source = Source.from_dependency(
                name=self.name,
                path=self.path,
                git=self.git,
                registry_url=self.registry_url,
                override_path=self.override_path,
                pre_release=self.pre_release,
                manifest_manager=self._manifest_manager,
            )

        return self._source

    @property
    def meta(self):
        return self.source.meta

    @property
    def build_name(self):
        """
        Name of the component with the namespace, but escaped the `/`.

        Usually used for build system, where `/` is not allowed.
        """
        return build_name(self.name)

    @property
    def short_name(self):
        """Name of the component without the namespace"""
        return self.name.rsplit('/', 1)[-1]

    @property
    def meet_optional_dependencies(self) -> bool:
        if (not self.matches) and (not self.rules):
            return True

        if self.optional_requirement.version_spec_if_meet_conditions(self.version_spec) is not None:
            return True

        notice('Skipping optional dependency: {}'.format(self.name))
        return False

    @classmethod
    def from_dependency_response(cls, dep_resp: DependencyResponse) -> 'ComponentRequirement':
        if dep_resp.source == 'idf':
            additional_kwargs = {
                'name': 'idf',
            }
        elif dep_resp.source == 'service':
            additional_kwargs = {
                'name': f'{dep_resp.namespace}/{dep_resp.name}',
                'registry_url': dep_resp.registry_url or IDF_COMPONENT_REGISTRY_URL,
            }
        else:
            raise InternalError(f'Unknown source: {dep_resp.source}')

        kwargs = {
            'version': dep_resp.spec,
            'require': 'public'
            if dep_resp.is_public
            else ('private' if dep_resp.require else 'no'),
            'matches': [OptionalDependency.fromdict(k.model_dump()) for k in dep_resp.matches],
            'rules': [OptionalDependency.fromdict(k.model_dump()) for k in dep_resp.rules],
        }

        return ComponentRequirement(
            **kwargs,
            **additional_kwargs,
        )


class FilesField(BaseModel):
    use_gitignore: bool = False
    include: UniqueStrListField = []
    exclude: UniqueStrListField = []


class RepositoryInfoField(BaseModel):
    commit_sha: Annotated[str, Field(pattern=COMMIT_ID_RE)] = None  # type: ignore
    path: str = None  # type: ignore


class ComponentLinks(BaseModel):
    repository: str = None  # type: ignore
    documentation: str = None  # type: ignore
    issues: str = None  # type: ignore
    discussion: str = None  # type: ignore
    url: str = None  # type: ignore


def _check_git_url(v: str) -> str:
    # don't touch the value
    if COMPILED_GIT_URL_RE.match(v):
        return v

    raise ValueError('Invalid git URL: {}'.format(v))


GIT_URL_FIELD = Annotated[str, AfterValidator(_check_git_url)]


class Manifest(BaseModel):
    name: str = None  # type: ignore
    version: ComponentVersion = None  # type: ignore
    targets: UniqueStrListField = []  # type: ignore
    maintainers: UniqueStrListField = None  # type: ignore
    description: str = None  # type: ignore
    license: str = None  # type: ignore
    tags: UniqueTagListField = []
    dependencies: t.Dict[
        str,
        Annotated[
            t.Union[
                Annotated[str, Tag(STR_MARKER)],
                Annotated[DependencyItem, Tag(DICT_MARKER)],
            ],
            Discriminator(
                str_dict_discriminator,
                custom_error_type='invalid_union_member',
                custom_error_message='Supported types for "dependency" field: "str,dict"',
            ),
        ],
    ] = {}  # type: ignore
    files: FilesField = None  # type: ignore
    examples: t.List[t.Dict[str, t.Any]] = None  # type: ignore
    url: UrlField = None  # type: ignore
    repository: GIT_URL_FIELD = None  # type: ignore
    documentation: UrlField = None  # type: ignore
    issues: UrlField = None  # type: ignore
    discussion: UrlField = None  # type: ignore
    repository_info: RepositoryInfoField = None  # type: ignore

    _upload_mode: UploadMode = UploadMode.false

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self._upload_mode = kwargs.pop('upload_mode', UploadMode.false)

        self.validate_post_init()

    def validate_post_init(self) -> None:
        """
        `model_post_init` will call after `super().__init__`.
        We need to initialize the private attrs first.
        """
        from .metadata import Metadata  # avoid circular import
        from .schemas import BUILD_METADATA_KEYS  # avoid circular import

        # validate source.version
        self.raw_requirements

        # validate metadata fields
        unknown_keys_errs: t.List[MetadataKeyError] = []
        for key in self.metadata.build_metadata_keys:
            if key not in BUILD_METADATA_KEYS:
                _k, _type = Metadata.get_closest_manifest_key_and_type(key)
                unknown_keys_errs.append(MetadataKeyError(_k, _type))

        if unknown_keys_errs:
            raise ValueError(unknown_keys_errs)

        # validate repository and commit sha
        if not self.repository and self.repository_info:
            raise ValueError('Invalid field "repository". Must set when "repository_info" is set')

        if self._upload_mode == UploadMode.component:
            self._validate_while_uploading()

    def model_dump(self, **kwargs) -> t.Dict[str, t.Any]:
        return super().model_dump(exclude=['name'], exclude_unset=True)

    @field_validator('version')
    @classmethod
    def validate_version(cls, v: t.Any):
        if isinstance(v, str):
            return ComponentVersion(v)

        return v

    @field_serializer('version')
    @staticmethod
    def serialize_version(version: ComponentVersion):
        return str(version)

    @field_validator('dependencies')
    @classmethod
    def validate_dependencies(cls, d: t.Dict[str, t.Any]):
        normalized_dict = {}

        error_msgs = []

        for k, v in d.items():
            if not COMPILED_FULL_SLUG_REGEX.match(k):
                error_msgs.append(f'Invalid field "dependencies:{k}": Invalid component name')
                continue

            if '__' in k:
                error_msgs.append(
                    f'Invalid field "dependencies:{k}": Component\'s name should not contain two consecutive underscores.'
                )
                continue

            # default namespace "espressif"
            if '/' not in k:
                full_name = f'{DEFAULT_NAMESPACE}/{k}'
            else:
                full_name = k

            try:
                if isinstance(v, dict):
                    normalized_dict[full_name] = DependencyItem.fromdict(v)
                else:
                    normalized_dict[full_name] = v
            except ValidationError as e:
                error_msgs.append(polish_validation_error(e))
                continue

        if error_msgs:
            raise ValueError(
                '\n'.join(error_msgs),
            )

        return d

    def _validate_while_uploading(self) -> None:
        """
        Only validate fields that are required during uploading to the registry
        """
        if not self.version:
            raise ValueError(
                'Invalid field "version". Must set while uploading component to the registry'
            )

        if not self.version.is_semver:
            raise ValueError(
                'Invalid field "version". '
                'Must follow semantic versioning while uploading component to the registry'
            )

        unknown_targets = sorted(set(self.targets) - set(known_targets()))
        if unknown_targets:
            raise ValueError(
                f'Invalid field "targets". Unknown targets: "{",".join(unknown_targets)}"'
            )

    @classmethod
    def validate_manifest(
        cls,
        obj: t.Any,
        *,
        upload_mode: UploadMode = UploadMode.false,
        return_with_object: bool = False,
        # pydantic options
        strict: t.Optional[bool] = None,
        from_attributes: t.Optional[bool] = None,
        context: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> t.Union[t.List[str], t.Tuple[t.List[str], t.Optional['Manifest']]]:
        if not isinstance(obj, dict):
            error_msgs = [
                'Invalid manifest format. Manifest should be a dictionary',
            ]
            return (error_msgs, None) if return_with_object else error_msgs

        obj['upload_mode'] = upload_mode
        try:
            with warnings.catch_warnings():
                if upload_mode != UploadMode.false:
                    warnings.filterwarnings(
                        'ignore', message='^Running in an environment without IDF.'
                    )

                res = super().model_validate(
                    obj,
                    strict=strict,
                    from_attributes=from_attributes,
                    context=context,
                )
        except ValidationError as e:
            error_msgs = [validation_error_to_str(err) for err in e.errors(include_url=False)]
            return (error_msgs, None) if return_with_object else error_msgs

        return ([], res) if return_with_object else []

    @property
    def links(self) -> ComponentLinks:
        return ComponentLinks.fromdict({
            'repository': self.repository,
            'documentation': self.documentation,
            'issues': self.issues,
            'discussion': self.discussion,
            'url': self.url,
        })

    @property
    def include_set(self) -> t.Set[str]:
        return set(self.files.include if self.files else [])

    @property
    def exclude_set(self) -> t.Set[str]:
        return set(self.files.exclude if self.files else [])

    @property
    def use_gitignore(self) -> bool:
        return self.files.use_gitignore if self.files else False

    @property
    def metadata(self):
        from .metadata import Metadata  # avoid circular import

        return Metadata.load(self.model_dump())

    @property
    def manifest_hash(self) -> str:
        return hash_object(self.model_dump_json(exclude_unset=True))

    @property
    def repository_path(self) -> t.Optional[str]:
        return self.repository_info.path if self.repository_info else None

    @property
    def raw_requirements(self) -> t.List[ComponentRequirement]:
        requirements = []

        for name, v in self.dependencies.items():
            d: t.Dict[str, t.Any]
            if isinstance(v, str):
                d = {'version': v}
            elif isinstance(v, DependencyItem):
                d = v.model_dump()
            else:
                raise InternalError('unknown type of dependency item: {}'.format(type(v)))

            if self._manifest_manager:
                d['manifest_manager'] = self._manifest_manager

            requirements.append(ComponentRequirement(name=name, **d))

        return requirements

    @property
    def requirements(self) -> t.List[ComponentRequirement]:
        kconfig_ctx = KCONFIG_CONTEXT.get()
        res = []
        for r in self.raw_requirements:
            try:
                if r.meet_optional_dependencies:
                    res.append(r)
            except MissingKconfigError as e:
                kconfig_ctx.set_missed_kconfig(str(e), r)

        return sorted(res, key=lambda x: x.name)

    @property
    def real_name(self) -> str:
        return build_name_to_namespace_name(
            self.name or (self._manifest_manager.name if self._manifest_manager else None) or ''
        )

    @property
    def path(self) -> str:
        return str(self._manifest_manager.path) if self._manifest_manager else ''


class SolvedComponent(BaseModel):
    name: str
    component_hash: t.Optional[str] = None  # type: ignore # idf is now using None
    source: BaseSource
    version: ComponentVersion
    dependencies: t.List[ComponentRequirement] = None  # type: ignore
    targets: UniqueStrListField = None  # type: ignore

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return 'SolvedComponent <{}({}) {}>'.format(self.name, self.version, self.component_hash)

    def __str__(self):
        base_str = f'{self.name} ({self.version})'

        if isinstance(self.source, LocalSource):
            base_str += f' ({self.source._path})'

        return base_str

    def model_post_init(self, __context: t.Any) -> None:
        if self.source.downloadable and not self.component_hash:
            raise ValueError('Component hash is required for source {}'.format(self.source))

    @field_serializer('name')
    def serialize_name(self, name: str) -> str:
        return self.source.normalized_name(name)

    @field_validator('version')
    @classmethod
    def validate_version(cls, v: t.Any):
        if isinstance(v, str):
            return ComponentVersion(v)

        return v

    @model_serializer(mode='wrap')
    def serialize_model(self, handler: SerializerFunctionWrapHandler) -> t.Dict[str, t.Any]:
        # serialize from flat dict to {'name': {...}}
        d = handler(self)

        # handler doesn't handle nested model correctly
        # ATTENTION!!! it's not a clean solution
        # nested model should be handled by handler
        d['source'] = self.source.model_dump()
        d['version'] = str(self.version)

        name = d.pop('name')
        return {name: d}

    @model_validator(mode='before')  # type: ignore
    def validate_model(self) -> t.Any:
        # validate it from {'name': {...}} to flat dict
        if not isinstance(self, dict):
            return self

        original_d = deepcopy(self)
        if len(self.keys()) == 1:
            d = {}
            for k, v in self.items():
                d['name'] = k
                d.update(v)

            original_d = d

        # source discriminator
        source_d = original_d.pop('source')
        original_d['source'] = Source.from_dict(source_d)

        return original_d


class SolvedManifest(BaseModel):
    direct_dependencies: UniqueStrListField = None  # type: ignore
    dependencies: t.List[SolvedComponent] = []
    manifest_hash: Annotated[str, Field(min_length=64, max_length=64)] = None  # type: ignore
    target: str = None  # type: ignore

    @field_validator('dependencies')
    @classmethod
    def validate_dependencies(cls, v):
        return sorted(v, key=lambda x: x.name)

    @model_serializer(mode='wrap')
    def serialize_model(self, handler: SerializerFunctionWrapHandler) -> t.Dict[str, t.Any]:
        d = {}
        for dep in self.dependencies:
            d.update(dep.model_dump())

        original_d = handler(self)
        original_d['dependencies'] = d
        return original_d

    @model_validator(mode='before')  # type: ignore
    def validate_model(self) -> t.Any:
        if not isinstance(self, dict):
            return self

        if ('dependencies' not in self) or (not isinstance(self['dependencies'], dict)):
            return self

        original_d = deepcopy(self)
        deps = []
        for k, v in original_d['dependencies'].items():
            if isinstance(v, dict):
                deps.append(SolvedComponent(name=k, **v))

        original_d['dependencies'] = deps
        return original_d

    @property
    def solved_components(self) -> t.Dict[str, SolvedComponent]:
        return {cmp.name: cmp for cmp in self.dependencies}

    @property
    def idf_version(self) -> t.Optional[Version]:
        if 'idf' in self.solved_components:
            return self.solved_components['idf'].version.semver

        return None
