# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import json
import os
import subprocess  # nosec
import sys
from io import open

import click

from idf_component_manager.core import ComponentManager
from idf_component_manager.utils import CLICK_SUPPORTS_SHOW_DEFAULT, print_error, print_info
from idf_component_tools.errors import FatalError
from idf_component_tools.file_cache import FileCache
from idf_component_tools.file_tools import human_readable_size
from idf_component_tools.manifest.validator import manifest_json_schema

try:
    from typing import Any
except ImportError:
    pass

CLI_NAME = 'compote'


def add_options(options):
    def wrapper(func):
        for _option in reversed(options):
            func = _option(func)

        return func

    return wrapper


DEFAULT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
}  # type: dict[str, Any]

if CLICK_SUPPORTS_SHOW_DEFAULT:
    DEFAULT_SETTINGS['show_default'] = True


def safe_cli():
    """
    Cli entrypoint with error handling
    """
    try:
        cli()
    except FatalError as e:
        print_error(e)
        sys.exit(e.exit_code)


@click.group(context_settings=DEFAULT_SETTINGS)
def cli():
    pass


@cli.group()
def project():
    """
    Group of project related commands
    """
    pass


PROJECT_DIR_OPTION = [
    click.option(
        '--project-dir', 'manager', default=os.getcwd(), callback=lambda ctx, param, value: ComponentManager(value)),
]
SERVICE_PROFILE_OPTION = [
    click.option(
        '--service-profile',
        envvar='IDF_COMPONENT_SERVICE_PROFILE',
        default='default',
        help='Profile for component registry to use.',
    ),
]
PROJECT_OPTIONS = PROJECT_DIR_OPTION + SERVICE_PROFILE_OPTION

NAMESPACE_OPTION = [
    click.option(
        '--namespace',
        envvar='IDF_COMPONENT_NAMESPACE',
        default='espressif',
        help='Namespace for the component. Can be set in config file.',
    ),
]
NAME_OPTION = [click.option('--name', required=True, help='Component name')]
NAMESPACE_NAME_OPTIONS = NAMESPACE_OPTION + NAME_OPTION


@project.command()
@add_options(PROJECT_DIR_OPTION)
@click.option(
    '-p',
    '--path',
    default=None,
    help='Path of the new project. The project will be created directly in the given folder if it is empty.')
@click.argument('example', required=True)
def create_from_example(manager, example, path):
    """
    Create a project from an example.

    You can specify EXAMPLE in the format like:
      namespace/name=1.0.0:example

    where "=1.0.0" is a version specification.

    An example command:

      compote project create-from-example example/cmp^3.3.8:cmp_ex

    Namespace and version are optional in the EXAMPLE argument.
    """
    manager.create_project_from_example(example, path=path)


@project.command()
@add_options(PROJECT_DIR_OPTION)
def remove_managed_components(manager):
    """
    Remove the managed_components folder.
    """

    manager.remove_managed_components()


@cli.group()
def manifest():
    """
    Group of manifest related commands
    """
    pass


@manifest.command()
def schema():
    """
    Print json schema of the manifest file idf_component.yml
    """
    print(json.dumps(manifest_json_schema(), indent=2))


MANIFEST_COMPONENT_NAME_OPTION = [click.option('--component', default='main', help='Component name in the project')]


@manifest.command()
@add_options(PROJECT_DIR_OPTION + MANIFEST_COMPONENT_NAME_OPTION)
def create(manager, component):
    """
    Create manifest file for the specified component.
    """
    manager.create_manifest(component=component)


@manifest.command()
@add_options(PROJECT_DIR_OPTION + MANIFEST_COMPONENT_NAME_OPTION)
@click.argument('dependency', required=True)
def add_dependency(manager, component, dependency):
    """
    Add dependency to the manifest file. For now we only support adding dependencies from the component registry.

    \b
    Examples:
    - $ compote manifest add-dependency example/cmp
      would add component `example/cmp` with constraint `*`
    - $ compote manifest add-dependency example/cmp<=2.0.0
      would add component `example/cmp` with constraint `<=2.0.0`
    """
    manager.add_dependency(dependency, component=component)


@cli.group()
def component():
    """
    Group of component related commands
    """
    pass


COMPONENT_VERSION_OPTION = [
    click.option(
        '--version',
        help='Set version if not defined in the manifest. Use "git" to get version from the git tag. '
        '(command would fail if running not from a git tag)',
    )
]


@component.command()
@add_options(PROJECT_DIR_OPTION + NAMESPACE_NAME_OPTIONS + COMPONENT_VERSION_OPTION)
def pack(manager, namespace, name, version):  # noqa: namespace is not used
    """
    Create component archive and store it in the dist directory.
    """
    manager.pack_component(name, version)


@component.command()
@add_options(PROJECT_OPTIONS + NAMESPACE_NAME_OPTIONS + COMPONENT_VERSION_OPTION)
@click.option(
    '--archive',
    help='Path of the archive with a component to upload. '
    'When not provided the component will be packed automatically.',
)
@click.option('--skip-pre-release', is_flag=True, default=False, help='Do not upload pre-release versions.')
@click.option(
    '--check-only', is_flag=True, default=False, help='Check if given component version is already uploaded and exit.')
@click.option(
    '--allow-existing', is_flag=True, default=False, help='Return success if existing version is already uploaded.')
def upload(manager, service_profile, namespace, name, version, archive, skip_pre_release, check_only, allow_existing):
    """
    Upload component to the component registry.

    If the component doesn't exist in the registry it will be created automatically.
    """
    manager.upload_component(
        name,
        version=version,
        service_profile=service_profile,
        namespace=namespace,
        archive=archive,
        skip_pre_release=skip_pre_release,
        check_only=check_only,
        allow_existing=allow_existing,
    )


@component.command()
@add_options(PROJECT_OPTIONS)
@click.option('--job', required=True, help='Upload job ID')
def upload_status(manager, service_profile, job):
    """
    Check the component uploading status.
    """
    manager.upload_component_status(job, service_profile=service_profile)


@component.command()
@add_options(PROJECT_OPTIONS + NAMESPACE_NAME_OPTIONS)
@click.option('--version', required=True, help='Component version to delete')
def delete(manager, service_profile, namespace, name, version):
    """
    Delete specified version of the component from the component registry.
    The deleted version cannot be restored or re-uploaded.
    """
    manager.delete_version(name, version, service_profile=service_profile, namespace=namespace)


@cli.command()
@click.option('--shell', required=True, type=click.Choice(['bash', 'zsh', 'fish']), help='Shell type')
def autocomplete(shell):
    """
    Inject autocomplete to your shell

    \b
    Examples:
    - $ compote autocomplete --shell zsh
      would inject the autocomplete file into your zsh.
      run `exec zsh` afterwards would make it work for your current terminal.
    """
    if shell == 'bash':
        complete_filepath = '~/.{}-complete.bash'.format(CLI_NAME)
        shell_str = '_{}_COMPLETE=bash_source {} > {}'.format(CLI_NAME.upper(), CLI_NAME, complete_filepath)
        config_filepath = '~/.bashrc'
        config_str = '. {}'.format(complete_filepath)
    elif shell == 'zsh':
        complete_filepath = '~/.{}-complete.zsh'.format(CLI_NAME)
        shell_str = '_{}_COMPLETE=zsh_source {} > {}'.format(CLI_NAME.upper(), CLI_NAME, complete_filepath)
        config_filepath = '~/.zshrc'
        config_str = '. {}'.format(complete_filepath)
    else:  # fish
        complete_filepath = '~/.config/fish/completions/{}.fish'.format(CLI_NAME)
        shell_str = '_{}_COMPLETE=fish_source {} > {}'.format(CLI_NAME.upper(), CLI_NAME, complete_filepath)
        config_filepath = ''
        config_str = ''

    if config_filepath and config_str:
        config = os.path.expanduser(config_filepath)
        if not os.path.isfile(config):
            s = ''
        else:
            with open(config, 'r') as fr:
                s = fr.read()

        if config_str not in s:
            with open(config, 'a+') as fw:
                fw.write('\n{}\n'.format(config_str))

    complete_file = os.path.expanduser(complete_filepath)
    if not os.path.isdir(os.path.dirname(complete_file)):
        os.makedirs(os.path.dirname(complete_file))

    subprocess.call(shell_str, shell=True)  # nosec


@cli.group()
def cache():
    """
    Group of cache related commands
    """
    pass


@cache.command()
def clear():
    """
    Clear cache of components and API client cache
    """
    FileCache().clear()
    print_info('Successfully cleared cache at\n\t{}'.format(FileCache().path()))


@cache.command()
def path():
    """
    Print cache path
    """
    print_info(FileCache().path())


@cache.command()
@click.option('--bytes', is_flag=True, default=False, help='Print size in bytes')
def size(bytes):
    """
    Print cache size of cache in human readable format
    """
    size = FileCache().size()
    if bytes:
        print_info(str(size))
    else:
        print_info(human_readable_size(size))
