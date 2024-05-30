# Test Components

The components under this folder would be uploaded to the ESP Component Registry under namespace `test`. Would be used
for testing dependency scenarios.

## Scenarios

### Component hash doesn't match
`component_hash_with_exclude` generates a new file, `test_file`.
When the component manager attempts to compare hashes, it encounters an error indicating that the hashes do not match.
If the `idf_component.yml` file contains include/exclude blocks, the component manager calculates the hash using these filters,
effectively resolving the hash error.
