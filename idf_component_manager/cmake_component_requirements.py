# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import re
import typing as t
from collections import OrderedDict, namedtuple

from idf_component_tools.errors import FatalError

ComponentProperty = namedtuple('ComponentProperty', ['component', 'prop', 'value'])
ITERABLE_PROPS = ['REQUIRES', 'PRIV_REQUIRES', 'MANAGED_REQUIRES', 'MANAGED_PRIV_REQUIRES']
REQ_RE = re.compile(
    r'^__component_set_property\(___(?P<prefix>[a-zA-Z\d\-]+)_(?P<name>[a-zA-Z\d_\-\.\+]+)'
    r'\s+(?P<prop>\w+)\s+(?P<value>.*)\)'
)


def name_without_namespace(name: str) -> str:
    name_parts = name.rsplit('__', 1)

    try:
        return name_parts[1]
    except IndexError:
        return name_parts[0]


class ComponentName:
    def __init__(self, prefix: str, name: str) -> None:
        self.prefix = prefix
        self.name = name

        self._name_without_namespace: t.Optional[str] = None

    def __eq__(self, another: object) -> bool:
        if not isinstance(another, ComponentName):
            return False

        return (self.prefix, self.name) == (another.prefix, another.name)

    def __hash__(self) -> int:
        return hash((self.prefix, self.name))

    def __repr__(self) -> str:
        return f'ComponentName({self.prefix}, {self.name})'

    @property
    def name_without_namespace(self) -> str:
        if self._name_without_namespace is None:
            self._name_without_namespace = name_without_namespace(self.name)

        return self._name_without_namespace


class RequirementsProcessingError(FatalError):
    pass


def parse_requirements_line(line: str) -> ComponentProperty:
    match = REQ_RE.match(line)

    if not match:
        raise RequirementsProcessingError(f'Cannot parse CMake requirements line: {line}')

    return ComponentProperty(
        ComponentName(match.group('prefix'), match.group('name')),
        match.group('prop'),
        match.group('value'),
    )


class CMakeRequirementsManager:
    def __init__(self, path):
        self.path = path

    def dump(
        self, requirements: t.Mapping[ComponentName, t.Dict[str, t.Union[t.List, str]]]
    ) -> None:
        with open(self.path, mode='w', encoding='utf-8') as f:
            for name, requirement in requirements.items():
                for prop, value in requirement.items():
                    if prop in ITERABLE_PROPS:
                        value = '"{}"'.format(';'.join(value))

                    f.write(
                        '__component_set_property(___{prefix}_{name} {prop} {value})\n'.format(
                            prefix=name.prefix, name=name.name, prop=prop, value=value
                        )
                    )

    def load(self) -> t.OrderedDict[ComponentName, t.Dict[str, t.Union[t.List[str], str]]]:
        requirements: t.OrderedDict[ComponentName, t.Dict[str, t.Union[t.List[str], str]]] = (
            OrderedDict()
        )

        with open(self.path, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    prop = parse_requirements_line(line)
                    requirement = requirements.setdefault(prop.component, OrderedDict())

                    value = prop.value
                    if prop.prop in ITERABLE_PROPS:
                        value = value.strip('"').split(';')
                        try:
                            value.remove('')
                        except ValueError:
                            pass

                    requirement[prop.prop] = value

        return requirements


def check_requirements_name_collisions(
    requirements: t.Dict[ComponentName, t.Dict[str, t.Union[t.List[str], str]]],
) -> None:
    """
    DEPRECATE: This function is deprecated since interface_version 3,
        Remove it after ESP-IDF 5.1 EOL
    """
    # Pay attention only to components without namespaces
    name_variants: t.Dict[str, t.Set[str]] = {
        cmp.name: {cmp.name}
        for cmp in requirements.keys()
        if cmp.name == cmp.name_without_namespace
    }

    for cmp in requirements.keys():
        if cmp.name_without_namespace not in name_variants:
            continue

        name_variants[cmp.name_without_namespace].add(cmp.name)

    non_unique_names = {key: names for key, names in name_variants.items() if len(names) > 1}

    if non_unique_names:
        descriptions = [
            '  requirement: "{}" candidates: "{}"'.format(key, ', '.join(names))
            for key, names in non_unique_names.items()
        ]
        raise RequirementsProcessingError(
            'Cannot process component requirements. '
            'Multiple candidates to satisfy project requirements:\n{}'.format(
                '\n'.join(descriptions)
            )
        )


def _choose_component(component: str, known_components: t.List[str]) -> str:
    if component in known_components:
        return component

    # Name without namespace is required, but one with namespace is known
    # Or the the opposite: namespaced is known but required one without namespace
    namespaced_name = f'__{component}'
    for known_component in known_components:
        if (
            known_component.endswith(namespaced_name)
            or name_without_namespace(component) == known_component
        ):
            return known_component

    # In this case CMake will fail due to unknown target
    return component


def _handle_component_reqs(components: t.List[str], known_components: t.List[str]) -> t.List[str]:
    updated_items = []
    for component in components:
        name_to_add = _choose_component(component, known_components)
        if name_to_add not in updated_items:
            updated_items.append(name_to_add)

    return updated_items


def handle_project_requirements(
    requirements: t.OrderedDict[ComponentName, t.Dict[str, t.Union[t.List[str], str]]],
) -> None:
    """
    Use local components with higher priority.
    For example if in some manifest has a dependency `namespace/component`,
    but there is a local component named `namespace__component` or `component`
    it will be used instead.
    """
    known_components = [component_name.name for component_name in requirements.keys()]
    for component, requirement in requirements.items():
        for prop in ITERABLE_PROPS:
            if prop not in requirement:
                continue

            requirements[component][prop] = _handle_component_reqs(
                requirement[prop],  # type: ignore # these props are always lists
                known_components,  # type: ignore # these props are always lists
            )
