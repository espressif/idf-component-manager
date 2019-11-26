import os
import sys
from collections import OrderedDict
from typing import Union

from strictyaml import (YAML, EmptyDict, Map, MapPattern, Optional, Str, YAMLError, as_document)
from strictyaml import load as load_yaml


class LockManager:
    COMPONENT_SCHEMA = EmptyDict() | MapPattern(
        Str(),
        Map(
            {
                Optional('component_hash'): Str(),
                Optional('source_specific_options'): (MapPattern(Str(), Str())),
                'source': (MapPattern(Str(), Str())),
                'version': Str(),
            }))

    LOCK_SCHEMA = Map({
        'component_manager_version': Str(),
        'dependencies': COMPONENT_SCHEMA,
        'manifest_hash': Str(),
    })

    def __init__(self, path):
        self._path = path

    def dump(self, solution):  # type: (Union[OrderedDict,YAML]) -> None
        """Writes updated lockfile to disk"""
        with open(self._path, 'w') as f:
            solution_yaml = solution if isinstance(solution, YAML) else as_document(
                solution, schema=self.LOCK_SCHEMA)  # type: YAML
            f.write(solution_yaml.as_yaml())

    def load(self):  # type: () -> YAML
        if not os.path.exists(self._path):
            return as_document(
                OrderedDict(
                    [
                        ('component_manager_version', ''),
                        ('dependencies', OrderedDict()),
                        ('manifest_hash', ''),
                    ]),
                schema=self.LOCK_SCHEMA,
            )

        with open(self._path, 'r') as f:
            try:
                # Load and validate
                lock = load_yaml(f.read(), schema=self.LOCK_SCHEMA)
                return lock
            except YAMLError as e:
                print(
                    (
                        'Error: Cannot parse components lock file. Please check that\n\t%s\nis valid YAML file.\n'
                        'You can delete corrupted lock file and it will be recreated on next run. '
                        'Some components may be updated in this case.') % self._path)
                print(e)
                sys.exit(1)
