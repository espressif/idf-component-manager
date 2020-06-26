import sys

from idf_component_tools.errors import FatalError

from .core import ComponentManager


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
            'install-deps': {
                'callback': callback,
                'help': 'Download dependencies.',
            },
            'init-project': {
                'callback': callback,
                'help': "Create manifest in project's directory.",
            },
            'pack-component': {
                'callback': callback,
                'help': 'Create component archive.',
            },
            'upload-component': {
                'callback': callback,
                'help': 'Upload component in dist directory.',
                'dependencies': ['pack-component'],
                'options': [
                    {
                        'names': ['--namespace'],
                        'help': 'Namespace for the component. Can be set in config file.',
                        'envvar': 'IDF_COMPONENT_NAMESPACE',
                        'default': None,
                    },
                    {
                        'names': ['--service-profile'],
                        'help': 'Profile for component service to use.',
                        'envvar': 'IDF_COMPONENT_SERVICE_PROFILE',
                        'default': 'default',
                    },
                ]
            },
        },
    }
