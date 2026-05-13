# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

from .state import (
    RootManagedComponentRecord,
    RootManagedComponentsState,
    RootManagedComponentsStateManager,
    validate_root_manifest,
)
from .tools import (
    ROOT_MANAGED_COMPONENTS_STATE_FILENAME,
    clean_root_managed_components,
    is_root_managed_components_path,
    iter_root_managed_component_dirs,
    managed_component_path,
    prune_root_managed_components,
    remove_empty_root_managed_dirs,
    root_managed_component_path,
    root_managed_components_state_path,
)

__all__ = [
    'ROOT_MANAGED_COMPONENTS_STATE_FILENAME',
    'RootManagedComponentRecord',
    'RootManagedComponentsState',
    'RootManagedComponentsStateManager',
    'clean_root_managed_components',
    'is_root_managed_components_path',
    'iter_root_managed_component_dirs',
    'managed_component_path',
    'prune_root_managed_components',
    'remove_empty_root_managed_dirs',
    'root_managed_component_path',
    'root_managed_components_state_path',
    'validate_root_manifest',
]
