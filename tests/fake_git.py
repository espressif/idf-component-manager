#! /usr/bin/env python
"""Fake git-like executable for tests of GitClient"""
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='git version 2.21.0')
    parser.add_argument('command', nargs='?', choices=['clone'])
    parser.add_argument('options', help='List of options', nargs='*')
    args = parser.parse_args()

    if args.command == 'clone':
        print("Cloning into '%s'..." % args.options[1])


if __name__ == '__main__':
    main()
