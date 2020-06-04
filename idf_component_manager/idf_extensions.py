import sys

from component_management_tools.errors import FatalError

from .core import ComponentManager


def action_extensions(base_actions, project_path):
    def callback(subcommand_name, ctx, args, components=None):
        try:
            manager = ComponentManager(args.project_dir)
            getattr(manager, subcommand_name)(components)
        except FatalError as e:
            print(e)
            sys.exit(2)

    components_option = {
        'names': ['-c', '--components'],
        'help': 'Add new components to manifest',
        'multiple': True,
    }

    return {
        'actions': {
            'install': {
                'callback': callback,
                'help': 'Install dependencies.',
                'options': [components_option]
            },
        },
    }
