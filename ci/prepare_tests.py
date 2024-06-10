# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import re
import shutil
import subprocess  # nosec
from io import open
from os import environ, getenv
from pathlib import Path

# integration tests
INTEGRATION_TESTS_RE = re.compile(r'^(.*,)*run_integration_tests(,.*)*$')
SKIP_INTEGRATION_TESTS_RE = re.compile(r'^(.*,)*skip_integration_tests(,.*)*$')

# dockerfiles
BUILD_DOCKER_RE = re.compile(r'^(.*,)*build_docker(,.*)*$')


def _modified_files(branch: str) -> str:
    return subprocess.check_output(  # nosec
        [
            'git',
            'diff-tree',
            '-r',
            '--name-only',
            '--no-commit-id',
            f'origin/{branch}',
            environ['CI_COMMIT_SHA'],
        ]
    ).decode('utf-8')


def should_run_build_docker_files() -> bool:
    basic_conditions = [
        BUILD_DOCKER_RE.match(getenv('CI_MERGE_REQUEST_LABELS', '')),
    ]

    if any(basic_conditions):
        return True

    # Check for changed files
    if target_branch := getenv('CI_MERGE_REQUEST_TARGET_BRANCH_NAME'):
        changed_files = _modified_files(target_branch)
        if 'Dockerfile' in changed_files:
            return True

        if 'setup.py' in changed_files:
            return True

    return False


def should_run_integration_tests() -> bool:
    # Check if integration tests are forcefully disabled:
    if getenv('RUN_INTEGRATION_TESTS') == '0' or SKIP_INTEGRATION_TESTS_RE.match(
        getenv('CI_MERGE_REQUEST_LABELS', '')
    ):
        return False

    basic_conditions = [
        # Check if current branch is main
        getenv('CI_COMMIT_BRANCH') == getenv('CI_DEFAULT_BRANCH', 'main'),
        # Check if current branch is release one
        getenv('CI_COMMIT_BRANCH', '').startswith('release/v'),
        # run_integration_tests label
        INTEGRATION_TESTS_RE.match(getenv('CI_MERGE_REQUEST_LABELS', '')),
        # Check env-variable triggers
        getenv('RUN_INTEGRATION_TESTS') == 'true',
        getenv('CI_PIPELINE_SOURCE') == 'schedule',
    ]

    if any(basic_conditions):
        return True

    # Check for changed files
    target_branch = getenv('CI_MERGE_REQUEST_TARGET_BRANCH_NAME')
    if target_branch:
        modified_files = _modified_files(target_branch)
        # If integration tests were modified
        if 'integration_tests' in modified_files:
            return True

        # If version was bumped during release preparation
        if 'CHANGELOG.md' in modified_files:
            return True

    return False


def main():
    ci_dir = Path(environ['CI_PROJECT_DIR']) / 'ci'
    if should_run_integration_tests():
        print('Adding integration tests')
        with open(ci_dir / 'tests.yml', 'a') as out, open(ci_dir / 'integration_tests.yml') as inp:
            shutil.copyfileobj(inp, out)
    if should_run_build_docker_files():
        print('Adding build docker files')
        with open(ci_dir / 'tests.yml', 'a') as out, open(ci_dir / 'build_docker.yml') as inp:
            shutil.copyfileobj(inp, out)


if __name__ == '__main__':
    main()
