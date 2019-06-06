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
        "help": "Installs the component from repository and updates manifest",
    },
    "eject": {
        "exec_without_components":
        False,
        "help":
        "Move component to unmanaged components directory and " + "add components dependencies to project's manifest",
    },
    "install": {
        "exec_without_components": True,
        "help": "Install all the dependencies listed within manifest in the local managed_components directory.",
    },
    "update": {
        "exec_without_components": True,
        "help": "Update components"
    },
    "prebuild": {
        "exec_without_components":
        True,
        "help":
        "Intended to be run as a first step of build process. " +
        "It checks installed components and generates CMake lists of dependencies.",
    },
}


def commands_help():
    help_descriptions = map(lambda key: "%s: %s" % (key, COMMANDS[key]["help"]), COMMANDS)
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

    parser.add_argument("--idf_path", help="Path to IDF", default=os.getenv("IDF_PATH"))

    parser.add_argument("--build_components", help="Override list of components to be built", default=[])

    parser.add_argument(
        "--common_components",
        help="Override list of components used in every project",
        default=[],
    )

    parser.add_argument(
        "--exclude_components",
        help="List of components that should be excluded from build",
        default=[],
    )

    parser.add_argument(
        "--component_directories",
        help="List of directories to search for components not managed by this tool",
        default=[],
    )

    # Tests
    parser.add_argument("--test_all", help="Test all components", default=False)

    parser.add_argument("--test_components", help="List of components to be tested", default=[])

    parser.add_argument(
        "--test_exclude_components",
        help="List of components that should be excluded from test build",
        default=[],
    )

    parser.add_argument("-D", "--debug", help="Run in debug mode", default=False)
    parser.add_argument("-t", "--target", help="Target platform", default=False)

    parser.add_argument(
        "--cmake_dependencies_file",
        help="Output path for CMake output (used by prebuild command)",
        default=[],
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
        raise ArgumentError("Command '%s' requires list of components to be provided" % command)
    elif command == "install" and components:
        raise ArgumentError("Command '%s' only installs components that are already in manifest. " % command +
                            "If you want to add components, please run `components.py add %s`" % " ".join(components))
    else:
        exec_command(command, components, os.getcwd())


def exec_command(command, components, path):
    manager = ComponentManager(path)
    handler = getattr(manager, command)
    if components:
        handler(components)
    elif (command in {cmd: features
                      for cmd, features in COMMANDS.items() if features["exec_without_components"]}.keys()):
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
