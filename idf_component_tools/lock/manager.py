import os
from io import open
from typing import Any, Dict, Union

import idf_component_tools as tools
import yaml
from schema import And, Optional, Or, Schema, SchemaError
from six import string_types

from ..errors import LockError
from ..manifest import FORMAT_VERSION, SolvedManifest

EMPTY_DEPS = dict()  # type: Dict[str, Any]
EMPTY_LOCK = {
    'dependencies': EMPTY_DEPS,
    'manifest_hash': None,
    'version': FORMAT_VERSION,
}

HASH_SCHEMA = And(Or(*string_types), lambda h: len(h) == 64)

LOCK_SCHEMA = Schema(
    {
        'dependencies': {
            Or(*string_types): {
                'source': Or(*[source.schema() for source in tools.sources.KNOWN_SOURCES]),
                'version': Or(*string_types),
                Optional('component_hash'): HASH_SCHEMA,
            }
        },
        'manifest_hash': HASH_SCHEMA,
        'version': And(Or(*string_types), len),
    })


class LockManager:
    def __init__(self, path):
        self._path = path

    def exists(self):
        return os.path.isfile(self._path)

    def dump(self, solution):  # type: (Union[Dict, SolvedManifest]) -> None
        """Writes updated lockfile to disk"""
        try:
            with open(self._path, mode='w', encoding='utf-8') as f:
                lock = LOCK_SCHEMA.validate(dict(solution))
                yaml.dump(data=lock, stream=f, encoding='utf-8', allow_unicode=True)
        except SchemaError as e:
            raise LockError('Lock format is not valid:\n%s' % str(e))

    def load(self):  # type: () -> Dict
        if not self.exists():
            return EMPTY_LOCK

        with open(self._path, mode='r', encoding='utf-8') as f:
            try:
                lock = LOCK_SCHEMA.validate(yaml.safe_load(f.read()))
                return lock
            except (yaml.YAMLError, SchemaError):
                raise LockError(
                    (
                        'Cannot parse components lock file. Please check that\n\t%s\nis a valid lock YAML file.\n'
                        'You can delete corrupted lock file and it will be recreated on next run. '
                        'Some components may be updated in this case.') % self._path)
