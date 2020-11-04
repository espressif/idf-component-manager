import sys

from idf_component_tools.errors import FatalError

from .core import ComponentManager

SERVICE_OPTIONS = [
    {
        'names': ['--namespace'],
        'help': 'Namespace for the component. Can be set in config file.',
        'envvar': 'IDF_COMPONENT_NAMESPACE',
    },
    {
        'names': ['--service-profile'],
        'help': 'Profile for component service to use. By default profile named "default" will be used.',
        'envvar': 'IDF_COMPONENT_SERVICE_PROFILE',
    },
]


def action_extensions(base_actions, project_path):
    def callback(subcommand_name, ctx, args, **kwargs):
        try:
            manager = ComponentManager(args.project_dir)
            getattr(manager, str(subcommand_name).replace('-', '_'))(kwargs)
        except FatalError as e:
            print(e)
            sys.exit(2)

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
                'arguments': [
                    {
                        'names': ['name'],
                    },
                ],
                'options': SERVICE_OPTIONS,
            },
            'pack-component': {
                'callback': callback,
                'help': 'Create component archive.',
            },
            'upload-component': {
                'callback': callback,
                'help': 'Upload component in dist directory to the component service.',
                'dependencies': ['pack-component'],
                'options': SERVICE_OPTIONS
            },
        },
    }
