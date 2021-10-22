import re

from idf_component_tools.manifest import WEB_DEPENDENCY_REGEX


def test_web_dep_re():
    valid_names = {
        'test': ('test', ''),
        't-e-s-t': ('t-e-s-t', ''),
        't-e_s-t': ('t-e_s-t', ''),
        'test>1': ('test', '>1'),
        'test/test>1': ('test/test', '>1'),
        'test/test==2': ('test/test', '==2'),
        't-e-s-t/t_e_s_t*': ('t-e-s-t/t_e_s_t', '*'),
    }

    invalid_names = ('!#@', 'adf\nadsf', '_', '-', '_good')

    for name, groups in valid_names.items():
        assert re.match(WEB_DEPENDENCY_REGEX, name).groups() == groups

    for name in invalid_names:
        assert not re.match(WEB_DEPENDENCY_REGEX, name)
