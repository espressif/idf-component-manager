# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This changelog is managed with commitizen tool, don't update it manually.

## v2.4.6 (2026-01-22)

### Fix

- Merge results from multiple --component flags in registry sync
- Profile argument validation

## v2.4.5 (2026-01-16)

### Fix

- kconfig build system for CMake v2
- pin docutils\<0.22 to keep sphinx-tabs compatibility
- Getting parent CMake process PPID on Windows

## v2.4.4 (2026-01-12)

### Fix

- Clear build component targets during Kconfig retry
- Lock tests - wrapping long strings in yaml
- WebSource components pulled in when local available

## v2.4.3 (2025-12-01)

### Feat

- improve solver errors

### Fix

- Kconfig build system
- Add esp32s31 to default known targets
- Kconfig not showing message on unsupported ESP-IDF
- empty name directory in archive
- Take sdkconfig.json from known location instead injecting from CMake
- **tests**: integration tests issues
- **kconfig**: transitive dependencies incorrect source on second CMake run
- handle malformed JSON in API responses

## v2.4.2 (2025-10-20)

### Fix

- Local dependency hash key equivalence

## v2.4.1 (2025-10-08)

### Fix

- Do not install pydantic 2.12.0 as dependency due to bug
- remove deprecated `click.__version__`

## v2.4.0 (2025-09-15)

### Feat

- support idf root deps, handle it in idf build system
- support constraint file

### Fix

- Error message regex in yank test

## v2.3.0 (2025-08-13)

### Feat

- add service profile as global option to idf.py
- add `--registry-url` and `--storage-url` params to idf.py
- add IDF_COMPONENT_LOCAL_STORAGE_URL env variable
- add function to validate url or file in cli
- add `--local-storage-url` param to idf.py
- use pydantic types for validation
- read env variables in ProfileItem
- create mermaid workflow diagrams
- Add optional path to ChecksumsManager dump method

### Fix

- cache message about skipped dependency
- better error message when manifest validation failed
- Allow to delete a yanked version
- Cassette when yanking
- Minor documentation fix
- ignore if clauses with kconfig options with unsupported idf version
- catch all MissingKconfigError exception
- fix checking max name length

### Refactor

- reformat all rst files using docstrfmt

## v2.2.2 (2025-06-12)

### Feat

- Better report for corrupted component error message

### Fix

- fix versions case sensitivity
- use `ComponentRequirements` in set
- Do not duplicate examples defined in the manifest when packing multiple times
- idf version regex supports >10
- root-level managed components folder path

## v2.2.1 (2025-06-04)

### Fix

- file existence check during checksums validation

## v2.2.0 (2025-06-02)

### Feat

- **cli**: add commands to edit config
- improve kconfig item debug message
- use cmake syntax to represent kconfig option $CONFIG{...}
- Upload examples defined in manifest separately
- download component files hash from registry
- rewrite validate functions
- add util functions to create and parse file with checksums
- remove checksum validation in fetcher
- move logic from source to fetcher
- create checksums manager class
- download checksums json during component sync from registry
- improve if parser, support int, bool, string
- support kconfig items as if clause left value
- Use include/exclude file filters with .gitiignore
- Use system TLS certificate store when available (py3.10 or newer)
- add esp32h4 known target
- Remove responsibility for checking version existance when yanking
- Add option to run network tests against the real environment

### Fix

- **cli**: Fix config unset command
- convert component name to lower case
- rename idf_component_tools tests folder
- fix downloading local component
- check if component cache folder exists in overwrite mode
- adjust test to handle breaking change of stdout and stderr behaviour in click 8.2.0
- use env var REGISTRY_URL and PROFILE for deps without registry_url set
- skip calling `/api` when unnecessary
- Fix hardcoded values to variables
- Skipped asserts in help tests

### Refactor

- migrate to ruamel yaml
- improve grammar and clarity in documentation and code comments

## v2.1.2 (2025-01-10)

### Fix

- keep comments in config YAML with ruamel.yaml
- Limit urllib3 version for tests
- Always use canonical representation of the component version

## v2.1.1 (2024-12-06)

### Fix

- Do not expand environment variables when validating example manifests
- Disable caching of task status endpoint

## v2.1.0 (2024-12-05)

### Feat

- **cli**: add validations for CLI options
- Get all information about Forbidden error from the server
- set local_storage_url as breaking change from 1.x to 2.x
- support `compote registry sync --resolution [all,latest]`
- Add in-memory cache for API and storage requests
- add debug logging for HTTP requests
- add esp32h21 to known target list
- Add ruamel.yaml dependency
- Improve add-dependency output and help
- Add an option to specify registry url when using add-dependency
- Add git source to add-dependency command
- increase HTTP timeouts, use custom timeout for uploads
- Add support of `.gitignore` file while uploading / packaging component
- Add `use_gitignore` option to the manifest
- validate manifest of examples when uploading a component

### Fix

- hash value of ComponentRequirement for register_url
- compote registry sync keep same folder structure as the registry
- Fix caching during uploading of components
- default storage url without fetching from registry
- only show debug hints when version solver failed
- unify 1.x 2.x generated parital sync metatdata file
- accept registry_url from api
- Use utf-8 encoding for all text file operations
- recreate lock file when missing env var
- drop current solution if requirement source is different
- ignore local storage urls when generating partial mirror

### Refactor

- rewrite partial mirror sync
- use logging module instead of warnings

## v2.0.4 (2024-10-01)

### Fix

- accept registry_url from api
- increase HTTP timeouts, use custom timeout for uploads
- recreate lock file when missing env var
- drop current solution if requirement source is different
- ignore local storage urls when generating partial mirror
- Use utf-8 encoding for all text file operations

## v2.0.3 (2024-08-26)

### Fix

- get_storage_client includes component registry_url
- wrong root_managed_components_lock_path
- Fix applying include / exclude lists in GitSource versions method
- Exclude custom dest_dir from component archive

### Refactor

- Refactor core.py, change os.path to pathlib.Path

## v2.0.2 (2024-08-21)

### Fix

- dependency with registry_url unrecognized correctly

## v2.0.1 (2024-08-15)

### Fix

- Fix filtering of files with default exclude filter patterns
- filterwarning "Running in an environment without IDF" while uploading

## v2.0.0 (2024-08-12)

### Feat

- drop support of root level `commit_sha` in the manifest file
- Add more descriptive error message for authentication
- compare .component_hash by default, support optionally strict checksum
- Make environment variables in if rules required to have a value
- Revoke token on logout CLI command
- Use compote CLI when executed as module
- support debug mode by setting env var IDF_COMPONENT_MANAGER_DEBUG_MODE
- use current solution while changing target or idf version if it works
- Drop support of Python 2.7
- remove redundant option --namespace from component pack CLI

### Fix

- pack and upload components without manifests
- Fix login command with non-existing directory
- union of constraints of unequal clauses
- Wrong version returned by `compote version`
- Add upload mode to the pack_component
- optional dependencies always skipped when "version" undefined
- skip optional dependencies while solving dependencies
- api response string could be empty
- revert name slug re changes
- correct error message when manifest file is not a dict
- docs: fix render of '--'
- support env var in git source fields `git`, `path`
- support env var in local source fields `path`, `override_path`
- assume false when exceptions raised in if clause
- reset version solver states when the old solution not working
- test_check_for_newer_component_versions wrong component_hash
- store download_url only in storage client
- cleanup dependencies, lift version restrictions
- Consistent naming convention for ESP Component Registry
- local components in lock file not exist
- re-trigger version solver when optional dependency now meet conditions
- skip the optional dependencies while version solving
- Fix 'default' profile not loading from the config file
- Invalid component name on upload
- Handle missing files/broken symlinks when calculating hash

### Refactor

- unify env var with pydantic-settings
- rename service_url to registry_url in manifest files
- remove api cache with file
- remove poetry and do project cleanup
- rewrite with pydantic
- Change comment types to regular ones
- Replace format() with f-strings

## v2.0.0rc2 (2024-08-09)

### Fix

- manifest dump always adds empty fields
- remove redundant option --namespace from component pack CLI
- pack and upload components without manifests
- Fix login command with non-existing directory
- union of constraints of unequal clauses
- Wrong version returned by `compote version`
- Add upload mode to the pack_component

## v2.0.0rc1 (2024-08-05)

### Feat

- drop support of root level `commit_sha` in the manifest file

### Fix

- pass CLI arguments while uploading packed components
- calculate manifest hash based on set values

### Refactor

- remove unused attr `component_hash_required`

## v2.0.0rc0 (2024-08-02)

### Feat

- Add more descriptive error message for authentication
- compare .component_hash by default, support optionally strict checksum
- Make environment variables in if rules required to have a value
- store images on dockerhub

### Fix

- optional dependencies always skipped when "version" undefined
- skip optional dependencies while solving dependencies
- api response string could be empty
- revert name slug re changes
- correct error message when manifest file is not a dict
- docs: fix render of '--'
- support env var in git source fields `git`, `path`
- support env var in local source fields `path`, `override_path`
- assume false when exceptions raised in if clause

## v2.0.0dev1 (2024-06-19)

### Feat

- Revoke token on logout CLI command
- Use compote CLI when executed as module
- support debug mode by setting env var IDF_COMPONENT_MANAGER_DEBUG_MODE
- support reuse local existing versions while version solving
- Set COMPONENT_VERSION in CMake from manifests in requirements file
- use current solution while changing target or idf version if it works

### Fix

- reset version solver states when the old solution not working
- test_check_for_newer_component_versions wrong component_hash
- store download_url only in storage client
- `compote registry login` url
- cleanup dependencies, lift version restrictions
- Consistent naming convention for ESP Component Registry
- local components in lock file not exist
- local dep with '\_\_' can be treated as namespace separator correctly
- re-trigger version solver when optional dependency now meet conditions
- skip the optional dependencies while version solving
- Fix 'default' profile not loading from the config file
- Invalid component name on upload

### Refactor

- unify env var with pydantic-settings
- rename service_url to registry_url in manifest files
- remove api cache with file
- remove poetry and do project cleanup

## v2.0.0-dev0 (2024-05-17)

### Feat

- add esp32c61 to the list of known targets
- Drop support of Python 2.7

### Fix

- Handle missing files/broken symlinks when calculating hash
- fix the order of managed_components

### Refactor

- rewrite with pydantic
- Change comment types to regular ones
- Replace format() with f-strings

## v1.5.2 (2024-02-23)

### Fix

- wrongly terminate the version solver when versions not been found at the first round
- support boolean type for require field

## v1.5.1 (2024-02-14)

### Fix

- Handle git compatible version with revision in CLI

## v1.5.0 (2024-02-13)

### Feat

- add sync command to synchronize local mirror
- used callback to deprecate msg
- add alias for default_namespace and registry_url

### Fix

- optimize import list in .py files, drop unused imports
- fix packing and uploading of the components with lightweight tags
- **cli**: create test for updated login flags
- Delete log typo
- add missing commitizen config to pyproject.toml

## v1.5.0-dev1 (2024-02-06)

### Feat

- Add environment variable to disable TLS verification
- add repository_info block to the manifest
- add commitizen for changelog management

### Fix

- add missing commitizen config to pyproject.toml
- filter versions when api_client getting versions
- local components should override dependencies with same short name
- move tqdm progress_bar from api_client.py to core.py
- project_components priority should be higher than project_extra_components
- rename component_type to component_source

## v1.5.0-dev0 (2023-12-31)

### Added

- Support overriding components according to the component types
- Included the use of include/exclude filters from the manifest that is used for calculating the component hash.
- Added a user-friendly message to handle a 413 HTTP error triggered by sending large component archive.
- Add esp32c5 target
- Add URL and status code to network error messages
- Added --repository and --commit-sha parameters for packing and uploading component
- Added aliases for '--default_namespace' as '--default-namespace' and '--registry_url' as '--registry-url'. The previous versions have been marked as deprecated.
- Added CLI command `compote registry sync` to download components and synchronize a local mirror

### Fixed

- Fixed message formatting and progress bar displays during user component upload
- Fixed a problem when the local source created by the override_path parameter doesn't support web_service source keys
- Only expand environment variables in the manifest files during CMake execution
- Manifest dumping with non-expanded environment variables

## [1.4.1] - 2023-10-02

### Fixed

- Fix typo in gitlab CI user agent
- Fix issue with creating a profile in `idf_component_manager.yml` if it does not exist, when executing `compote registry login` command with `--service-profile` specified
- Remove warnings of the unknown root keys in the manifest files
- Fix schema validation of `idf_component_manager.yml`, for an empty profile name value
- Fix manifest schema validation message for an empty field value
- Fix processing of `rules` and `matches` for components from the registry
- Fix processing handling of `require` field for components from the registry

## [1.4.0] - 2023-09-15

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
- Option to check for new versions of components each time CMake is triggered (IDF_COMPONENT_CHECK_NEW_VERSION env variable)
- Support multiple storage urls in IDF_COMPONENT_STORAGE_URL environment variable (“;” separated) or from configuration file.

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

- Pin urllib version to \<2 to avoid incompatibility with older python versions
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
