# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Pin urllib version to <2 to avoid incompatibility with older python versions

## [1.2.2] 2023-01-17

### Fixed

- Fix name and namespace regex used in create project from example command
- Fix `compote autocomplete` incompatible with click 7.x issue
- Fix `compote autocomplete` failed when .zshrc has no `compinit` set
- Fix nondeterministic order of components passed to IDF build system (https://github.com/espressif/esp-idf/issues/10419)
- Fix hash validation for components uploaded with older versions of the component manager

## [1.2.1] 2022-12-12

### Fixed

- Fix `idf.py add-dependency` crash for any argument
- Fix regression in `python -m idf_component_manager upload-component` command

## [1.2.0] 2022-12-08 [YANKED]

### Fixed

- Make cache path shorter (important on Windows)
- Set default API responses cache time to 5 minutes
- Fix support of python 3.4

## [1.2.0-rc0] 2022-12-02

### Added

- Add the `repository`, `documentation`, `issues`, and `discussion` fields for the URLs in the root of the manifest
- Cache request to the API component registry
- Add `require` field for dependencies. Add possibility to download dependencies without building them.
- Default revision number change from 1 to 0
- Warn users when the `override_path` point to a non-component directory
- Load component details from pre-rendered JSON files from the static endpoint
- Use local file system like `file://` as a Component storage URL
- Record managed component version in component property `COMPONENT_VERSION`
- Disable API interaction if only storage URL is set
- Add warnings for build files in component version archives
- Add hints for user printed to stderr
- New CLI: compote
- Add `create-project-from-example` command to the `idf.py`
- Add the `pre_release` flag for the dependency to control downloads of pre-release versions
- Print a note with the list of alternative targets when the solver cannot find a suitable component version for the current target but there are some candidates for other targets.
- Add the `examples` field for the custom examples paths
- Add new environment variables `IDF_COMPONENT_REGISTRY_URL` and `IDF_COMPONENT_REGISTRY_PROFILE` for configuring the component manager
- Exclude build artefacts from the examples

### Fixed

- Hide stack trace after solver dependency error
- Fix packing archives with version from git tag
- Validate case-insensitive duplicate items in the manifest file
- Provide better error message when no network connection
- Improve the error message when failed to solve the dependencies specified in manifest files
- Fix crash on use of local components and `override_path` for namespaced components
- Mixing stdout and stderr of git command
- Dump manifest file inconsistency with escaped dollar sign
- Fix schema validation of the `idf_component_manager.yml` config file

## [1.1.4] 2022-07-04

### Fixed

- Loose the restrictions for pyyaml on python 2.7 and 3.4

## [1.1.3] 2022-06-21

### Fixed

- error when revision number equals to 1
- colorama version incompatible with python 3.4
- pyyaml version incompatible with python 3.4

## [1.1.2] 2022-06-10

### Added

- Add constraints for dependencies in setup.py

### Fixed

- Fix crash on malformed env variables
- Support revision numbers in `version` and `dependencies` -> `version`

## [1.1.1] 2022-05-31

### Added

- Print suggestion to update the component manager on manifest errors

### Fixed

- Fix expansion of environment variables in manifest for `rules`
- Fix inject optional dependencies even if they are excluded

## [1.1.0] 2022-05-19

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
