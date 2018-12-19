import os
import sys
from collections import OrderedDict

from strictyaml import EmptyDict, Map, MapPattern, Str, YAMLError, as_document
from strictyaml import load as load_yaml


class LockParser:
    COMPONENTS_SCHEMA = EmptyDict() | MapPattern(
        Str(),
        Map(
            {
                "version": Str(),
                "hash": Str(),
                "source_type": Str(),
                "source": MapPattern(Str(), Str()),
            }
        ),
    )
    LOCK_SCHEMA = Map(
        {
            "component_manager_version": Str(),
            "idf_version": Str(),
            "manifest_hash": Str(),
            "components": COMPONENTS_SCHEMA,
        }
    )

    def __init__(self, path):
        self._path = path

    def dump(self, solution):
        """Writes updated lockfile to disk"""

        comment = (
            "# This file is generated automatically by IDF component management tool.\n",
            "# Please do edit it manually. Run `idf.py component install` to update this lock file.\n",
        )

        new_file = not os.path.exists(self._path)

        with open(self._path, "w") as f:
            if new_file:
                f.writelines(comment)
            f.write(solution.as_yaml())

    def load(self):
        if not os.path.exists(self._path):
            return as_document(
                OrderedDict(
                    [
                        ("component_manager_version", ""),
                        ("idf_version", ""),
                        ("manifest_hash", ""),
                        ("components", OrderedDict()),
                    ]
                ),
                schema=self.LOCK_SCHEMA,
            )

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
