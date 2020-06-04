import sys

from component_management_tools.errors import FatalError

from .core import ComponentManager


def action_extensions(base_actions, project_path):
    def callback(subcommand_name, ctx, args, components=None):
        try:
            manager = ComponentManager(args.project_dir)
            getattr(manager, str(subcommand_name).replace('-', '_'))(components)
        except FatalError as e:
            print(e)
            sys.exit(2)

    return {
        'actions': {
            'install': {
                'callback': callback,
                'help': 'Install dependencies.',
            },
            'init-project': {
                'callback': callback,
                'help': "Creates manifest in project's directory.",
            },
        },
    }
