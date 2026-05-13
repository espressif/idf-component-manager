# SPDX-FileCopyrightText: 2022-2026 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0


from idf_component_manager.__main__ import main
from tests.network_test_utils import use_vcr_or_real_env


def test_cli(mocker):
    """Test that safe_cli is executed"""
    mock_initialize_cli = mocker.patch('idf_component_manager.cli.core.initialize_cli')

    main()

    mock_initialize_cli.assert_called_once_with()


def test_cooking_commands_are_hidden_but_callable(invoke_cli, mocker):
    install_root_components = mocker.patch(
        'idf_component_manager.cli.cooking.install_root_components'
    )

    help_output = invoke_cli('--help')
    assert help_output.exit_code == 0
    assert 'cooking' not in help_output.output

    result = invoke_cli('cooking', 'stock')

    assert result.exit_code == 0
    install_root_components.assert_called_once_with()


def test_cooking_prepare_delegates_to_prepare_components(invoke_cli, mocker):
    prepare_dep_dirs = mocker.patch('idf_component_manager.cli.cooking.prepare_dep_dirs')

    result = invoke_cli(
        'cooking',
        'prepare',
        '--project_dir=/project',
        '--lock_path=dependencies.lock',
        '--interface_version=6',
        '--use_sdk_json=true',
        '--managed_components_list_file=managed.cmake',
        '--local_components_list_file=local.yml',
        '--build_dir=build',
    )

    assert result.exit_code == 0
    args = prepare_dep_dirs.call_args.args[0]
    assert args.project_dir == '/project'
    assert args.lock_path == 'dependencies.lock'
    assert args.interface_version == 6
    assert args.use_sdk_json == 'true'
    assert args.managed_components_list_file == 'managed.cmake'
    assert args.local_components_list_file == 'local.yml'
    assert args.build_dir == 'build'


def test_cooking_inject_delegates_to_prepare_components(invoke_cli, mocker):
    inject_requirements = mocker.patch('idf_component_manager.cli.cooking.inject_requirements')

    result = invoke_cli(
        'cooking',
        'inject',
        '--project_dir=/project',
        '--lock_path=dependencies.lock',
        '--interface_version=6',
        '--use_sdk_json=true',
        '--component_requires_file=requires.cmake',
        '--build_dir=build',
        '--idf_path=/idf',
    )

    assert result.exit_code == 0
    args = inject_requirements.call_args.args[0]
    assert args.project_dir == '/project'
    assert args.lock_path == 'dependencies.lock'
    assert args.interface_version == 6
    assert args.use_sdk_json == 'true'
    assert args.component_requires_file == 'requires.cmake'
    assert args.build_dir == 'build'
    assert args.idf_path == '/idf'


@use_vcr_or_real_env('tests/fixtures/vcr_cassettes/test_exception_on_warnings.yaml')
def test_raise_exception_on_warnings(invoke_cli, mock_registry):  # noqa: ARG001
    output = invoke_cli(
        '--warnings-as-errors',
        'project',
        'create-from-example',
        'test_component_manager/ynk=1.0.0:cmp_ex',
    )

    assert output.exit_code == 1
    assert (
        'The following versions of the "test_component_manager/ynk" component have been yanked:\n'
        in str(output.exception)
    )
