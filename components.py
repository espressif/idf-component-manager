#!/usr/bin/env python

from __future__ import print_function

import argparse

debug = False

COMMANDS = {
    'install': "Install components described in components.yaml and updates components-lock.yaml if necessary",
    'add': "Add new component to components.yaml, then install",
    'update': "Update components",
    'eject': "Move component to unmanaged components directory and add components dependencies to project's components.yaml"
}


def main():
    global debug

    parser = argparse.ArgumentParser(
        description='components.py - ESP-IDF Component management command line utility', prog='components')

    parser.add_argument('--debug', help='Display debugging output', action='store_true')

    parser.add_argument('command', help="Command to run", nargs='?',
                        choices=COMMANDS.keys())

    args = parser.parse_args()
    debug = args.debug


if __name__ == "__main__":
    main()
