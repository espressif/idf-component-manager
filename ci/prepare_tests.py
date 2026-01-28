# SPDX-FileCopyrightText: 2022-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import re
import subprocess
from os import environ, getenv
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Default template configuration
DEFAULT_IDF_BRANCHES = ['release-v6.0', 'master']
DEFAULT_PYTHON_VERSIONS = ['3.10', '3.14']
DEFAULT_PYTEST_SPLIT_GROUPS = [1, 2, 3, 4, 5]

# Constraint file version mapping for master branch
MASTER_CONSTRAINT_VERSION = 'v6.1'


def sanitize_branch_for_docker_tag(branch: str) -> str:
    """Sanitize branch name for use in Docker image tags.
    Docker tags cannot contain '/'. Replace with '-'.
    """
    return branch.replace('/', '-')


def get_template_config() -> dict:
    """Get template configuration, allowing env var overrides."""
    idf_branches_env = getenv('IDF_BRANCHES')
    if idf_branches_env:
        idf_branches = [
            sanitize_branch_for_docker_tag(b.strip()) for b in idf_branches_env.split(',')
        ]
    else:
        idf_branches = DEFAULT_IDF_BRANCHES

    return {
        'idf_branches': idf_branches,
        'python_versions': DEFAULT_PYTHON_VERSIONS,
        'pytest_split_groups': DEFAULT_PYTEST_SPLIT_GROUPS,
        'master_constraint_version': MASTER_CONSTRAINT_VERSION,
    }


# integration tests
INTEGRATION_TESTS_RE = re.compile(r'^(.*,)*run_integration_tests(,.*)*$')
SKIP_INTEGRATION_TESTS_RE = re.compile(r'^(.*,)*skip_integration_tests(,.*)*$')

# dockerfiles
BUILD_DOCKER_RE = re.compile(r'^(.*,)*build_docker(,.*)*$')


def _modified_files(branch: str) -> str:
    return subprocess.check_output([
        'git',
        'diff-tree',
        '-r',
        '--name-only',
        '--no-commit-id',
        f'origin/{branch}',
        environ['CI_COMMIT_SHA'],
    ]).decode('utf-8')


def should_run_build_docker_files() -> bool:
    basic_conditions = [
        BUILD_DOCKER_RE.match(getenv('CI_MERGE_REQUEST_LABELS', '')),
        getenv('BUILD_DOCKER_IMAGE') == '1',
    ]

    if any(basic_conditions):
        return True

    # Check for changed files
    target_branch = getenv('CI_MERGE_REQUEST_TARGET_BRANCH_NAME')
    if target_branch:
        changed_files = _modified_files(target_branch)
        if 'Dockerfile' in changed_files:
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
        getenv('RUN_INTEGRATION_TESTS') == '1',
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

    return False


def render_template(ci_dir: Path, template_name: str, output_file) -> None:
    """Render a Jinja2 template and append to output file."""
    env = Environment(loader=FileSystemLoader(ci_dir))
    template = env.get_template(template_name)
    rendered = template.render(**get_template_config())
    output_file.write(rendered)
    output_file.write('\n')


def main():
    ci_dir = Path(environ['CI_PROJECT_DIR']) / 'ci'
    with open(ci_dir / 'tests.yml', 'a') as out:
        if should_run_integration_tests():
            print('Adding integration tests')
            render_template(ci_dir, 'integration_tests.yml.j2', out)
        if should_run_build_docker_files():
            print('Adding build docker files')
            render_template(ci_dir, 'build_docker.yml.j2', out)


if __name__ == '__main__':
    main()
