# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import typing as t
from io import StringIO

from pydantic import ValidationError
from ruamel.yaml import YAML, YAMLError

from idf_component_tools.build_system_tools import get_env_idf_target, get_idf_version
from idf_component_tools.errors import LockError
from idf_component_tools.manifest import SolvedComponent, SolvedManifest
from idf_component_tools.messages import notice
from idf_component_tools.sources import IDFSource
from idf_component_tools.utils import ComponentVersion

FORMAT_VERSION = '2.0.0'


class LockFile(SolvedManifest):
    version: str = FORMAT_VERSION


EMPTY_LOCK: t.Dict[str, t.Any] = {}


class LockManager:
    def __init__(self, path):
        self._path = path
        self._yaml = YAML(typ='safe')
        self._yaml.default_flow_style = False

    def exists(self):
        return os.path.isfile(self._path)

    def dump(self, solution: SolvedManifest) -> bool:
        """
        Writes updated lockfile to disk. Won't write if lockfile is already up to date.

        :param: the solved manifest, which includes all the components with decided versions
        :return: True if lockfile was updated, False otherwise
        """
        current_idf = SolvedComponent(
            name='idf',
            version=ComponentVersion(get_idf_version()),
            source=IDFSource(),
        )

        # always use the current idf version
        if 'idf' in solution.solved_components:
            solution.dependencies.remove(solution.solved_components['idf'])
            solution.dependencies.append(current_idf)
        else:
            solution.dependencies.append(current_idf)

        try:
            with StringIO() as new_lock:
                # inject lock file version and current target
                lock = LockFile(**solution.model_dump())
                lock.target = get_env_idf_target()

                self._yaml.dump(
                    data=lock.model_dump(),
                    stream=new_lock,
                )
                new_lock.seek(0)
                new_lock_content = new_lock.read()
        except ValidationError as e:
            raise LockError(f'Lock format is not valid:\n{e}')

        # create it when string is different
        if (
            not self.exists()
            or new_lock_content != open(self._path, mode='r', encoding='utf-8').read()
        ):
            with open(self._path, mode='w', encoding='utf-8') as fw:
                fw.write(new_lock_content)
                notice('Updating lock file at {}'.format(self._path))
                return True

        return False

    def load(self) -> SolvedManifest:
        if not self.exists():
            return SolvedManifest.fromdict(EMPTY_LOCK)

        try:
            with open(self._path, encoding='utf-8') as f:
                yaml_dict = self._yaml.load(f)

            if not yaml_dict:
                lock = LockFile.fromdict(EMPTY_LOCK)
            else:
                lock = LockFile.fromdict(yaml_dict)

            lock_dict = lock.model_dump()
            version = lock_dict.pop('version')
            if version != FORMAT_VERSION:
                notice(
                    f'Current idf-component-manager default lock file version is {FORMAT_VERSION}, '
                    f'but found {version} in {self._path}. '
                    f'Recreating lock file with the current version.'
                )

            return SolvedManifest.fromdict(lock_dict)
        except (YAMLError, ValidationError):
            raise LockError(
                'Cannot parse components lock file. '
                f'Please check that\n\t{self._path}\nis a valid lock YAML file.\n'
                'You can delete corrupted lock file and it will be recreated on next run. '
                'Some components may be updated in this case.'
            )
