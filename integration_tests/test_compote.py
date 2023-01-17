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
@pytest.mark.skipif(sys.version_info < (3, 5, 0), reason='Old pythons are not supported')
@pytest.mark.parametrize('shell', [
    'fish',
    'bash',
    'zsh',
])
@pytest.mark.flaky(reruns=10, reruns_delay=2)
def test_autocomplete(shell, monkeypatch):
    if shell in ['fish']:
        monkeypatch.setenv('TERM', 'screen-256color')  # var TERM is required in fish

    with open(os.path.join(os.path.dirname(__file__), '..', '{}.txt'.format(shell)), 'wb') as fw:
        TIMEOUT = 10
        # install autocomplete
        child = pexpect.spawn('{} -i'.format(shell))
        child.logfile = fw
        child.expect([r'\$ ', '# ', '> '], timeout=TIMEOUT)
        child.sendline('compote autocomplete --shell {}'.format(shell))
        # test autocomplete
        child.expect([r'\$ ', '# ', '> '], timeout=TIMEOUT)
        child.sendline('exec {}'.format(shell))  # reload
        child.expect([r'\$ ', '# ', '> '], timeout=TIMEOUT)
        child.send('compote \t\t')
        for group in ['autocomplete', 'component', 'manifest', 'project']:
            child.expect(group, timeout=TIMEOUT / 2)
