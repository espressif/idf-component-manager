#!/usr/bin/env python

from __future__ import print_function

import argparse
import sys

COMMANDS = {
    'install': "Install components described in components.yaml " +
    "and updates components-lock.yaml if necessary",
    'add': "Add new component to components.yaml, then install",
    'update': "Update components",
    'eject': "Move component to unmanaged components directory " +
    "and add components dependencies to project's components.yaml"
}


def parse_args(args):
    parser = argparse.ArgumentParser(
        description="components.py - ESP-IDF Component management command line tool", prog='components')
    parser.add_argument('command', help="Command to run", nargs='?', choices=COMMANDS.keys())
    parser.add_argument('components', help="List of components", nargs='*')

    return parser.parse_args(args)


def main():
    args = parse_args(sys.argv[1:])

    print(args)


if __name__ == "__main__":
    main()
