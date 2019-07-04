import os
import sys
from collections import OrderedDict
from typing import Union

from strictyaml import (YAML, Any, EmptyDict, Map, MapPattern, Optional, Regex, Str, YAMLError, as_document)
from strictyaml import load as load_yaml

from component_manager.version_solver.solver_result import SolverResult


class LockManager:
    COMPONENT_SCHEMA = EmptyDict() | MapPattern(
        Str(),
        Map({
            Optional("component_hash"): Str(),
            Optional("source"): (MapPattern(Str(), Str())),
            "source_type": Str(),
            "version": Str(),
        }))

    LOCK_SCHEMA = Map({
        "component_manager_version": Str(),
        "dependencies": COMPONENT_SCHEMA,
        "manifest_hash": Str(),
    })

    GENERIC_COMPONENT_SCHEMA = Map({
        "component_hash": Str(),
        "source": (MapPattern(Str(), Str())),
        "source_type": Str(),
        "version": Str(),
    })

    IDF_COMPONENT_SCHEMA = Map({
        "source_type": Regex("idf"),
        "version": Str(),
    })

    def __init__(self, path):
        self._path = path

    def dump(self, solution):  # type: (Union[SolverResult,OrderedDict,YAML]) -> None
        """Writes updated lockfile to disk"""

        comment = (
            "# This file is generated automatically by IDF component management tool.\n",
            "# Please do edit it manually. Run `idf.py component install` to update this lock file.\n",
        )

        new_file = not os.path.exists(self._path)

        with open(self._path, "w") as f:
            if new_file:
                f.writelines(comment)

            solution_dict = solution.as_ordered_dict() if isinstance(
                solution, SolverResult) else solution  # type: Union[YAML,OrderedDict]
            solution_yaml = solution_dict if isinstance(solution, YAML) else as_document(solution_dict)  # type: YAML
            f.write(solution_yaml.as_yaml())

    def load(self):  # type: () -> Any
        if not os.path.exists(self._path):
            return as_document(
                OrderedDict([
                    ("component_manager_version", ""),
                    ("dependencies", OrderedDict()),
                    ("manifest_hash", ""),
                ]),
                schema=self.LOCK_SCHEMA,
            )

        with open(self._path, "r") as f:
            try:
                lock = load_yaml(f.read(), schema=self.LOCK_SCHEMA)

                for component in lock['dependencies'].values():
                    if component['source_type'] == 'idf':
                        component.revalidate(self.IDF_COMPONENT_SCHEMA)
                    else:
                        component.revalidate(self.GENERIC_COMPONENT_SCHEMA)

                return lock
            except YAMLError as e:
                print(("Error: Cannot parse components lock file. Please check that\n\t%s\nis valid YAML file.\n"
                       "You can delete corrupted lock file and it will be recreated on next run. "
                       "Some components may be updated in this case.") % self._path)
                print(e)
                sys.exit(1)
