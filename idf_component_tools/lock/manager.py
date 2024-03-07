# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
from collections import OrderedDict
from typing import OrderedDict as OrderedDictType

from schema import And, Optional, Or, Schema, SchemaError, Use
from yaml import Node, SafeDumper, YAMLError
from yaml import dump as dump_yaml
from yaml import safe_load

import idf_component_tools as tools

from ..build_system_tools import get_env_idf_target, get_idf_version
from ..errors import LockError
from ..manifest import ComponentVersion, known_targets
from ..manifest.solved_component import SolvedComponent
from ..manifest.solved_manifest import SolvedManifest
from ..sources import IDFSource

FORMAT_VERSION = '1.0.0'

EMPTY_LOCK = {
    'manifest_hash': None,
    'version': FORMAT_VERSION,
}

HASH_SCHEMA = Or(And(str, lambda h: len(h) == 64), None)

LOCK_SCHEMA = Schema(
    {
        Optional('dependencies'): {
            Optional(str): {
                'source': Or(*[source.schema() for source in tools.sources.KNOWN_SOURCES]),
                'version': str,
                Optional('component_hash'): HASH_SCHEMA,
            }
        },
        'manifest_hash': HASH_SCHEMA,
        'version': And(str, len),
        Optional('target'): And(Use(str.lower), lambda s: s in known_targets()),
    }
)


def _ordered_dict_representer(dumper: SafeDumper, data: OrderedDictType) -> Node:
    return dumper.represent_data(dict(data))


def _unicode_representer(dumper: SafeDumper, data: str) -> Node:
    return dumper.represent_str(data.encode('utf-8'))  # type: ignore


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
                    'idf',
                    ComponentVersion(get_idf_version()),
                    IDFSource(),
                )
            )

        try:
            with open(self._path, mode='w', encoding='utf-8') as f:
                # inject format version
                solution_dict = solution.serialize()
                solution_dict['version'] = FORMAT_VERSION
                solution_dict['target'] = get_env_idf_target()
                lock = LOCK_SCHEMA.validate(solution_dict)
                dump_yaml(
                    data=lock, stream=f, encoding='utf-8', allow_unicode=True, Dumper=SafeDumper
                )
        except SchemaError as e:
            raise LockError(f'Lock format is not valid:\n{e}')

    def load(self) -> SolvedManifest:
        if not self.exists():
            return SolvedManifest.fromdict(EMPTY_LOCK)

        with open(self._path, encoding='utf-8') as f:
            try:
                content = f.read()

                if not content:
                    return SolvedManifest.fromdict(EMPTY_LOCK)

                lock = LOCK_SCHEMA.validate(safe_load(content))

                version = lock.pop('version')
                if version != FORMAT_VERSION:
                    raise LockError(
                        'Cannot parse components lock file.'
                        'Lock file format version is %s, while only %s is supported'
                        % (version, FORMAT_VERSION)
                    )

                return SolvedManifest.fromdict(lock)
            except (YAMLError, SchemaError):
                raise LockError(
                    (
                        'Cannot parse components lock file. '
                        'Please check that\n\t%s\nis a valid lock YAML file.\n'
                        'You can delete corrupted lock file and it will be recreated on next run. '
                        'Some components may be updated in this case.'
                    )
                    % self._path
                )
