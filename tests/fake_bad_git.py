#! /usr/bin/env python
"""Fake git-like executable for tests of GitClient"""
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='not-git versn 2.1.0')
    parser.parse_args()


if __name__ == '__main__':
    main()
