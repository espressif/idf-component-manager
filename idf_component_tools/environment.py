# SPDX-FileCopyrightText: 2023-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""
This module contains utility functions for working with environment variables.
"""

import os
import typing as t
import warnings
from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_core.core_schema import ValidationInfo, ValidatorFunctionWrapHandler
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from idf_component_tools.messages import UserDeprecationWarning

KNOWN_CI_ENVIRONMENTS = {
    'GITHUB_ACTIONS': 'github-actions',
    'GITLAB_CI': 'gitlab-ci',
    'CIRCLECI': 'circle-ci',
    'TRAVIS': 'travis',
    'JENKINS_URL': 'jenkins',
    'DRONE': 'drone',
    'APPVEYOR': 'appveyor',
    'BITBUCKET_COMMIT': 'bitbucket-pipelines',
    'SEMAPHORE': 'semaphore',
    'TEAMCITY_VERSION': 'teamcity',
    'CI': 'unknown',
}


def _env_to_bool(value: str) -> bool:
    """Returns True if environment variable is set to 1, t, y, yes, true, or False otherwise"""

    return value.lower() in {'1', 't', 'true', 'y', 'yes'}


def _env_to_bool_or_string(value: str) -> t.Union[bool, str]:
    """Returns
    - True if environment variable is set to 1, t, y, yes, true,
    - False if environment variable is set to 0, f, n, no, false
    - or the string value otherwise
    """
    if value.lower() in {'1', 't', 'true', 'y', 'yes'}:
        return True
    elif value.lower() in {'0', 'f', 'false', 'n', 'no'}:
        return False
    else:
        return value


def detect_ci() -> t.Optional[str]:
    """Returns the name of CI environment if running in a CI environment"""
    for env_var, name in KNOWN_CI_ENVIRONMENTS.items():
        if os.getenv(env_var):
            return name

    return None


class ComponentManagerSettings(BaseSettings):
    """
    Settings for the component manager

    Regarding the Aliases:
    - The first one is the recommended one
    - Will raise UserDeprecationWarning if the other env vars are set in the environment
    """

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_prefix='IDF_COMPONENT_',
    )

    # logging
    # by default log-level is hint(15)
    DEBUG_MODE: bool = False  # log-level: debug(10)
    NO_HINTS: bool = False  # log-level: notice/info(20)
    NO_COLORS: bool = False  # with colorama or not

    # general
    CACHE_PATH: t.Optional[str] = None
    KNOWN_TARGETS: t.Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            'IDF_COMPONENT_KNOWN_TARGETS',
            'IDF_COMPONENT_MANAGER_KNOWN_TARGETS',
        ),
    )

    # network
    VERSION_PROCESS_TIMEOUT: int = Field(
        default=300,
        validation_alias=AliasChoices(
            'IDF_COMPONENT_VERSION_PROCESS_TIMEOUT', 'COMPONENT_MANAGER_JOB_TIMEOUT'
        ),
    )
    API_TIMEOUT: t.Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices(
            'IDF_COMPONENT_API_TIMEOUT',
            'IDF_COMPONENT_SERVICE_TIMEOUT',
        ),
    )
    API_TOKEN: t.Optional[str] = None
    VERIFY_SSL: t.Union[bool, str] = True
    CACHE_HTTP_REQUESTS: bool = True
    PROFILE: t.Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            'IDF_COMPONENT_PROFILE',
            'IDF_COMPONENT_REGISTRY_PROFILE',
            'IDF_COMPONENT_SERVICE_PROFILE',
        ),
    )
    REGISTRY_URL: t.Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            'IDF_COMPONENT_REGISTRY_URL',
            'DEFAULT_COMPONENT_SERVICE_URL',
        ),
    )
    STORAGE_URL: t.Optional[str] = None

    # managed_components
    OVERWRITE_MANAGED_COMPONENTS: bool = False
    SUPPRESS_UNKNOWN_FILE_WARNINGS: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            'IDF_COMPONENT_SUPPRESS_UNKNOWN_FILE_WARNINGS',
            'IGNORE_UNKNOWN_FILES_FOR_MANAGED_COMPONENTS',
        ),
    )
    # if true, calculate by hash_dir() instead of checking the .component_hash file
    STRICT_CHECKSUM: bool = False

    # version solver
    CHECK_NEW_VERSION: bool = True

    @field_validator('*', mode='wrap')
    @classmethod
    def fallback_to_default(
        cls, v: t.Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> t.Any:
        field = cls.model_fields.get(info.field_name)

        # deprecation warning if old env var is set in env
        # the first one is the recommended one
        if field.validation_alias:
            for alias in field.validation_alias.choices[1:]:
                if alias in os.environ:
                    warnings.warn(
                        f'{alias} environment variable is deprecated. '
                        f'Please use {field.validation_alias.choices[0]} instead.',
                        UserDeprecationWarning,
                    )

        try:
            if v is None:
                return field.default

            if field.annotation is bool:
                return _env_to_bool(v)
            elif field.annotation is t.Union[bool, str]:
                return _env_to_bool_or_string(v)
            else:
                return handler(v)
        except Exception:  # all exceptions will fall back to default
            return field.default

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: t.Type[BaseSettings],  # noqa: ARG003
        init_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        file_secret_settings: PydanticBaseSettingsSource,  # noqa: ARG003
    ) -> t.Tuple[PydanticBaseSettingsSource, ...]:
        # we only want to use the env_settings
        return (env_settings,)

    @classmethod
    @lru_cache(1)
    def known_env_vars(cls) -> t.List[str]:
        env_var_names = set()

        for name, field in ComponentManagerSettings.model_fields.items():
            if field.validation_alias:
                env_var_names.update(field.validation_alias.choices)
            else:
                prefix = ComponentManagerSettings.model_config.get('env_prefix', '')
                env_var_names.add(prefix + name)

        return sorted(env_var_names)
