# SPDX-FileCopyrightText: 2022-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import sys
import typing as t

from idf_component_manager.cli.validations import (
    validate_add_dependency,
    validate_existing_dir,
    validate_git_url,
    validate_path_for_project,
)
from idf_component_manager.utils import (
    CLICK_SUPPORTS_SHOW_DEFAULT,
)
from idf_component_tools import error, setup_logging
from idf_component_tools.errors import FatalError

from .core import ComponentManager

PROFILE_NAME: t.List[t.Dict[str, t.Any]] = [
    {
        'names': ['--profile', '--service-profile', 'profile_name'],
        'help': 'Specifies the profile to use for this command.'
        ' By default profile named "default" will be used.'
        ' Alias "--service-profile" is deprecated and will be removed.',
        'envvar': 'IDF_COMPONENT_PROFILE',
    },
]

NAMESPACE: t.List[t.Dict[str, t.Any]] = [
    {
        'names': ['--namespace'],
        'help': 'Namespace for the component. Can be set in the config file.',
        'envvar': 'IDF_COMPONENT_NAMESPACE',
    },
]

NAME: t.List[t.Dict[str, t.Any]] = [
    {
        'names': ['--name'],
        'help': 'Component name.',
        'required': True,
    },
]

GIT_OPTIONS = [
    {
        'names': ['--git'],
        'help': 'Git URL of the component.',
        'required': False,
        'callback': validate_git_url,
    },
    {
        'names': ['--git-path'],
        'help': 'Path to the component in the git repository.',
        'default': '.',
    },
    {
        'names': ['--git-ref'],
        'help': 'Git reference (branch, tag, commit SHA) of the component.',
        'required': False,
    },
]

REGISTRY_OPTIONS = PROFILE_NAME + NAMESPACE + NAME

LOCAL_MANIFEST_OPTIONS: t.List[t.Dict[str, t.Any]] = [
    {
        'names': ['--component'],
        'default': 'main',
        'help': 'Name of the component in the project where the dependency will be added.',
    },
    {
        'names': ['-p', '--path'],
        'help': 'Path to the component where the dependency will be added. The component name is ignored when path the is specified.',
        'default': None,
        'callback': validate_existing_dir,
    },
]

if CLICK_SUPPORTS_SHOW_DEFAULT:
    LOCAL_MANIFEST_OPTIONS[0]['show_default'] = True

VERSION_PARAMETER = [
    {
        'names': ['--version'],
        'help': 'Set version, if not defined in the manifest. '
        'Use "git" to get version from git tag. '
        "The command won't try uploading, if running not from a git tag.",
        'required': False,
    }
]

CREATE_PROJECT_FROM_EXAMPLE_DESCR = """
Create a project from an example in the ESP Component Registry.

You can specify EXAMPLE in the format like:
namespace/name=1.0.0:example

where "=1.0.0" is a version specification.

An example command:

idf.py create-project-from-example example/cmp^3.3.8:cmp_ex

Namespace and version are optional in the EXAMPLE argument.
"""


def action_extensions(base_actions, project_path):  # noqa: ARG001
    setup_logging()

    def callback(subcommand_name, ctx, args, **kwargs):  # noqa: ARG001
        try:
            manager = ComponentManager(args.project_dir)
            getattr(manager, str(subcommand_name).replace('-', '_'))(**kwargs)
        except FatalError as e:
            error(str(e))
            sys.exit(e.exit_code)

    def add_dependency_callback(subcommand_name, ctx, args, **kwargs):
        validate_add_dependency(ctx, None, kwargs.get('dependency'))
        callback(subcommand_name, ctx, args, **kwargs)

    def global_callback(ctx, global_args, tasks):  # noqa: ARG001
        copy_tasks = list(tasks)
        for index, task in enumerate(copy_tasks):
            if task.name == 'fullclean':
                tasks.insert(
                    index + 1,
                    ctx.invoke(ctx.command.get_command(ctx, 'remove_managed_components')),
                )
            elif task.name == 'update-dependencies':
                reconfigure = ctx.invoke(ctx.command.get_command(ctx, 'reconfigure'))
                # reсonfigure does not take any parameters.
                # More information in the idf.py implementation (idf.py/execute_tasks)
                reconfigure.action_args = {}
                tasks.insert(index + 1, reconfigure)

    return {
        'global_action_callbacks': [global_callback],
        'actions': {
            'create-manifest': {
                'callback': callback,
                'help': (
                    'Create manifest for specified component.\n'
                    'By default:\n'
                    'If you run the command in the directory with project, the manifest'
                    ' will be created in the "main" directory.\n'
                    'If you run the command in the directory with a component, '
                    'the manifest will be created right in that directory.\n'
                    'You can explicitly specify directory using the --path option.'
                ),
                'options': LOCAL_MANIFEST_OPTIONS,
            },
            'add-dependency': {
                'callback': add_dependency_callback,
                'help': (
                    'Add dependency to the manifest file.\n'
                    'By default:\n'
                    'If you run the command in the directory with project, the dependency'
                    ' will be added to the manifest in the "main" directory.\n'
                    'If you run the command in the directory with a component, '
                    'the dependency will be added to the manifest right in that directory.\n'
                    'You can explicitly specify directory using the --path option.'
                ),
                'arguments': [
                    {
                        'names': ['dependency'],
                        'required': True,
                    },
                ],
                'options': LOCAL_MANIFEST_OPTIONS + PROFILE_NAME + GIT_OPTIONS,
            },
            'remove_managed_components': {'callback': callback, 'hidden': True},
            'upload-component': {
                'callback': callback,
                'deprecated': True,
                'hidden': True,
                'help': (
                    'New CLI command: "compote component upload". '
                    'Upload component to the component registry. '
                    "If the component doesn't exist in the registry "
                    'it will be created automatically.'
                ),
                'options': REGISTRY_OPTIONS
                + VERSION_PARAMETER
                + [
                    {
                        'names': ['--archive'],
                        'help': 'Path of the archive with a component to upload. '
                        'When not provided the component will be packed automatically.',
                    },
                    {
                        'names': ['--skip-pre-release'],
                        'help': 'Do not upload pre-release versions.',
                        'is_flag': True,
                        'default': False,
                    },
                    {
                        'names': ['--check-only'],
                        'help': 'Check if given component version is already uploaded and exit.',
                        'is_flag': True,
                        'default': False,
                    },
                    {
                        'names': ['--allow-existing'],
                        'help': 'Return success if existing version is already uploaded.',
                        'is_flag': True,
                        'default': False,
                    },
                ],
            },
            'delete-version': {
                'callback': callback,
                'deprecated': True,
                'hidden': True,
                'help': (
                    'New CLI command: "compote component delete". '
                    'Delete specified version of the component from the component registry.'
                ),
                'options': REGISTRY_OPTIONS
                + [
                    {
                        'names': ['--version'],
                        'help': 'Component version',
                        'required': True,
                    }
                ],
            },
            'upload-component-status': {
                'callback': callback,
                'deprecated': True,
                'hidden': True,
                'help': (
                    'New CLI command: "compote component upload-status". '
                    'Check the component uploading status by the job ID.'
                ),
                'options': PROFILE_NAME
                + [
                    {
                        'names': ['--job'],
                        'help': 'Job ID',
                        'required': True,
                    }
                ],
            },
            'pack-component': {
                'callback': callback,
                'deprecated': True,
                'hidden': True,
                'help': (
                    'New CLI command: "compote component pack". '
                    'Create component archive and store it in the dist directory.'
                ),
                'options': PROFILE_NAME + NAME + VERSION_PARAMETER,
            },
            'create-project-from-example': {
                'callback': callback,
                'help': CREATE_PROJECT_FROM_EXAMPLE_DESCR,
                'arguments': [{'names': ['example']}],
                'options': PROFILE_NAME
                + [
                    {
                        'names': ['-p', '--path'],
                        'help': (
                            'Set the path for the new project. The project '
                            'will be created directly in the given folder '
                            'if it does not contain anything'
                        ),
                        'required': False,
                        'callback': validate_path_for_project,
                    }
                ],
            },
            'update-dependencies': {
                'callback': callback,
                'help': 'Update dependencies of the project',
            },
        },
    }
