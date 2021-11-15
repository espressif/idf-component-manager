import re
from collections import OrderedDict, namedtuple
from io import open

from idf_component_tools.errors import FatalError

try:
    from typing import Dict, List, Mapping, Union
except ImportError:
    pass

ComponentName = namedtuple('ComponentName', ['prefix', 'name'])
ComponentProperty = namedtuple('ComponentProperty', ['component', 'prop', 'value'])
ITERABLE_PROPS = ['REQUIRES', 'PRIV_REQUIRES']
REQ_RE = re.compile(
    r'^__component_set_property\(___(?P<prefix>[a-zA-Z\d\-]+)_(?P<name>[a-zA-Z\d_\-\.\+]+)'
    r'\s+(?P<prop>\w+)\s+(?P<value>.*)\)')


class RequirementsProcessingError(FatalError):
    pass


def parse_requirements_line(line):  # type: (str) -> ComponentProperty
    match = REQ_RE.match(line)

    if not match:
        raise RequirementsProcessingError('Cannot parse CMake requirements line: %s' % line)

    return ComponentProperty(
        ComponentName(match.group('prefix'), match.group('name')),
        match.group('prop'),
        match.group('value'),
    )


class CMakeRequirementsManager(object):
    def __init__(self, path):
        self.path = path

    def dump(self, requirements):  # type: (Mapping[ComponentName, Dict[str, Union[List, str]]]) -> None
        with open(self.path, mode='w', encoding='utf-8') as f:
            for name, requirement in requirements.items():
                for prop, value in requirement.items():
                    if prop in ITERABLE_PROPS:
                        value = '"{}"'.format(';'.join(value))

                    f.write(
                        u'__component_set_property(___{prefix}_{name} {prop} {value})\n'.format(
                            prefix=name.prefix, name=name.name, prop=prop, value=value))

    def load(self):  # type: () -> Dict[ComponentName, Dict[str, Union[List, str]]]
        requirements = OrderedDict()  # type: Dict[ComponentName, Dict[str, Union[List, str]]]

        with open(self.path, mode='r', encoding='utf-8') as f:
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
