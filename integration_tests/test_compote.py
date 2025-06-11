# SPDX-FileCopyrightText: 2022-2025 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import time

import pexpect
import pytest


def send_and_wait(child, command):
    if command is not None:
        child.sendline(command)
    child.expect([r'\$ ', r'# ', r'> ', r'% '], timeout=10)


def trigger_autocomplete(child, shell):
    # If there’s no unique completion with two tabs, bash will emit a bell character
    # https://en.wikipedia.org/wiki/Bell_character
    # Thus three tabs are required to force showing the completion
    tabs = 3 if shell == 'bash' else 2
    for _ in range(tabs):
        child.send('\t')
        time.sleep(0.3)


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
        'fish',
        'bash',
        'zsh',
    ],
)
def test_autocomplete(shell, monkeypatch):
    compote_path = shutil.which('compote')
    if not compote_path:
        pytest.fail('compote not found in Path')

    if shell in ['fish']:
        monkeypatch.setenv('TERM', 'screen-256color')  # var TERM is required in fish

    log_file = os.path.join(os.path.dirname(__file__), '..', f'{shell}.txt')
    with open(log_file, 'w', encoding='utf-8') as fw:
        # install autocomplete
        child = pexpect.spawn(f'{shell} -i', dimensions=(40, 120), encoding='utf-8')
        child.logfile = fw

        time.sleep(1)  # Allow time for shell initialization

        # Wait for shell initialization
        send_and_wait(child, None)
        # Install the autocomplete
        send_and_wait(child, f'compote autocomplete --shell {shell} --install')

        # Reload the shell
        send_and_wait(child, f'exec {shell}')

        # Test the autocomplete
        time.sleep(0.5)
        child.send('compote')
        time.sleep(0.3)
        trigger_autocomplete(child, shell)
        time.sleep(1)

        # read all buffer
        child.expect(pexpect.TIMEOUT, timeout=5)
        output = child.before + child.buffer

        for group in [
            'autocomplete',
            'cache',
            'component',
            'manifest',
            'project',
            'registry',
            'version',
        ]:
            assert group in output, (
                f"Expected '{group}' in autocomplete output for {shell}, got:\n{output}"
            )
