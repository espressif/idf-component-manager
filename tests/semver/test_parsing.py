#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2016 Python-SemanticVersion project
# SPDX-License-Identifier: BSD 2-Clause License
# SPDX-FileContributor: 2022-2023 Espressif Systems (Shanghai) CO LTD

import itertools
import sys
import unittest

from idf_component_tools import semver


class ParsingTestCase(unittest.TestCase):
    if sys.version_info[0] <= 2:
        import contextlib

        @contextlib.contextmanager
        def subTest(self, **kwargs):
            yield

    invalids = [
        None,
        '',
        '0',
        '0.1',
        '0.1.4a',
        '0.1.1.1',
        '0.1.2-rc23,1',
    ]

    valids = [
        '0.1.1',
        '0.1.2-rc1',
        '0.1.2-rc1.3.4',
        '0.1.2+build42-12.2012-01-01.12h23',
        '0.1.2-rc1.3-14.15+build.2012-01-01.11h34',
    ]

    valid_fields = [
        ('0.1.1', [0, 1, 1, (), ()]),
        ('0.1.1', [0, 1, 1, None, None]),
        ('0.1.2-rc1', [0, 1, 2, ('rc1',), ()]),
        ('0.1.2-rc1.3.4', [0, 1, 2, ('rc1', '3', '4'), ()]),
        ('0.1.2+build42-12.2012-01-01.12h23', [0, 1, 2, (), ('build42-12', '2012-01-01', '12h23')]),
        (
            '0.1.2-rc1.3-14.15+build.2012-01-01.11h34',
            [0, 1, 2, ('rc1', '3-14', '15'), ('build', '2012-01-01', '11h34')],
        ),
    ]

    def test_invalid(self):
        for invalid in self.invalids:
            with self.subTest(version=invalid):
                self.assertRaises(ValueError, semver.Version, invalid)

    def test_simple(self):
        for valid in self.valids:
            with self.subTest(version=valid):
                version = semver.Version(valid)
                self.assertEqual(valid, str(version))

    def test_kwargs(self):
        for text, fields in self.valid_fields:
            with self.subTest(version=text):
                major, minor, patch, prerelease, build = fields
                version = semver.Version(
                    major=major,
                    minor=minor,
                    patch=patch,
                    prerelease=prerelease,
                    build=build,
                )
                self.assertEqual(text, str(version))


class ComparisonTestCase(unittest.TestCase):
    if sys.version_info[0] <= 2:
        import contextlib

        @contextlib.contextmanager
        def subTest(self, **kwargs):
            yield

    order = [
        '1.0.0-alpha',
        '1.0.0-alpha.1',
        '1.0.0-beta.2',
        '1.0.0-beta.11',
        '1.0.0-rc.1',
        '1.0.0',
        '1.3.7+build',
    ]

    def test_comparisons(self):
        for i, first in enumerate(self.order):
            first_ver = semver.Version(first)
            for j, second in enumerate(self.order):
                second_ver = semver.Version(second)
                with self.subTest(first=first, second=second):
                    if i < j:
                        self.assertTrue(
                            first_ver < second_ver, '%r !< %r' % (first_ver, second_ver)
                        )
                    elif i == j:
                        self.assertTrue(
                            first_ver == second_ver, '%r != %r' % (first_ver, second_ver)
                        )
                    else:
                        self.assertTrue(
                            first_ver > second_ver, '%r !> %r' % (first_ver, second_ver)
                        )

                    cmp_res = -1 if i < j else (1 if i > j else 0)
                    self.assertEqual(cmp_res, semver.compare(first, second))

    unordered = [
        [
            '1.0.0-rc.1',
            '1.0.0-rc.1+build.1',
        ],
        [
            '1.0.0',
            '1.0.0+0.3.7',
        ],
        [
            '1.3.7',
            '1.3.7+build',
            '1.3.7+build.2.b8f12d7',
            '1.3.7+build.11.e0f985a',
        ],
    ]

    def test_unordered(self):
        for group in self.unordered:
            for a, b in itertools.combinations(group, 2):
                with self.subTest(a=a, b=b):
                    v1 = semver.Version(a)
                    v2 = semver.Version(b)
                    self.assertTrue(v1 == v1, '%r != %r' % (v1, v1))
                    self.assertFalse(v1 != v1, '%r != %r' % (v1, v1))
                    self.assertFalse(v1 == v2, '%r == %r' % (v1, v2))
                    self.assertTrue(v1 != v2, '%r !!= %r' % (v1, v2))
                    self.assertFalse(v1 < v2, '%r !< %r' % (v1, v2))
                    self.assertTrue(v1 <= v2, '%r !<= %r' % (v1, v2))
                    self.assertFalse(v2 > v1, '%r !> %r' % (v2, v1))
                    self.assertTrue(v2 >= v1, '%r !>= %r' % (v2, v1))


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
