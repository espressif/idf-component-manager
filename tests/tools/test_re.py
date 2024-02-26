# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
from pytest import mark

from idf_component_tools.constants import COMPILED_FILE_RE, COMPILED_GIT_URL_RE


@mark.parametrize(
    'url',
    [
        'git://github.com/user/repo.git',
        'ssh://git@github.com/user/repo.git',
        'https://github.com/user/repo.git',
        # Without .git suffix
        'git://github.com/user/repo',
        'ssh://git@github.com/user/repo',
        'https://github.com/user/repo',
        'http://github.com/user/repo',
        # Without protocol
        'git@github.com:user/repo',
        'git@github.com:user/user.git',
    ],
)
def test_valid_git_urls(url):
    assert COMPILED_GIT_URL_RE.match(url), f'Failed to match valid URL: {url}'


@mark.parametrize(
    'url',
    [
        # missing protocol
        'github.com/user/repo',
        # unsupported protocol
        'ftp://github.com/user/repo',
        # random string
        'arstfpwafp',
        # random string with special characters
        'WRj7vPcetd3!^Jun8r&WoSM9',
    ],
)
def test_invalid_git_urls(url):
    assert not COMPILED_GIT_URL_RE.match(url), f'Matched invalid URL: {url}'


@mark.parametrize(
    'path',
    [
        'file://C:\\\\test\\folder\\',
        'file://C:\\\\new_\\path\\help\\',
        'file://C:\\\\a\\..\\path\\',
        # Unix Path
        'file:///data/storage/',
        'file:///data/storage/../new_folder/',
    ],
)
def test_valid_file_re(path):
    assert COMPILED_FILE_RE.match(path)


@mark.parametrize(
    'path',
    [
        'file://C:\\\\test\\folder',
        'file://C:\\\\new_\\path\\help?.@\\',
        'file://../../a/',
        # Unix Path
        'file://../data/storage/',
    ],
)
def test_invalid_file_re(path):
    assert not COMPILED_FILE_RE.match(path)
