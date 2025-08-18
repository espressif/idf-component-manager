# SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""
This module contains utility functions for working with environment variables.
"""

import os
import typing as t
import warnings
from functools import lru_cache

from pydantic import AliasChoices, Field, computed_field, create_model, field_validator
from pydantic_core.core_schema import ValidationInfo, ValidatorFunctionWrapHandler
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from idf_component_manager.version_solver.mixology.range import Range
from idf_component_manager.version_solver.mixology.union import Union
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
    Component Manager settings.

    .. warning::

        For environment variable aliases, the first alias is the recommended one.
        Any other listed aliases are also supported, but deprecated and will raise a
        ``UserDeprecationWarning`` if they are set in the environment.
        They may be removed in the future.
    """

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_prefix='IDF_COMPONENT_',
    )

    # LOGGING

    # by default log-level is hint(15)
    DEBUG_MODE: bool = Field(False, description='Enable debug mode.')  # log-level: debug(10)

    NO_HINTS: bool = Field(
        False, description='Disable hints in the output.'
    )  # log-level: notice/info(20)

    NO_COLORS: bool = Field(False, description='Disable colored output.')  # with colorama or not

    # GENERAL

    CACHE_PATH: t.Optional[str] = Field(
        None,
        description="""
            | Cache directory for Component Manager.
            | **Default:** Depends on OS
        """,
    )

    KNOWN_TARGETS: t.Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            'IDF_COMPONENT_KNOWN_TARGETS',
            'IDF_COMPONENT_MANAGER_KNOWN_TARGETS',
        ),
        description="""
            Targets that are known to the Component Manager.

            Aliases:

            - ``IDF_COMPONENT_KNOWN_TARGETS``
            - ``IDF_COMPONENT_MANAGER_KNOWN_TARGETS`` (**deprecated**)
        """,
    )

    # NETWORK

    VERSION_PROCESS_TIMEOUT: int = Field(
        default=300,
        validation_alias=AliasChoices(
            'IDF_COMPONENT_VERSION_PROCESS_TIMEOUT', 'COMPONENT_MANAGER_JOB_TIMEOUT'
        ),
        description="""
            Timeout for processing version jobs in seconds.

            Aliases:

            - ``IDF_COMPONENT_VERSION_PROCESS_TIMEOUT``
            - ``COMPONENT_MANAGER_JOB_TIMEOUT`` (**deprecated**)
        """,
    )

    API_TIMEOUT: t.Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices(
            'IDF_COMPONENT_API_TIMEOUT',
            'IDF_COMPONENT_SERVICE_TIMEOUT',
        ),
        description="""
            | Timeout for API requests to the Component Registry in seconds.
            | If not set, the default timeout of the HTTP client will be used.

            Aliases:

            - ``IDF_COMPONENT_API_TIMEOUT``
            - ``IDF_COMPONENT_SERVICE_TIMEOUT`` (**deprecated**)
        """,
    )

    API_TOKEN: t.Optional[str] = Field(
        None, description='API token to access the Component Registry.'
    )

    VERIFY_SSL: t.Union[bool, str] = Field(
        True,
        description="""
            | Verify SSL certificates when making requests to the Component Registry.
            | Set 0 to disable or provide a CA bundle path.
        """,
    )

    CACHE_HTTP_REQUESTS: bool = Field(
        True,
        description="""
            | Cache HTTP requests to the Component Registry during runtime.
            | Set 0 to disable.
        """,
    )

    PROFILE: t.Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            'IDF_COMPONENT_PROFILE',
            'IDF_COMPONENT_REGISTRY_PROFILE',
            'IDF_COMPONENT_SERVICE_PROFILE',
        ),
        description="""
            | Profile in the config file to use.
            | **Default:** default

            Aliases:

            - ``IDF_COMPONENT_PROFILE``
            - ``IDF_COMPONENT_REGISTRY_PROFILE`` (**deprecated**)
            - ``IDF_COMPONENT_SERVICE_PROFILE`` (**deprecated**)
        """,
    )

    REGISTRY_URL: t.Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            'IDF_COMPONENT_REGISTRY_URL',
            'DEFAULT_COMPONENT_SERVICE_URL',
        ),
        description="""
            | URL of the default Component Registry.
            | **Default:** https://components.espressif.com/

            Aliases:

            - ``IDF_COMPONENT_REGISTRY_URL``
            - ``DEFAULT_COMPONENT_SERVICE_URL`` (**deprecated**)
        """,
    )

    STORAGE_URL: t.Optional[str] = Field(
        None,
        description="""
            | URL of the file storage server.
            | To set multiple URLs, use semicolon (;) to separate them:
            | `<url1>;<url2>;...`
            | **Default:** https://components-file.espressif.com/
        """,
    )

    LOCAL_STORAGE_URL: t.Optional[str] = Field(
        None,
        description="""
            | URL of the mirror.
            | To set multiple URLs, use semicolon (;) to separate them:
            | `<url1>;<url2>;...`
        """,
    )

    # MANAGED COMPONENTS

    OVERWRITE_MANAGED_COMPONENTS: bool = Field(
        False,
        description="""
            | Overwrite files in the ``managed_components`` directory,
            | even if they have been modified by the user.
        """,
    )

    SUPPRESS_UNKNOWN_FILE_WARNINGS: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            'IDF_COMPONENT_SUPPRESS_UNKNOWN_FILE_WARNINGS',
            'IGNORE_UNKNOWN_FILES_FOR_MANAGED_COMPONENTS',
        ),
        description="""
            Ignore unknown files in ``managed_components`` directory.

            Aliases:

            - ``IDF_COMPONENT_SUPPRESS_UNKNOWN_FILE_WARNINGS``
            - ``IGNORE_UNKNOWN_FILES_FOR_MANAGED_COMPONENTS`` (**deprecated**)
        """,
    )

    # if true, calculate by hash_dir() instead of checking the .component_hash file
    STRICT_CHECKSUM: bool = Field(
        False,
        description="""
            | Validate checksums strictly.
            | If set to 1, checksum of each file will be compared to the expected value.
        """,
    )

    # version solver
    CHECK_NEW_VERSION: bool = Field(True, description='Check for new versions of components.')

    CONSTRAINT_FILES: t.Optional[str] = Field(
        None,
        description="""
            | Constraint files for component version solving.
            | To specify multiple files, use semicolons to separate them:
            | `/path/to/file1;/path/to/file2,...`
        """,
    )

    CONSTRAINTS: t.Optional[str] = Field(
        None,
        description="""
            | Direct constraint definitions for component version solving.
            | To specify multiple constraints, use semicolons to separate them:
            | `namespace/component_name>=version;component_name>=version;...`
        """,
    )

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

    @computed_field  # type: ignore
    @property
    def constraints(self) -> t.Dict[str, t.Union[Union, Range]]:
        from idf_component_manager.version_solver.constraint_file import (
            parse_constraint_file,
            parse_constraint_string,
        )

        merged_constraints = {}

        # First, load constraints from files
        if self.CONSTRAINT_FILES:
            for fp in [path.strip() for path in self.CONSTRAINT_FILES.split(';') if path]:
                merged_constraints.update(parse_constraint_file(fp))

        # Then, load direct constraints (can override file constraints)
        if self.CONSTRAINTS:
            merged_constraints.update(parse_constraint_string(self.CONSTRAINTS))

        return merged_constraints

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


# Separate model for documentation
ComponentManagerEnvVariables = create_model(  # type: ignore
    'ComponentManagerEnvVariables',
    __doc__=ComponentManagerSettings.__doc__,
    __base__=BaseSettings,
    **{
        f'{ComponentManagerSettings.model_config.get("env_prefix")}{field_name}': (
            field_info.annotation,
            Field(field_info.default, description=field_info.description),
        )
        for (field_name, field_info) in ComponentManagerSettings.model_fields.items()
    },
)
