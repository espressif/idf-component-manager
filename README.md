# IDF Component Management

Component manager python script for ESP IDF
This repo is only intended to be used for initial development, then it should be part of IDF itself.

## Use Cases

- Third party develops a component for use with IDF and wants to make this available to others.
- User wants to combine components from multiple third parties and from Espressif to compile their firmware. Wants to be able to update this code as necessary when new versions are available.
- IDF developers want to minimize the amount of external functionality in "core" IDF (for compile time, ease of maintenance, etc)
- Espressif wants to provide code for support of third party hardware, cloud services, software libraries, etc. without bundling this into IDF.

# IDF Component Management

Component manager checks and installs your project's dependencies, provides information about dependencies to CMake based build system, makes distributable packages and uploads them to components registry service.

Component service is hosted at https://components.espressif.com and provides JSON API as well as WEB UI and provides version management, dependency information and documentation for all components

## General requirements

Client-side part of component manager is a python CLI application, that works with both python 2 and 3 on all major platforms (Windows, Linux, macOS). It check/install dependencies for IDF projects and provides dependency information for IDF's CMake build system.

## Terminology and file structure

### Component

"component" is an library that can be used with your project that consists from:

- bundle of code (described in `CMakeLists.txt`)
- `tests` directory (optional)
- `examples` directory (optional)
- `docs` directory (optional)
- `CMakeLists.txt`
- `KConfig` (optional)
- `LICENSE` (optional, but highly recommended)
- `idf_component.yml` - list of dependencies and component's description(optional, but highly recommended and required for components )

_NB_: Word "package" in this document is the synonym for "component"

### Project

"project" is an IDF project, ie application code which compiles to a .bin app to flash to a chip (esp32, for example).

- `tests` directory (optional)
- `docs` directory (optional)
- `components` - is a directory that stores components managed by user itself. These components have higher priority over managed components
- `managed_components` - is a directory that stores components managed by component manager. This should be ingored by git.
- `idf_project.yml` - contains list of project dependencies
- `idf_project.lock` - yaml-formatted document that contains flat list of exact versions for whole tree of dependencies

## Component manager requirements

### Requirements

- Cross-platfrom (Windows, Linux, macOS)
- Written in python, works with both python 2 and 3
- Should be used by CMake to check/install dependencies before the build
- Store all dependencies in `external_components` folder under project root

### CLI Commands

- `add [package_name ...]` - adds packages to components file, then sync all packages listed in components list and updates lock file if necessary.
- `install` - installs packages from current manifest
- `sync` - downloads packages listed in current `dependencies.lock` file
- `update [package_name ...]` - updates given packages with respect to version ranges from component file. If package name are not provided updates all components from dependencies file.
- `prebuild` - this command is only intended to be used by cmake as a first step of build process
- `package` - Creates a tarball of current. All code from `components` folder will be added to the archive (To be used with components)
- `upload [--url https://package.repository] [--token "LONG_LONG_JWT"] [--username user] [--password secret]` - Uploads tarball to repository using provided credentials
- `list` - show list of all dependencies for current project

## Component service

### Requirements

- For public service registration should be possible through social services: Github, Gitlab, Bitbucket(?)
- New versions of packages should be added automatically using git hooks for projects hosted on Github/Gitlab
- Registration with email and password
- Option to search packages and see package history
- Automatic component releaser should support submodules in git repositories

### Web interface requirements

### API methods

#### Components

Methods that require user authentication are marked as **auth**.

Implemented:

- `GET /api/` - shows generic information about API: version, description and status
  Example response:
  ```
  {
    "status": "ok",
    "info": "Espressif Component Manager Service HTTP JSON API",
    "version": "0.0.1"
  }
  ```
- `GET /api/components/[component name]?version=[version]` - returns component manifest including download url for specified version (or latest)
- `POST /api/components/` - **auth** Uploads new version of the component. tar, zip and tar.gz files are supported. Components metadata may be send along with request (for faster validaton) or will be extracted from archive.
- `GET /api/components/[component name]/versions?spec=[spec]` - list of versions that conform "spec"

In progress:

- `GET /api/components/search?query=[query]` - search for components, paginated response
- `GET /api/components/` - **auth** list of components for current user
- `DELETE /api/components/[component_name]?version=[version]` - **auth** Mark given version of component as deleted

#### User management

- `GET/api/api_key` - returns API key by login and password send with basic auth

#### Component

- List of direct dependencies for given package and version
- Tree of dependencies for given list of packages
- Search for package by name
- Show package versions and history

### Possible requirements

- Ability to upload archives with components
- Should be open sourced, so organizations can deploy on own hardware
- Should be distributed as docker image for easy deployment

## Manifest file

### Requirements

- Should support comments
- Supports a particular IDF version or range.
- Supports packages from component repository and from git
- Works with semantically versioned tags, git branches and commits
- Works with private package repositories
- Expects that all versions follow semantic versioning 2.0
- Versions can be declared as:
  - '~1.2.3' - version >= 1.2.3 < 1.3.0
  - '^1.2.3' - version >= 1.2.3 < 2.0.0
  - '>1.2.3'
  - '>=1.2.3'
  - '<1.2.3'
  - '<=1.2.3'
  - '!=1.2.3'
  - '1.2.3'
  - Combined rules: ">= 1.2.3,<1.3.4,!=1.3.1"

### Example (

```yaml
version: "2.3.1" # While it may be optional for projects it should be required for components
targets: [esp32]
description: "" # Required for components
dependencies:
  idf: 3.1.2
  freertos:
    version: ">=8.2.0 <9.0.0"
  esp32: "^1.2.7" # Shorthand, if version is the only parameter
  aws-iot:
    version: "~1.2.7"
  component-some:
    version: "~1.2.2"
```

## Lock file

### Requirements

- Should be readable by CMake build system (?)
- Should store exact versions of every package, IDF
- Should store hash of components manifest to check if it's necessary to update
- Should store hash sum for directory, to check if actual component on disk is the same that required

### Example for dependencies.lock

```yaml
# This file is generated automatically. Please never edit it manually. Run "idf.py component install" to update lock file.
component_manager_version: 1.0.3

manifest_hash: "f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b"
dependencies:
  idf: 3.0.2
  aws-iot:
    version: 1.2.7
    component_hash: "f0e4c2f76c58916ec258f246851bea091d14d4247a2fc3e18694461b1816e13b"
    source:
      type: service
      url: https://repo.example.com/
```

### Possible future features

- Support for License
- Support for binary components
- Support for documentation hosting
- Support for host-side python tools
- An ability to install component to `components` folder
- Support for host-side tools, that require compilation or providing binaries for all supported platforms
- Supports environment variables in manifest
- Support for multiple repositories in manifest file, like:

```yaml
repositories: # Describes all package repositories. Support for grouped repositories will be added with next release
  default: # Allows to override url for default package source
    url: "http://some-mirror-in.cn" # Should insecure http mirrors be allowed?
  corporate:
    url: "https://some.company.repo"
    api_token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c # Values may be stored directly in the file (JWT are well suited for this use)
  one_more:
    url: "https://example.repo"
    api_token: { { ONE_MORE_API_TOKEN } } # Or environment variable
dependencies:
  component-1:
    version: "~1.2.7"
    repository: corporate
  component-2:
    version: "~1.2.7"
    repository: corporate
```
