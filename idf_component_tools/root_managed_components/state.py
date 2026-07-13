# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import os
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML

from idf_component_tools.errors import FatalError
from idf_component_tools.manifest import Manifest
from idf_component_tools.root_managed_components.tools import root_managed_components_state_path
from idf_component_tools.semver import Version
from idf_component_tools.utils import canonical_component_name

FORMAT_VERSION = '1'

# Shared instruction appended to every "state is missing/stale/corrupt" error.
_INSTALL_COMMAND_HINT = 'Please run: compote cooking stock'


@dataclass(frozen=True)
class RootManagedComponentRecord:
    # Canonical component name, e.g. `espressif/foo`.
    name: str
    version: str
    # Absolute path to the installed component directory.
    path: str
    # Targets the component supports (its REQUIRED_IDF_TARGETS); empty means any.
    targets: t.Tuple[str, ...] = ()

    @property
    def build_name(self) -> str:
        return os.path.basename(self.path)

    @property
    def posix_path(self) -> str:
        return Path(self.path).as_posix()

    def is_compatible_with_target(self, target: t.Optional[str]) -> bool:
        return not target or not self.targets or target in self.targets


@dataclass
class RootManagedComponentsState:
    """Installed root-managed component inventory.

    This is not a solved dependency graph. It is the set of components downloaded
    from the root-managed download catalog (`tools/idf_extra_components.yml`) by the
    installer. Multiple versions of the same component may be present side by side;
    selection happens per-target at configure time.
    """

    manifest_hash: t.Optional[str] = None
    components: t.Dict[str, t.Dict[str, RootManagedComponentRecord]] = field(default_factory=dict)

    def exists(self) -> bool:
        return bool(self.components)

    def records(self) -> t.Iterator[RootManagedComponentRecord]:
        for versions in self.components.values():
            yield from versions.values()

    @classmethod
    def from_records(
        cls,
        manifest_hash: t.Optional[str],
        records: t.Iterable[RootManagedComponentRecord],
    ) -> 'RootManagedComponentsState':
        state = cls(manifest_hash=manifest_hash)
        for record in records:
            state.components.setdefault(record.name, {})[record.version] = record
        return state


class RootManagedComponentsStateManager:
    """Reads and writes the `root_components.lock` install-state file."""

    def __init__(self, path: t.Optional[t.Union[str, Path]] = None) -> None:
        self.path = Path(path) if path else root_managed_components_state_path()
        self._yaml = YAML(typ='safe')
        self._yaml.default_flow_style = False
        self._yaml.width = 2048

    @property
    def root_path(self) -> Path:
        return self.path.parent

    def exists(self) -> bool:
        return self.path.is_file()

    def load(self) -> RootManagedComponentsState:
        if not self.exists():
            return RootManagedComponentsState()

        with open(self.path, encoding='utf-8') as f:
            data = self._yaml.load(f) or {}

        if data.get('version') != FORMAT_VERSION:
            raise FatalError(
                f'Unsupported root managed components state version in {self.path}.\n'
                f'{_INSTALL_COMMAND_HINT}'
            )

        state = RootManagedComponentsState(manifest_hash=data.get('manifest_hash'))
        for name, versions in (data.get('components') or {}).items():
            for version, item in (versions or {}).items():
                version = str(version)
                try:
                    Version.parse(version)
                except (TypeError, ValueError) as e:
                    raise FatalError(
                        f'Invalid root managed component version in {self.path}: '
                        f'{name}@{version}\n{_INSTALL_COMMAND_HINT}'
                    ) from e
                path = (self.root_path / item['path']).resolve()
                try:
                    path.relative_to(self.root_path.resolve())
                except ValueError:
                    raise FatalError(
                        f'Invalid root managed component path in {self.path}: {path}\n'
                        f'{_INSTALL_COMMAND_HINT}'
                    )
                if not path.is_dir():
                    raise FatalError(_install_required_message(str(self.path)))

                record = RootManagedComponentRecord(
                    name=name,
                    version=version,
                    path=str(path),
                    targets=tuple(item.get('targets') or ()),
                )
                state.components.setdefault(name, {})[record.version] = record

        return state

    def dump(self, state: RootManagedComponentsState) -> None:
        data: t.Dict[str, t.Any] = {
            'version': FORMAT_VERSION,
            'manifest_hash': state.manifest_hash,
            'components': {},
        }

        for record in sorted(state.records(), key=lambda item: item.path):
            name = canonical_component_name(record.name)
            versions = data['components'].setdefault(name, {})
            entry: t.Dict[str, t.Any] = {
                'path': os.path.relpath(record.path, self.root_path),
            }
            if record.targets:
                entry['targets'] = list(record.targets)
            versions[str(record.version)] = entry

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            self._yaml.dump(data, f)

    def load_required_current(
        self,
        manifest_hash: str,
        manifest_path: str,
    ) -> RootManagedComponentsState:
        if not self.exists():
            raise FatalError(_install_required_message(manifest_path))

        state = self.load()
        if state.manifest_hash != manifest_hash:
            raise FatalError(_install_required_message(manifest_path, updated=True))
        return state


def validate_root_manifest(manifest: Manifest) -> None:
    for requirement in manifest.raw_requirements:
        if not requirement.meta and requirement.source.type != 'service':
            raise FatalError(
                f'Invalid {manifest.path}: dependency "{requirement.name}" uses source '
                f'"{requirement.source.type}". Root managed component manifests can only '
                'reference components from the ESP Component Registry.'
            )
        if requirement.rules:
            raise FatalError(
                f'Invalid {manifest.path}: dependency "{requirement.name}" uses "rules". '
                'Root managed component manifests are only for downloading and cannot '
                'contain conditional dependencies.'
            )
        if requirement.matches:
            raise FatalError(
                f'Invalid {manifest.path}: dependency "{requirement.name}" uses "matches". '
                'Root managed component manifests are only for downloading and cannot '
                'contain conditional dependencies.'
            )


def _install_required_message(manifest_path: str, updated: bool = False) -> str:
    if updated:
        reason = f'{manifest_path} has been updated.'
    else:
        reason = 'ESP-IDF root managed components are not installed.'

    return f'{reason}\n{_INSTALL_COMMAND_HINT}'
