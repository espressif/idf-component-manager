import os

import pytest


@pytest.fixture()
def cmp_path():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '..',
        'fixtures',
        'components',
        'cmp',
    )
