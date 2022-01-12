import subprocess

import pytest


@pytest.fixture()
def valid_manifest_hash():
    return '4daaa65faaa56fc0db508e3777072ed8f45feb639d5584c327ce212e94861cc6'


@pytest.fixture()
def valid_manifest():
    return {
        'version': '2.3.1',
        'targets': ['esp32'],
        'maintainers': ['Test Tester <test@example.com>'],
        'description': 'Test project',
        'url': 'https://github.com/espressif/esp-idf',
        'tags': [
            'test_tag',
            'Example',
            'one_more-tag123',
        ],
        'dependencies': {
            'idf': '~4.4.4',
            'test': {
                'version': '>=8.2.0,<9.0.0'
            },
            'test-1': '^1.2.7',
            'test-8': {
                'version': '',
                'public': True,
            },
            'test-2': '',
            'test-4': '*',
            'some_component': {
                'version': '!=1.2.7'
            },
        },
        'files': {
            'include': ['**/*'],
            'exclude': ['.pyc']
        }
    }


@pytest.fixture(scope='session')
def git_repository_with_two_branches(tmpdir_factory):
    temp_dir = tmpdir_factory.mktemp('git_repo')
    subprocess.check_output(['git', 'init', temp_dir.strpath])

    subprocess.check_output(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir.strpath)
    subprocess.check_output(['git', 'config', 'user.name', 'Test Test'], cwd=temp_dir.strpath)

    subprocess.check_output(['git', 'checkout', '-b', 'default'], cwd=temp_dir.strpath)

    f = temp_dir.mkdir('component1').join('test_file')
    f.write(u'component1')

    subprocess.check_output(['git', 'add', '*'], cwd=temp_dir.strpath)
    subprocess.check_output(['git', 'commit', '-m', '"Init commit"'], cwd=temp_dir.strpath)

    main_commit_id = subprocess.check_output(['git', 'rev-parse', 'default'], cwd=temp_dir.strpath).strip()

    subprocess.check_output(['git', 'checkout', '-b', 'new_branch'], cwd=temp_dir.strpath)

    f = temp_dir.mkdir('component2').join('test_file')
    f.write(u'component2')

    subprocess.check_output(['git', 'add', '*'], cwd=temp_dir.strpath)
    subprocess.check_output(['git', 'commit', '-m', '"Add new branch"'], cwd=temp_dir.strpath)

    branch_commit_id = subprocess.check_output(['git', 'rev-parse', 'new_branch'], cwd=temp_dir.strpath).strip()
    subprocess.check_output(['git', 'checkout', 'default'], cwd=temp_dir.strpath)

    return {
        'path': temp_dir.strpath,
        'default_head': main_commit_id.decode('utf-8'),
        'new_branch_head': branch_commit_id.decode('utf-8')
    }
