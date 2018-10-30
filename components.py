#!/usr/bin/env python

from __future__ import print_function

import argparse
import os
import sys

from component_manager.core import ComponentManager


class ArgumentError(RuntimeError):
    pass


COMMANDS = {
    "add": {
        "exec_without_components": False,
        "help": "Installs the component from repository and updates manifest.yaml",
    },
    "eject": {
        "exec_without_components": False,
        "help": "Move component to unmanaged components directory and "
        + "add components dependencies to project's manifest.yaml",
    },
    "install": {
        "exec_without_components": True,
        "help": "Install all the dependencies listed within manifest.yaml in the local managed_components directory.",
    },
    "update": {"exec_without_components": True, "help": "Update components"},
}


def commands_help():
    help_descriptions = map(
        lambda key: "%s: %s" % (key, COMMANDS[key]["help"]), COMMANDS
    )
    return "\n".join(help_descriptions)


def build_parser():
    parser = argparse.ArgumentParser(
        description="components.py - ESP-IDF Component management command line tool",
        prog="components",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-p",
        "--path",
        help="Path to directory that contains manifest.yaml or path to manifest itself",
        default=os.getcwd(),
    )
    parser.add_argument(
        "command",
        help="Command to run\n" + commands_help(),
        nargs="?",
        choices=COMMANDS.keys(),
    )
    parser.add_argument("components", help="List of components", nargs="*")

    return parser


def parse_args(argv):
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command
    components = args.components

    if not command:
        parser.print_help()
    elif command in ["add", "eject"] and not components:
        raise ArgumentError(
            "Command '%s' requires list of components to be provided" % command
        )
    elif command == "install" and components:
        raise ArgumentError(
            "Command '%s' only installs components that are already in manifest. "
            % command
            + "If you want to add components, please run `components.py add %s`"
            % " ".join(components)
        )
    else:
        exec_command(command, components, args.path)


def exec_command(command, components, path):
    manager = ComponentManager(path)
    handler = getattr(manager, command)
    if components:
        handler(components)
    elif (
        command
        in {
            cmd: features
            for cmd, features in COMMANDS.items()
            if features["exec_without_components"]
        }.keys()
    ):
        handler()
    else:
        print("Do nothing, unknown command")


def main():
    parse_args(sys.argv[1:])


if __name__ == "__main__":
    try:
        main()
    except ArgumentError as e:
        print(e)
        sys.exit(2)
