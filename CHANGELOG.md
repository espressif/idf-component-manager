# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Tracking modifications of the managed components
- Add CLI method to create a project from a component's example
- Print a warning when the name of the local component doesn't match the directory name.
- Optional dependencies for the `idf_component.yml` based on two keywords, `idf_version` and `target`.
  `idf_version` supports all [`SimpleSpec`](https://python-semanticversion.readthedocs.io/en/latest/reference.html#semantic_version.SimpleSpec) grammar,
  and `target` supports `==`, `!=`, `in`, `not in`.
- Revision number support in component manifest file
- Add `override_path` field for dependencies. Add possibility to change component from component
  registry to the local one. Can be used for examples of the component to change that component to the local one.
- Support environment variables in `idf_component.yml` yaml values.
  Substrings of the form `$name` or `${name}` are replaced by the value of environment variable name.
- Send custom User-Agent with client version to registry API
- Add OS, platform and python version to API client user agent
- Provide list of managed components to ESP-IDF build system

### Changed

- Use bare repositories for caching components sourced from git
- `idf.py fullclean` command also delete unchanged dependency components from `managed_components` folder
- Printing information about selected profile using `--service-profile` flag, error message if profile didn't find in idf_component_manager.yml file
- Printing warnings and errors to stderr

### Fixed

- Fix use of project's components with higher priority than ones delivered by the component manager
- Delete unused components from the `managed_components` directory
- Fix include/exclude filters for nested paths in `idf_component.yml` manifest
- Update lock file if new version of the idf was detected
- Fix checkout error when depends on git source without `path`
- Fix solve version error when using local components with git source.
- Fix solve version error when using caret (`^`) with prerelease version
- Fix relative path in the manifest for local components
- Fix bug with the progress bar during uploading components
- Fix error messages when there's self-dependent package during version solving
- Fix support of REQUIRES by the project's main component
- Allow transient dependencies for the main component

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
