#! /usr/bin/env python
#
# SPDX-FileCopyrightText: 2022 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Fake git-like executable for tests of GitClient"""

import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='not-git versn 2.1.0')
    parser.parse_args()


if __name__ == '__main__':
    main()
