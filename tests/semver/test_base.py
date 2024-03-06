#!/usr/bin/env python
# SPDX-FileCopyrightText: 2016 Python-SemanticVersion project
# SPDX-License-Identifier: BSD 2-Clause License
# SPDX-FileContributor: 2022-2024 Espressif Systems (Shanghai) CO LTD
"""Test the various functions from 'base'."""

import sys
import unittest

from idf_component_tools.semver import base


class TopLevelTestCase(unittest.TestCase):
    """Test module-level functions."""

    if sys.version_info[0] <= 2:
        import contextlib

        @contextlib.contextmanager
        def subTest(self, **kwargs):
            yield

    versions = (
        ('0.1.0', '0.1.1', -1),
        ('0.1.1', '0.1.1', 0),
        ('0.1.1', '0.1.0', 1),
        ('0.1.1~1', '0.1.2', -1),
        ('0.1.1~1', '0.1.0', 1),
        ('0.1.1~1', '0.1.1~2', -1),
        ('0.1.0~2-alpha', '0.1.0~1', 1),
        ('0.1.0-alpha', '0.1.0', -1),
        ('0.1.0-alpha+2', '0.1.0-alpha', NotImplemented),
    )

    def test_compare(self):
        for a, b, expected in self.versions:
            with self.subTest(a=a, b=b):
                result = base.compare(a, b)
                self.assertEqual(
                    expected,
                    result,
                    'compare({!r}, {!r}) should be {!r} instead of {!r}'.format(
                        a, b, expected, result
                    ),
                )

    matches = (
        ('>=0.1.1', '0.1.2'),
        ('>=0.1.1', '0.1.1'),
        ('>=0.1.1', '0.1.2-alpha'),
        ('>=0.1.1', '0.1.2~1-alpha'),
        ('>=0.1.1,!=0.2.0', '0.2.1'),
    )

    def test_match(self):
        for spec, version in self.matches:
            with self.subTest(spec=spec, version=version):
                self.assertTrue(
                    base.match(spec, version), '{!r} should accept {!r}'.format(spec, version)
                )

    valid_strings = (
        '1.0.0-alpha',
        '1.0.0-alpha.1',
        '1.0.0-beta.2',
        '1.0.0-beta.11',
        '1.0.0~1-beta+build999',
        '1.0.0-rc.1',
        '1.0.0-rc.1+build.1',
        '1.0.0',
        '1.0.0~999',
        '1.0.0+0.3.7',
        '1.3.7+build',
        '1.3.7+build.2.b8f12d7',
        '1.3.7+build.11.e0f985a',
        '1.1.1',
        '1.1.2',
        '1.1.3-rc4.5',
        '1.1.3~20-rc4.5',
        '1.1.3-rc42.3-14-15.24+build.2012-04-13.223',
        '1.1.3+build.2012-04-13.HUY.alpha-12.1',
    )

    def test_validate_valid(self):
        for version in self.valid_strings:
            with self.subTest(version=version):
                self.assertTrue(
                    base.validate(version), '{!r} should be a valid version'.format(version)
                )

    invalid_strings = (
        '1',
        'v1',
        '1.2.3.4',
        '1.2.3~a',
        '1.2.3~-0',
        '1.2',
        '1.2a3',
        '1.2.3a4',
        'v12.34.5',
        '1.2.3+4+5',
    )

    def test_validate_invalid(self):
        for version in self.invalid_strings:
            with self.subTest(version=version):
                self.assertFalse(
                    base.validate(version), '{!r} should not be a valid version'.format(version)
                )


class VersionTestCase(unittest.TestCase):
    if sys.version_info[0] <= 2:
        import contextlib

        @contextlib.contextmanager
        def subTest(self, **kwargs):
            yield

    versions = {
        '1.0.0-alpha': (1, 0, 0, 0, ('alpha',), ()),
        '1.0.0-alpha.1': (1, 0, 0, 0, ('alpha', '1'), ()),
        '1.0.0-beta.2': (1, 0, 0, 0, ('beta', '2'), ()),
        '1.0.0-beta.11': (1, 0, 0, 0, ('beta', '11'), ()),
        '1.0.0-rc.1': (1, 0, 0, 0, ('rc', '1'), ()),
        '1.0.0-rc.1+build.1': (1, 0, 0, 0, ('rc', '1'), ('build', '1')),
        '1.0.0': (1, 0, 0, 0, (), ()),
        '1.0.0~1': (1, 0, 0, 1, (), ()),
        '1.0.0~99': (1, 0, 0, 99, (), ()),
        '1.0.0+0.3.7': (1, 0, 0, 0, (), ('0', '3', '7')),
        '1.3.7+build': (1, 3, 7, 0, (), ('build',)),
        '1.3.7+build.2.b8f12d7': (1, 3, 7, 0, (), ('build', '2', 'b8f12d7')),
        '1.3.7+build.11.e0f985a': (1, 3, 7, 0, (), ('build', '11', 'e0f985a')),
        '1.1.1': (1, 1, 1, 0, (), ()),
        '1.1.2': (1, 1, 2, 0, (), ()),
        '1.1.3-rc4.5': (1, 1, 3, 0, ('rc4', '5'), ()),
        '1.1.3~2-rc4+build99': (1, 1, 3, 2, ('rc4',), ('build99',)),
        '1.1.3-rc42.3-14-15.24+build.2012-04-13.223': (
            1,
            1,
            3,
            0,
            ('rc42', '3-14-15', '24'),
            ('build', '2012-04-13', '223'),
        ),
        '1.1.3+build.2012-04-13.HUY.alpha-12.1': (
            1,
            1,
            3,
            0,
            (),
            ('build', '2012-04-13', 'HUY', 'alpha-12', '1'),
        ),
    }

    def test_parsing(self):
        for text, expected_fields in self.versions.items():
            with self.subTest(text=text):
                version = base.Version(text)
                actual_fields = (
                    version.major,
                    version.minor,
                    version.patch,
                    version.revision,
                    version.prerelease,
                    version.build,
                )
                self.assertEqual(expected_fields, actual_fields)

    def test_str(self):
        for text in self.versions:
            with self.subTest(text=text):
                version = base.Version(text)
                self.assertEqual(text, str(version))
                self.assertEqual(
                    "Version('%s', revision=%d)" % (text, version.revision), repr(version)
                )

    def test_compare_to_self(self):
        for text in self.versions:
            with self.subTest(text=text):
                self.assertEqual(base.Version(text), base.Version(text))
                self.assertNotEqual(text, base.Version(text))

    def test_hash(self):
        self.assertEqual(1, len({base.Version('0.1.0'), base.Version('0.1.0')}))
        self.assertEqual(1, len({base.Version('0.1.0'), base.Version('0.1.0~0')}))
        self.assertEqual(1, len({base.Version('0.1.0~2'), base.Version('0.1.0~2')}))

    @unittest.skipIf(sys.version_info[0] <= 2, "Comparisons don't raise TypeError in Python 2")
    def test_invalid_comparisons(self):
        v = base.Version('0.1.0')
        with self.assertRaises(TypeError):
            v < '0.1.0'
        with self.assertRaises(TypeError):
            v <= '0.1.0'
        with self.assertRaises(TypeError):
            v > '0.1.0'
        with self.assertRaises(TypeError):
            v >= '0.1.0'

        self.assertTrue(v != '0.1.0')
        self.assertFalse(v == '0.1.0')

    def test_bump_clean_versions(self):
        # We Test each property explicitly as the == comparator for versions
        # does not distinguish between prerelease or builds for equality.

        v = base.Version('1.0.0+build')
        v = v.next_major()
        self.assertEqual(v.major, 2)
        self.assertEqual(v.minor, 0)
        self.assertEqual(v.patch, 0)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.0.0+build')
        v = v.next_minor()
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 1)
        self.assertEqual(v.patch, 0)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.0.0+build')
        v = v.next_patch()
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 0)
        self.assertEqual(v.patch, 1)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.1.0+build')
        v = v.next_major()
        self.assertEqual(v.major, 2)
        self.assertEqual(v.minor, 0)
        self.assertEqual(v.patch, 0)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.1.0+build')
        v = v.next_minor()
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 2)
        self.assertEqual(v.patch, 0)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.1.0+build')
        v = v.next_patch()
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 1)
        self.assertEqual(v.patch, 1)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.0.1+build')
        v = v.next_major()
        self.assertEqual(v.major, 2)
        self.assertEqual(v.minor, 0)
        self.assertEqual(v.patch, 0)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.0.1+build')
        v = v.next_minor()
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 1)
        self.assertEqual(v.patch, 0)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.0.1+build')
        v = v.next_patch()
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 0)
        self.assertEqual(v.patch, 2)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

    def test_bump_prerelease_versions(self):
        # We Test each property explicitly as the == comparator for versions
        # does not distinguish between prerelease or builds for equality.

        v = base.Version('1.0.0-pre+build')
        v = v.next_major()
        self.assertEqual(v.major, 2)
        self.assertEqual(v.minor, 0)
        self.assertEqual(v.patch, 0)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.0.0-pre+build')
        v = v.next_minor()
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 1)
        self.assertEqual(v.patch, 0)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.0.0-pre+build')
        v = v.next_patch()
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 0)
        self.assertEqual(v.patch, 1)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.1.0-pre+build')
        v = v.next_major()
        self.assertEqual(v.major, 2)
        self.assertEqual(v.minor, 0)
        self.assertEqual(v.patch, 0)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.1.0-pre+build')
        v = v.next_minor()
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 2)
        self.assertEqual(v.patch, 0)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.1.0-pre+build')
        v = v.next_patch()
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 1)
        self.assertEqual(v.patch, 1)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.0.1-pre+build')
        v = v.next_major()
        self.assertEqual(v.major, 2)
        self.assertEqual(v.minor, 0)
        self.assertEqual(v.patch, 0)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.0.1-pre+build')
        v = v.next_minor()
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 1)
        self.assertEqual(v.patch, 0)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())

        v = base.Version('1.0.1-pre+build')
        v = v.next_patch()
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 0)
        self.assertEqual(v.patch, 2)
        self.assertEqual(v.revision, 0)
        self.assertEqual(v.prerelease, ())
        self.assertEqual(v.build, ())


class CoerceTestCase(unittest.TestCase):
    if sys.version_info[0] <= 2:
        import contextlib

        @contextlib.contextmanager
        def subTest(self, **kwargs):
            yield

    examples = {
        # Dict of target: [list of equivalents]
        '0.0.0': ('0', '0.0', '0.0.0', '0.0.0+', '0-', '0~'),
        '0.1.0': ('0.1', '0.1+', '0.1-', '0.1~', '0.1.0', '0.01.0', '000.0001.0000000000'),
        '0.1.0+2': ('0.1.0+2', '0.1.0.2', '0.1~1+2'),
        '0.1.0+2.3.4': ('0.1.0+2.3.4', '0.1.0+2+3+4', '0.1.0~1+2+3+4', '0.1.0.2+3+4'),
        '0.1.0+2-3.4': (
            '0.1.0+2-3.4',
            '0.1.0+2-3+4',
            '0.1.0~1+2-3+4',
            '0.1.0.2-3+4',
            '0.1.0.2_3+4',
        ),
        '0.1.0-a2.3': ('0.1.0-a2.3', '0.1.0a2.3', '0.1.0~1_a2.3', '0.1.0_a2.3'),
        '0.1.0-a2.3+4.5-6': (
            '0.1.0-a2.3+4.5-6',
            '0.1.0a2.3+4.5-6',
            '0.1.0a2.3+4.5_6',
            '0.1.0~1a2.3+4.5_6',
            '0.1.0a2.3+4+5/6',
        ),
    }

    def test_coerce(self):
        for equivalent, samples in self.examples.items():
            target = base.Version(equivalent)
            for sample in samples:
                with self.subTest(target=equivalent, sample=sample):
                    v_sample = base.Version.coerce(sample)
                    self.assertEqual(target, v_sample)

    def test_invalid(self):
        self.assertRaises(ValueError, base.Version.coerce, 'v1')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
