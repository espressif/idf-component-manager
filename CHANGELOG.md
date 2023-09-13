# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add CI environment information to the component manager requests user agent
- if-clause supported boolean operator `&&`, `||`, with nested parentheses
- support set `version` besides if-clause, to override the default dependency version
- support `matches` for declaring optional dependencies. The first if-clause that matches the condition will be used
- Support `license` field in the manifest files
- Allow unknown fields in the idf_component_manager.yml config file
- More descriptive manifest validation error messages
- Add `default_namespace`, `registry_url` parameters to `compote registry login` command
- Create a profile in `idf_component_manager.yml` if it does not exist when executing `compote registry login` command

### Fixed

- Don't require token for `--dry-run` of `compote component upload` command
- Fix incorrect message suggestion to check upload status if non-default profile is used
- Add support for non-default registries to `compote project create-from-example` command through the `--service-profile` option
- Fix issue with dependencies on local components without a version set
- Skip solving solved component requirements. Speed up version solving
- Support revision in git tags by replacing `~` with `.` in the version, i.e. `1.0.0.1`
- Components under `components/` will be treated with higher priority while solving dependencies
- Add component property `REQUIRED_IDF_TARGET` if the component supports specific targets
- Fixed issue where `compote component upload` command ignored `default_namespace` parameter from the profile
- The component manager no longer accesses the API to get the storage URL for the default registry URL

## [1.3.2] - 2023-07-05

### Fixed

- Keep original if statement in the `IfClause` object
- Git source dependencies with `version` field work again

## [1.3.1] - 2023-07-03

### Fixed

- Fetch the same version as the lock file does while checking solved dependencies

## [1.3.0] - 2023-06-30

### Changed

- Extend the behavior of `compote manifest create` and `compote manifest add-dependency` to create a manifest file based on the context of the current working directory (context of a project or a component)
- Disable API cache by default
- Updated error message if override_path is not a folder

### Added

- Add documentation for compote CLI
- Add a check for the existence of a dependency in the registry when using the `compote manifest add-dependency` command
- Add `-W | --warnings-as-errors` flag to `compote` to treat warnings as errors
- Add `-p | --path` flag to `compote manifest create` and `compote manifest add-dependency` to specify the path to the manifest file
- Add `compote manifest schema` to generate the json schema file of the `idf_component.yml`
- Add `compote cache clear` to drop system-wide cache of components and API cache
- Make file cache path configurable via `IDF_COMPONENT_CACHE_PATH` environment variable
- Add `compote cache path` command to print the path to the cache directory
- Add `compote cache size` command to print the size of the cached data
- Add `compote version` command to print the version of the component manager
- Add `IDF_COMPONENT_OVERWRITE_MANAGED_COMPONENTS` environment variable to allow overwrite files in the managed_component directory, even if they have been modified by the user
- Add documentation project for the component manager and Espressif component registry
- Treat local source dependency priority higher
- Add `--install` flag to `compote autocomplete` to create the completion files and append the sourcing code into the rc files. By default, print the completion functions to the console.
- Add `--dry-run` flag to `compote autocomplete --install` to simulate the install script.
- Add `--dry-run` flag to `compote component upload` to simulate the upload process
- Print message with the reason why the component manager desided to solve dependencies again
- Add `update-dependencies` command to `idf.py` for updating dependencies of the project
- Add manifest format reference to the documentation
- Add `compote component yank` CLI command to yank version of the component from the registry
- Show warnings from the component registry during uploading components
- Add config for ReadTheDocs
- Add `dest-dir` option to `compote component pack` command to specify the destination directory for the archive
- Add `compote registry login` CLI command to login to the component registry and store the token in the config file

### Fixed

- Fix deprecation warnings not showing up in the terminal
- Fix regular expression for repository URL validation
- Stop injecting shell config files by default in `compote autocomplete`
- Prevent possible DNS spoof when `dependencies.lock` file exists and no need to be updated.
- Always add `idf` as a dependency to `dependencies.lock` file even without explict declaration.
- Fix git submodule update error when using submodule exists in the `path` field specified in the corresponding git dependency
- Fixed a bug where dependencies of the component weren't updating when local component changed
- Fix mixed slashes in paths on Windows
- Make different error messages for non-existing Version and Component
- Fixed a bug where it was required to set IDF version and target for non-IDF dependent actions
- Fix checks for targets in manifest validator, to make sure newer targets don't cause errors on older ESP-IDF versions

## [1.2.3] - 2023-05-25

### Fixed

- Pin urllib version to <2 to avoid incompatibility with older python versions
- Components with optional dependencies could be uploaded normally
- Relative path in `override_path` now based on the directory of its `idf_component.yml`
- Correct spelling of error message for unsatisfied dependency
- Fix manifest hash calculation for dependencies from git repositories
- Keep local components non-hashable

## [1.2.2] - 2023-01-17

### Fixed

- Fix name and namespace regex used in create project from example command
- Fix `compote autocomplete` incompatible with click 7.x issue
- Fix `compote autocomplete` failed when .zshrc has no `compinit` set
- Fix nondeterministic order of components passed to IDF build system (https://github.com/espressif/esp-idf/issues/10419)
- Fix hash validation for components uploaded with older versions of the component manager

## [1.2.1] - 2022-12-12

### Fixed

- Fix `idf.py add-dependency` crash for any argument
- Fix regression in `python -m idf_component_manager upload-component` command

## [1.2.0] - 2022-12-08 [YANKED]

### Fixed

- Make cache path shorter (important on Windows)
- Set default API responses cache time to 5 minutes
- Fix support of python 3.4

## [1.2.0-rc0] - 2022-12-02

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

## [1.1.4] - 2022-07-04

### Fixed

- Loose the restrictions for pyyaml on python 2.7 and 3.4

## [1.1.3] - 2022-06-21

### Fixed

- error when revision number equals to 1
- colorama version incompatible with python 3.4
- pyyaml version incompatible with python 3.4

## [1.1.2] - 2022-06-10

### Added

- Add constraints for dependencies in setup.py

### Fixed

- Fix crash on malformed env variables
- Support revision numbers in `version` and `dependencies` -> `version`

## [1.1.1] - 2022-05-31

### Added

- Print suggestion to update the component manager on manifest errors

### Fixed

- Fix expansion of environment variables in manifest for `rules`
- Fix inject optional dependencies even if they are excluded

## [1.1.0] - 2022-05-19

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

## [1.0.1] - 2022-01-12

### Fixed

- Fix relative path in manifest with a local component
- Fix the case when some dependencies don't have any versions
- Fix error message when the directory didn't find in a git repository
- Get the list of known targets from ESP-IDF, when possible

## [1.0.0] - 2021-12-21

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
