import sys

from idf_component_tools.errors import FatalError

from .core import ComponentManager

try:
    from typing import Any, Dict, List
except ImportError:
    pass

SERVICE_PROFILE = [
    {
        'names': ['--service-profile'],
        'help': 'Profile for component service to use. By default profile named "default" will be used.',
        'envvar': 'IDF_COMPONENT_SERVICE_PROFILE',
    },
]  # type: List[Dict[str, Any]]

SERVICE_OPTIONS = SERVICE_PROFILE + [
    {
        'names': ['--name'],
        'help': 'Component name',
        'required': True,
    },
    {
        'names': ['--namespace'],
        'help': 'Namespace for the component. Can be set in config file.',
        'envvar': 'IDF_COMPONENT_NAMESPACE',
    },
]  # type: List[Dict[str, Any]]


def action_extensions(base_actions, project_path):
    def callback(subcommand_name, ctx, args, **kwargs):
        try:
            manager = ComponentManager(args.project_dir)
            getattr(manager, str(subcommand_name).replace('-', '_'))(kwargs)
        except FatalError as e:
            print(e)
            sys.exit(e.exit_code)

    return {
        'actions': {
            'create-manifest': {
                'callback': callback,
                'help': "Create manifest for project's main component.",
            },
            'create-remote-component': {
                'callback': callback,
                'help': ('Register a new component on the component service.\n\n'
                         'NAME\tname of the component.'),
                'options': SERVICE_OPTIONS,
            },
            'upload-component': {
                'callback': callback,
                'help': 'Upload component in dist directory to the component service.',
                'options': SERVICE_OPTIONS + [{
                    'names': ['--archive'],
                    'help': 'Pass an archive to for upload',
                }],
            },
            'delete-version': {
                'callback': callback,
                'help': 'Delete version in dist directory from the component service.',
                'options': SERVICE_OPTIONS + [{
                    'names': ['--version'],
                    'help': 'Component version',
                    'required': True,
                }],
            },
            'upload-component-status': {
                'callback': callback,
                'help': 'Check status of component upload',
                'options': SERVICE_PROFILE + [{
                    'names': ['--job'],
                    'help': 'Job ID',
                    'required': True,
                }],
            },
            'pack-component': {
                'callback': callback,
                'help': 'Create component archive.',
                'options': SERVICE_OPTIONS,
            },
        },
    }
