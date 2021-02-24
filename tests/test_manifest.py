from idf_component_tools.manifest import Manifest, ManifestValidator


def dep_by_name(manifest, name):
    for dependency in manifest.dependencies:
        if dependency.name == name:
            return dependency


def test_manifest_hash(valid_manifest, valid_manifest_hash):
    manifest = Manifest.fromdict(valid_manifest, name='test')
    assert manifest.manifest_hash == valid_manifest_hash


def test_project_manifest_builder(valid_manifest):
    manifest = Manifest.fromdict(valid_manifest, name='test')
    assert str(manifest.version) == '2.3.1'
    assert manifest.description == 'Test project'
    assert manifest.url == 'https://github.com/espressif/esp-idf'
    assert len(manifest.dependencies) == 7
    assert manifest.targets == ['esp32']
    test1 = dep_by_name(manifest, 'espressif/test-1')
    assert test1.version_spec == '^1.2.7'
    assert not test1.public
    test8 = dep_by_name(manifest, 'espressif/test-8')
    assert test8.public
    assert dep_by_name(manifest, 'espressif/test-2').version_spec == '*'
    assert dep_by_name(manifest, 'espressif/test-4').version_spec == '*'


def test_validator_broken_deps():
    manifest = {
        'dependencies': {
            'dep1': [],
            'dep2': 4
        },
    }
    errors = ManifestValidator(manifest).validate_normalize()
    assert len(errors) == 5


def test_validator_valid_manifest(valid_manifest):
    assert not ManifestValidator(valid_manifest).validate_normalize()
