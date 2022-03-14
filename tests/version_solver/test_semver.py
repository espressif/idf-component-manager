import pytest

from idf_component_tools.semver import SimpleSpec, Version


@pytest.mark.parametrize(
    'spec, passed, failed', [
        ('^0.0.2-alpha2', [
            '0.0.2-beta',
            '0.0.2',
        ], [
            '0.0.1',
            '0.0.2-alaaa',
            '0.0.2-alpha',
            '0.0.3-pre',
            '0.0.3',
        ]),
        (
            '^0.2.3-beta', [
                '0.2.3-beta2',
                '0.2.3-rc',
                '0.2.4',
            ], [
                '0.2.3-alpha',
                '0.3.0-pre',
                '0.3.0',
                '1.0.0-pre',
                '1.0.0',
            ]),
        (
            '^1.2.3-rc', [
                '1.2.3-rc1',
                '1.2.3',
                '1.2.4',
                '1.3.0',
            ], [
                '1.2.3-alpha',
                '1.2.3-beta',
                '2.0.0-pre',
                '2.0.0',
            ])
    ])
def test_simple_spec_with_caret_and_prerelease(spec, passed, failed):
    version_spec = SimpleSpec(spec)
    for item in passed:
        assert version_spec.match(Version(item))

    for item in failed:
        assert not version_spec.match(Version(item))
