# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Tracking modifications of the managed components

### Changed

- Use bare repositories for caching components sourced from git
- `idf.py fullclean` command also delete unchanged dependency components from `managed_components` folder

### Fixed

- Delete unused components from the `managed_components` directory
- Fix include/exclude filters for nested paths in `idf_component.yml` manifest
- Update lock file if new version of the idf was detected
- Fix checkout error when depends on git source without `path`

## [1.0.1] 2022-01-12

### Fixed

- Fix relative path in manifest with a local component
- Fix the case when some dependencies don't have any versions
- Fix error message when the directory didn't find in a git repository
- Get the list of known targets from ESP-IDF, when possible

## [1.0.0] 2021-12-21

### Added

- Add version to CLI help
- Add . and + as allowed chars in component names
- Add tags block into manifest file
- Allow passing version during component upload
- Add esp32h2 and linux targets
- Add loading of version from git tag

### Fixed

- Fix possibility to use a branch as a git version
- Fix downloading dependencies from a git source
- Copy filtered paths for git source
- Fix local source missing dependencies

## [0.3.2-beta] - 2021-10-22
