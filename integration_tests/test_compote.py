# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import sys

import pexpect
import pytest


@pytest.mark.snapshot(
    '~/.config/fish/completions',
    '~/.bashrc',
    '~/.zshrc',
    '~/.compote-complete.zsh',
    '~/.compote-complete.bash',
)
@pytest.mark.parametrize(
    'shell',
    [
        pytest.param(
            'fish',
            marks=pytest.mark.skipif(
                sys.version_info[:2] == (3, 4), reason='fish support is added in click==7.1'
            ),
        ),
        'bash',
        'zsh',
    ],
)
def test_autocomplete(shell, monkeypatch):
    if shell in ['fish']:
        monkeypatch.setenv('TERM', 'screen-256color')  # var TERM is required in fish

    with open(os.path.join(os.path.dirname(__file__), '..', '{}.txt'.format(shell)), 'wb') as fw:
        # install autocomplete
        child = pexpect.spawn('{} -i'.format(shell))
        child.logfile = fw
        child.expect([r'\$ ', '# ', '> '], timeout=5)
        child.sendline('compote autocomplete --shell {} --install'.format(shell))
        # test autocomplete
        child.expect([r'\$ ', '# ', '> '], timeout=5)
        child.sendline('exec {}'.format(shell))  # reload
        child.expect([r'\$ ', '# ', '> '], timeout=5)
        child.send('compote \t\t')
        child.flush()

        # read all buffer
        child.expect(pexpect.TIMEOUT, timeout=5)

        for group in ['autocomplete', 'cache', 'component', 'manifest', 'project', 'version']:
            assert group in child.buffer.decode('utf8')
