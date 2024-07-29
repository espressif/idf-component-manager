# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import typing as t

from pydantic import ConfigDict, Field

from idf_component_tools.utils import BaseModel


class ApiBaseModel(BaseModel):
    model_config = ConfigDict(
        str_min_length=None,  # type: ignore # overrides the parent non-empty
        extra='allow',
    )


class ErrorResponse(ApiBaseModel):
    error: str
    messages: t.Union[t.List[str], t.Dict[str, t.Any]]


class OptionalDependencyResponse(ApiBaseModel):
    if_clause: str = Field(alias='if')
    version: str = None  # type: ignore


class DependencyResponse(ApiBaseModel):
    spec: str
    source: str
    name: t.Optional[str] = None  # type: ignore
    namespace: t.Optional[str] = None  # type: ignore
    is_public: bool = False
    require: bool = False
    rules: t.List[OptionalDependencyResponse] = []
    matches: t.List[OptionalDependencyResponse] = []


class VersionResponse(ApiBaseModel):
    version: str
    component_hash: str
    url: str
    dependencies: t.List[DependencyResponse] = []
    targets: t.Optional[t.List[str]] = None


class ComponentResponse(ApiBaseModel):
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
