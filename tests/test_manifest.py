from idf_component_tools.manifest import Manifest, ManifestValidator


def dep_by_name(manifest, name):
    for d in manifest.dependencies:
        if d.name == name:
            return d


def test_manifest_hash(valid_manifest, valid_manifest_hash):
    manifest = Manifest.fromdict(valid_manifest)
    assert manifest.manifest_hash == valid_manifest_hash


def test_project_manifest_builder(valid_manifest):
    manifest = Manifest.fromdict(valid_manifest)
    assert str(manifest.version) == '2.3.1'
    assert manifest.description == 'Test project'
    assert manifest.url == 'https://github.com/espressif/esp-idf'
    assert len(manifest.dependencies) == 7
    assert manifest.targets == ['esp32']
    assert dep_by_name(manifest, 'test-1').version_spec == '^1.2.7'
    assert dep_by_name(manifest, 'test-2').version_spec == '*'
    assert dep_by_name(manifest, 'test-4').version_spec == '*'


def test_validator_broken_deps():
    manifest = {
        'dependencies': {
            'dep1': [],
            'dep2': 4
        },
    }
    errors = ManifestValidator(manifest).validate_normalize()
    assert len(errors) == 2


def test_validator_valid_manifest(valid_manifest):
    assert not ManifestValidator(valid_manifest).validate_normalize()
