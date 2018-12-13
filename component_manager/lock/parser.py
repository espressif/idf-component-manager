import os
import sys

from strictyaml import EmptyDict, Map, MapPattern, Seq, Str, YAMLError
from strictyaml import load as load_yaml


class LockParser:
    LOCK_SCHEMA = Map(
        {
            "component_manager_version": Str(),
            "idf_version": Str(),
            "manifest_hash": Str(),
            "components": EmptyDict()
            | MapPattern(
                Str(),
                Map(
                    {
                        "version": Str(),
                        "hash": Str(),
                        "source": MapPattern(Str(), Str()),
                    }
                ),
            ),
        }
    )

    def __init__(self, path):
        self._path = path

    def load(self):
        if not os.path.exists(self._path):
            return {}

        with open(self._path, "r") as f:
            try:
                return load_yaml(f.read(), schema=self.LOCK_SCHEMA)
            except YAMLError as e:
                print(
                    (
                        "Error: Cannot parse components lock file. Please check that\n\t%s\nis valid YAML file.\n"
                        "You can delete corrupted lock file and it will be recreated on next run. "
                        "Some components may be updated in this case."
                    )
                    % self._path
                )
                print(e)
                sys.exit(1)
