# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import sys
import warnings

from idf_component_manager.utils import CLICK_SUPPORTS_SHOW_DEFAULT, print_error, showwarning
from idf_component_tools.errors import FatalError

from .core import ComponentManager

try:
    from typing import Any, Dict, List
except ImportError:
    pass

SERVICE_PROFILE = [
    {
        'names': ['--service-profile'],
        'help': 'Profile for component registry to use. By default profile named "default" will be used.',
        'envvar': 'IDF_COMPONENT_SERVICE_PROFILE',
    },
]  # type: List[Dict[str, Any]]

NAMESPACE = [
    {
        'names': ['--namespace'],
        'help': 'Namespace for the component. Can be set in config file.',
        'envvar': 'IDF_COMPONENT_NAMESPACE',
    },
]  # type: List[Dict[str, Any]]

NAME = [
    {
        'names': ['--name'],
        'help': 'Component name.',
        'required': True,
    },
]  # type: List[Dict[str, Any]]

SERVICE_OPTIONS = SERVICE_PROFILE + NAMESPACE + NAME

LOCAL_MANIFEST_OPTIONS = [
    {
        'names': ['--component'],
        'default': 'main',
        'help': 'Name of the component in the project.',
    },
]  # type: list[dict[str, Any]]

if CLICK_SUPPORTS_SHOW_DEFAULT:
    LOCAL_MANIFEST_OPTIONS[0]['show_default'] = True

VERSION_PARAMETER = [
    {
        'names': ['--version'],
        'help': 'Set version, if not defined in the manifest. Use "git" to get version from git tag. '
        "The command won\'t try uploading, if running not from a git tag.",
        'required': False,
    }
]

CREATE_PROJECT_FROM_EXAMPLE_DESCR = """
Create a project from an example.

You can specify EXAMPLE in the format like:
namespace/name=1.0.0:example

where "=1.0.0" is a version specification.

An example command:

idf.py create-project-from-example example/cmp^3.3.8:cmp_ex

Namespace and version are optional in the EXAMPLE argument.
"""


def action_extensions(base_actions, project_path):
    def callback(subcommand_name, ctx, args, **kwargs):
        try:
            warnings.showwarning = showwarning
            manager = ComponentManager(args.project_dir)
            getattr(manager, str(subcommand_name).replace('-', '_'))(**kwargs)
        except FatalError as e:
            print_error(e)
            sys.exit(e.exit_code)

    def global_callback(ctx, global_args, tasks):
        copy_tasks = list(tasks)
        for index, task in enumerate(copy_tasks):
            if task.name == 'fullclean':
                tasks.insert(index + 1, ctx.invoke(ctx.command.get_command(ctx, 'remove_managed_components')))

    return {
        'global_action_callbacks': [global_callback],
        'actions': {
            'create-manifest': {
                'callback': callback,
                'help': 'Create manifest for specified component.',
                'options': LOCAL_MANIFEST_OPTIONS,
            },
            'add-dependency': {
                'callback': callback,
                'help': (
                    'Add dependency to the manifest file. '
                    'For now we only support adding dependencies from the component registry.'),
                'arguments': [
                    {
                        'names': ['dependency'],
                        'required': True,
                    },
                ],
                'options': LOCAL_MANIFEST_OPTIONS,
            },
            'remove_managed_components': {
                'callback': callback,
                'hidden': True
            },
            'upload-component': {
                'callback': callback,
                'deprecated': True,
                'help': (
                    'New CLI command: "compote component upload". '
                    'Upload component to the component registry. '
                    'If the component doesn\'t exist in the registry it will be created automatically.'),
                'options': SERVICE_OPTIONS + VERSION_PARAMETER + [
                    {
                        'names': ['--archive'],
                        'help': 'Path of the archive with a component to upload. '
                        'When not provided the component will be packed automatically.',
                    }, {
                        'names': ['--skip-pre-release'],
                        'help': 'Do not upload pre-release versions.',
                        'is_flag': True,
                        'default': False,
                    }, {
                        'names': ['--check-only'],
                        'help': 'Check if given component version is already uploaded and exit.',
                        'is_flag': True,
                        'default': False,
                    }, {
                        'names': ['--allow-existing'],
                        'help': 'Return success if existing version is already uploaded.',
                        'is_flag': True,
                        'default': False,
                    }
                ],
            },
            'delete-version': {
                'callback': callback,
                'deprecated': True,
                'help': (
                    'New CLI command: "compote component delete". '
                    'Delete specified version of the component from the component registry.'),
                'options': SERVICE_OPTIONS +
                [{
                    'names': ['--version'],
                    'help': 'Component version',
                    'required': True,
                }],
            },
            'upload-component-status': {
                'callback': callback,
                'deprecated': True,
                'help': (
                    'New CLI command: "compote component upload-status". '
                    'Check the component uploading status by the job ID.'),
                'options': SERVICE_PROFILE + [{
                    'names': ['--job'],
                    'help': 'Job ID',
                    'required': True,
                }],
            },
            'pack-component': {
                'callback': callback,
                'deprecated': True,
                'help': (
                    'New CLI command: "compote component pack". '
                    'Create component archive and store it in the dist directory.'),
                'options': SERVICE_PROFILE + NAME + VERSION_PARAMETER,
            },
            'create-project-from-example': {
                'callback': callback,
                'help': CREATE_PROJECT_FROM_EXAMPLE_DESCR,
                'arguments': [{
                    'names': ['example']
                }],
                'options': SERVICE_PROFILE + [
                    {
                        'names': ['-p', '--path'],
                        'help': (
                            'Set the path for the new project. The project '
                            'will be created directly in the given folder if it does not contain anything'),
                        'required': False,
                    }
                ],
            },
        },
    }
