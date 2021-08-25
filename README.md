# IDF Component Management

IDF Component manager is a tool for managing dependencies for any ESP IDF 4.1+ CMake project. Components can be installed either from [the component registry](https://components.espressif.com) or from a git repository.

List of components can be found on https://components.espressif.com/

## Installing the IDF Component Manager

To use component manager with IDF install `idf-component-manager` [python package](https://pypi.org/project/idf-component-manager/) to virtual environment with IDF environment. For example in BASH:

```
source $IDF_PATH/export.sh
pip install idf-component-manager --upgrade
```

No extra steps are required, if CMake is started using `idf.py` or [ESP IDF VSCode Extension](https://marketplace.visualstudio.com/items?itemName=espressif.esp-idf-extension).
If CMake is used directly or with some CMake-based IDE, like Clion it's necessary to set `IDF_COMPONENT_MANAGER` environment variable to `1` to enable the component manager integration with the build system.

## Using with a project

Dependencies for each component in the project are defined in a separate manifest file named `idf_component.yml` placed in the root of the component.
It's not necessary to have a manifest for components that don't need any managed dependencies.

When CMake configures the project (e.g. `idf.py reconfigure`) component manager does a few things:

- Processes `idf_component.yml` manifests for every component in the project
- Creates a `dependencies.lock` file in the root of the project with a full list of dependencies
- Downloads all dependencies to the `managed_components` directory

The component manager won't try to regenerate `dependencies.lock` or download any components if manifests, lock file, and content of `managed_component` directory weren't modified since the last successful build.

### Defining dependencies in the manifest

```yaml
dependencies:
  # Required IDF version
  idf: ">=4.1"
  # For components maintained by Espressif only name can be used.
  # Same as `espressif/component`
  component:
    version: "~2.0.0"
  # Or in a shorter form
  component2: ">=1.0.0"
  # For 3rd party components :
  username/component:
    version: "~1.0.0"
    # For transient dependencies `public` flag can be set.
    # `public` flag doesn't have an effect for the `main` component.
    # All dependencies of `main` are public by default.
    public: true
  anotheruser/component: "<3.2.20"
  # For components hosted on non-default registry:
  company_user/component:
    version: "~1.0.0"
    service_url: "https://componentregistry.company.com"
  # For components in git repository:
  test_component:
    path: test_component
    git: ssh://git@gitlab.com/user/components.git
  # For test projects during component development
  # components can be used from a local directory
  # with relative or absolute path
  some_local_component:
    path: ../../projects/component
```

## Creating a component for the registry

For components to be published in the registry `idf_component.yml` manifest is required.

Example of a component manifest `idf_component.yml`:

```yaml
# Version of the component [Required]
# It should follow https://semver.org/spec/v2.0.0.html spec.
version: "2.3.1"

# List of supported targets [Optional]
# If missing all targets are considered to be supported
targets:
  - esp32

# Short description for the project [Recommended]
description: Test project
# Github repo or a home  [Recommended]
url: https://github.com/espressif/esp-idf

# List of dependencies [Optional]
# All dependencies of the component should be published in the same registry.
dependencies:
  # Default namespace is `espressif`
  # Declaring dependency as `cool_component` is the same as `espressif/cool_component`
  cool_component: ">1.0.0"
  some_ns/some_component:
    version: "~1.2.7"
```

It's also recommended to include documentation and license information with the component.

### Documenting components

Component registry automatically processes and renders in the Web UI documentation provided in these files:

- `README.md` - General information
- `CHANGELOG.md` - Version history
- `API.md` - Programming interface

Only markdown (\*.md) files are supported. Filenames are not case-sensitive.

### Providing a license

There is no field in the manifest to put license name, instead, it's possible to create a file name `license` or `license.txt` (case insensitive) in the root of the component with the full text of the license agreement. Commonly used licenses will be detected automatically and displayed with the component. The original text of the license is always delivered with the component.

### Uploading a component to the registry

To upload a component run `upload-component` command. If the component doesn't exist in the registry it will be created automatically.

```
idf.py upload-component --namespace=username --name=component
```

## Using component manager in CI

Some component manager commands commonly used for CI pipelines use are available without IDF.

- `pack-component` - Prepare an archive with the component
- `upload-component` - Upload component to the registry
- `upload-component-status` - Check status of the processing of the component
- `delete-version` - Mark component version as deleted.

These commands can be executed by running component manager as a python package:

```
python -m idf_component_manager upload-component --namespace robertpaulson --name mayhem
```

### Exit codes

In case of issues during execution CLI will return a non-zero exit code. Some of these exit codes having a special meaning are listed below:

- **2** - Regular exit code for unsuccessful execution.
- **144** - Runtime error for situations, when an operation is prematurely aborted due to nothing to do. For example, "upload-component" command returns code 144 when the version already exists in the registry.

### Uploading components with Github Action

Github Action to upload components to the registry is available as part of Espressif's GitHub actions:
https://github.com/espressif/github-actions/tree/master/upload_components

## Athentication in the registry

To run a command that changes data in the registry authentication token should be provided. The most common way to do it is by setting `IDF_COMPONENT_API_TOKEN` environment variable.

## Configuring multiple profiles

If it's necessary to configure access to a non-default registry or configure more than one profile then the configuration can be placed to the `idf_component_manager.yml` in the directory with IDF toolchain (`~/.espressif` by default, but can be changed by setting `IDF_TOOLS_PATH` environment variable)

Values provided for `default` profile will be used by default.

Configurable options:

- `api_token` - Access token to the registry. Required for all operations modifying data in the registry.
- `default_namespace` - Namespace used for the creation of component or upload of a new version. Default is not set.
- `service_url` - URL of the component registry API. Default: `https://api.components.espressif.com`

Example `idf_component_manager.yml`:

```yaml
profiles:
  default:
    api_token: some_token
    default_namespace: example

  staging:
    service_url: https://api.example-service.com
    api_token: my_long_long_token
    default_namespace: my_namespace
```
