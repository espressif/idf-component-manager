# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t

from pydantic import BaseModel, ConfigDict, Field

from idf_component_tools.utils import Self, dict_drop_none


# use pydantic BaseModel
class ApiBaseModel(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        extra='allow',
    )

    @classmethod
    def fromdict(cls, d: t.Dict[str, t.Any]) -> Self:
        return cls.model_validate(dict_drop_none(d))

    def model_dump(self, **kwargs) -> t.Dict[str, t.Any]:  # default to True unless explicitly set
        return super().model_dump(by_alias=True)


class ErrorResponse(ApiBaseModel):
    error: str
    messages: t.Union[t.List[str], t.Dict[str, t.Any]]


class OptionalDependencyResponse(ApiBaseModel):
    if_clause: str = Field(alias='if')
    version: str = None  # type: ignore


class DependencyResponse(ApiBaseModel):
    is_public: bool = False
    matches: t.List[OptionalDependencyResponse] = []
    name: t.Optional[str] = None
    namespace: t.Optional[str] = None
    registry_url: t.Optional[str] = None
    require: bool = False
    rules: t.List[OptionalDependencyResponse] = []
    source: str
    spec: str

    @classmethod
    def fromdict(cls, d: t.Dict[str, t.Any]) -> Self:
        if 'rules' in d:
            d['rules'] = [OptionalDependencyResponse.fromdict(r) for r in d['rules']]
        if 'matches' in d:
            d['matches'] = [OptionalDependencyResponse.fromdict(m) for m in d['matches']]

        return cls.model_validate(dict_drop_none(d))


class VersionResponse(ApiBaseModel):
    build_metadata_keys: t.Optional[t.List[str]] = None
    component_hash: str
    created_at: t.Optional[str] = None
    dependencies: t.List[DependencyResponse] = []
    description: t.Optional[str] = None
    exclusion_list: t.Optional[t.List[str]] = None
    targets: t.Optional[t.List[str]] = None
    url: str
    version: str
    yanked_at: t.Optional[str] = None
    yanked_message: t.Optional[str] = None


class ComponentResponse(ApiBaseModel):
    created_at: t.Optional[str] = None
    featured: bool = False
    name: str
    namespace: str
    versions: t.List[VersionResponse] = []


class VersionUpload(ApiBaseModel):
    job_id: str


class TaskStatus(ApiBaseModel):
    id: str
    status: str
    message: t.Optional[str] = None  # type: ignore
    progress: float = None  # type: ignore
    warnings: t.List[str] = []


class ApiInformation(ApiBaseModel):
    components_base_url: str
    info: str
    status: str
    version: str

    model_config = ConfigDict(
        extra='ignore',
    )


class ApiToken(ApiBaseModel):
    id: str
    scope: str
    created_at: t.Optional[str] = None
    expires_at: t.Optional[str] = None
    description: t.Optional[str] = None
    access_token_prefix: str

    model_config = ConfigDict(
        extra='ignore',
    )
