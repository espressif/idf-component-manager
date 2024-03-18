# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import typing as t
from collections import OrderedDict

from pydantic import ValidationError
from yaml import Node, SafeDumper, YAMLError, safe_load
from yaml import dump as dump_yaml

from idf_component_tools.build_system_tools import get_env_idf_target, get_idf_version
from idf_component_tools.errors import LockError, LockVersionMismatchError
from idf_component_tools.manifest import SolvedComponent, SolvedManifest
from idf_component_tools.sources import IDFSource
from idf_component_tools.utils import ComponentVersion

FORMAT_VERSION = '2.0.0'


class LockFile(SolvedManifest):
    version: str = FORMAT_VERSION


EMPTY_LOCK: t.Dict[str, t.Any] = {}


def _ordered_dict_representer(dumper: SafeDumper, data: t.OrderedDict) -> Node:
    return dumper.represent_data(dict(data))


SafeDumper.add_representer(OrderedDict, _ordered_dict_representer)


class LockManager:
    def __init__(self, path):
        self._path = path

    def exists(self):
        return os.path.isfile(self._path)

    def dump(self, solution: SolvedManifest) -> None:
        """Writes updated lockfile to disk"""
        # add idf version if not in solution.dependencies
        if 'idf' not in solution.solved_components:
            solution.dependencies.append(
                SolvedComponent(
                    name='idf',
                    version=ComponentVersion(get_idf_version()),
                    source=IDFSource(),
                )
            )

        try:
            with open(self._path, mode='w', encoding='utf-8') as f:
                # inject lock file version and current target
                lock = LockFile(**solution.model_dump())
                lock.target = get_env_idf_target()

                dump_yaml(
                    data=lock.model_dump(),
                    stream=f,
                    encoding='utf-8',
                    allow_unicode=True,
                    Dumper=SafeDumper,
                )
        except ValidationError as e:
            raise LockError(f'Lock format is not valid:\n{e}')

    def load(self) -> SolvedManifest:
        if not self.exists():
            return SolvedManifest.fromdict(EMPTY_LOCK)

        try:
            with open(self._path, encoding='utf-8') as f:
                yaml_dict = safe_load(f)

            if not yaml_dict:
                lock = LockFile.fromdict(EMPTY_LOCK)
            else:
                lock = LockFile.fromdict(yaml_dict)

            lock_dict = lock.model_dump()
            version = lock_dict.pop('version')
            if version != FORMAT_VERSION:
                raise LockVersionMismatchError(
                    f'Current idf-component-manager default lock file version is {FORMAT_VERSION}, '
                    f'but found {version} in {self._path}. '
                    f'Recreating lock file with the current version.'
                )

            return SolvedManifest.fromdict(lock_dict)
        except (YAMLError, ValidationError):
            raise LockError(
                (
                    'Cannot parse components lock file. '
                    'Please check that\n\t%s\nis a valid lock YAML file.\n'
                    'You can delete corrupted lock file and it will be recreated on next run. '
                    'Some components may be updated in this case.'
                )
                % self._path
            )
