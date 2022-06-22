#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2016 Python-SemanticVersion project
# SPDX-License-Identifier: BSD 2-Clause License
# SPDX-FileContributor: 2022 Espressif Systems (Shanghai) CO LTD

import sys
import unittest

from idf_component_tools import semver


class MatchTestCase(unittest.TestCase):
    if sys.version_info[0] <= 2:
        import contextlib

        @contextlib.contextmanager
        def subTest(self, **kwargs):
            yield

    invalid_specs = [
        '',
        '!0.1',
        '<=0.1.4a',
        '>0.1.1.1',
        '<0.1.2-rc1.3-14.15+build.2012-01-01.11h34',
        '==0.0~2',
        '>0.1~2',
        '~=1~1',
    ]

    valid_specs = [
        '*',
        '==0.1.0',
        '=0.1.0',
        '0.1.0',
        '<=0.1.1',
        '<0.1',
        '1',
        '>0.1.2-rc1',
        '>=0.1.2-rc1.3.4',
        '==0.1.2+build42-12.2012-01-01.12h23',
        '!=0.1.2-rc1.3-14.15+build.2012-01-01.11h34',
        '^0.1.2',
        '~0.1.2',
        '~=0.1.2',
    ]

    matches = {
        '*': [
            '0.1.1',
            '0.1.1+build4.5',
            '0.1.2-rc1',
            '0.1.2-rc1.3',
            '0.1.2-rc1.3.4',
            '0.1.2+build42-12.2012-01-01.12h23',
            '0.1.2-rc1.3-14.15+build.2012-01-01.11h34',
            '0.2.0',
            '1.0.0~2',
            '1.0.0~1-alpha.2',
            '1.0.0',
        ],
        '==0.1.2': [
            '0.1.2+build42-12.2012-01-01.12h23',
        ],
        '==0.1.2~2': [
            '0.1.2~2',
        ],
        '=0.1.2': [
            '0.1.2+build42-12.2012-01-01.12h23',
        ],
        '0.1.2': [
            '0.1.2+build42-12.2012-01-01.12h23',
        ],
        '<=0.1.2': [
            '0.1.1',
            '0.1.1~2',
            '0.1.2-rc1',
            '0.1.2-rc1.3.4',
            '0.1.2',
            '0.1.2+build4',
        ],
        '<=0.1.2~3': [
            '0.1.1',
            '0.1.1~2',
            '0.1.2',
            '0.1.2~2',
            '0.1.2~3',
        ],
        '>=0.1.2~3': [
            '0.1.2~3',
            '0.1.2~4',
            '0.1.3',
        ],
        '!=0.1.2+': [
            '0.1.2+1',
            '0.1.2~2',
            '0.1.2-rc1',
        ],
        '!=0.1.2-': [
            '0.1.1',
            '0.1.2~2',
            '0.1.2-rc1',
        ],
        '!=0.1.2+345': [
            '0.1.1',
            '0.1.1~2+345',
            '0.1.2-rc1+345',
            '0.1.2+346',
            '0.2.3+345',
        ],
        '>=0.1.1': [
            '0.1.1',
            '0.1.1~2',
            '0.1.1+build4.5',
            '0.1.2-rc1.3',
            '0.2.0',
            '1.0.0',
        ],
        '>0.1.1': [
            '0.1.2~2',
            '0.1.2+build4.5',
            '0.1.2-rc1.3',
            '0.2.0',
            '1.0.0',
        ],
        '<0.1.1-': [
            '0.1.1-alpha',
            '0.1.1-rc4',
            '0.1.0+12.3',
        ],
        '^0.1.2': [
            '0.1.2',
            '0.1.2~2',
            '0.1.2+build4.5',
            '0.1.3-rc1.3',
            '0.1.4',
        ],
        '~0.1.2': [
            '0.1.2',
            '0.1.2~2',
            '0.1.2+build4.5',
            '0.1.3-rc1.3',
        ],
        '~=1.4.5': (
            '1.4.5',
            '1.4.8~2',
            '1.4.10-alpha',
            '1.4.10',
        ),
        '~=1.4': [
            '1.4.0',
            '1.4.0~2',
            '1.6.10-alpha',
            '1.6.10',
        ],
    }

    def test_invalid(self):
        for invalid in self.invalid_specs:
            with self.subTest(spec=invalid):
                with self.assertRaises(ValueError, msg='Spec(%r) should be invalid' % invalid):
                    semver.SimpleSpec(invalid)

    def test_simple(self):
        for valid in self.valid_specs:
            with self.subTest(spec=valid):
                spec = semver.SimpleSpec(valid)
                normalized = str(spec)
                self.assertEqual(spec, semver.SimpleSpec(normalized))

    def test_match(self):
        for spec_text, versions in self.matches.items():
            for version_text in versions:
                with self.subTest(spec=spec_text, version=version_text):
                    spec = semver.SimpleSpec(spec_text)
                    self.assertNotEqual(spec, spec_text)
                    version = semver.Version(version_text)
                    self.assertIn(version, spec)
                    self.assertTrue(spec.match(version), '%r does not match %r' % (version, spec))
                    self.assertTrue(semver.match(spec_text, version_text))

    def test_contains(self):
        spec = semver.SimpleSpec('<=0.1.1')
        self.assertFalse('0.1.0' in spec, '0.1.0 should not be in %r' % spec)

        version = semver.Version('0.1.1+4.2')
        self.assertTrue(version in spec, '%r should be in %r' % (version, spec))

        version = semver.Version('0.1.1-rc1+4.2')
        self.assertTrue(version in spec, '%r should be in %r' % (version, spec))

    def test_prerelease_check(self):
        strict_spec = semver.SimpleSpec('>=0.1.1-')
        lax_spec = semver.SimpleSpec('>=0.1.1')
        version = semver.Version('0.1.1-rc1+4.2')
        self.assertFalse(version in lax_spec, '%r should not be in %r' % (version, lax_spec))
        self.assertFalse(version in strict_spec, '%r should not be in %r' % (version, strict_spec))

    def test_build_check(self):
        spec = semver.SimpleSpec('<=0.1.1-rc1')
        version = semver.Version('0.1.1-rc1+4.2')
        self.assertTrue(version in spec, '%r should be in %r' % (version, spec))


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
