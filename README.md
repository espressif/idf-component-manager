# IDF Component Manager

The IDF Component Manager is a tool that ensures the correct versions of all components required for a successful build are present in your [ESP-IDF](https://www.espressif.com/en/products/sdks/esp-idf) project.

- The Component Manager downloads the dependencies for your project automatically during a `CMake` run.
- The components can be sourced either from [the ESP Component Registry](https://components.espressif.com/) or from a Git repository.
- A list of components can be found at https://components.espressif.com/

## Contributing to the project

See [CONTRIBUTING.md](CONTRIBUTING.md)

## Resources

- [Offical Documentation at docs.espressif.com](https://docs.espressif.com/projects/idf-component-manager/en/latest/)
- The Python Package Index project page https://pypi.org/project/idf-component-manager/
- The Component Manager section in the [ESP-IDF Programming Guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/tools/idf-component-manager.html)

# Develop ESP-IDF projects with the IDF Component Manager

## Installing a development version of the Component Manager

You can install the development version of the Component Manager from the main branch of this repository:

**On Linux/macOS:**

Go to the directory with your ESP-IDF installation and run:

```bash
# activate ESP-IDF environment
source ./export.sh # or . ./export.fish, if you use fish shell
# remove old version of the Component Manager
python -m pip uninstall -y idf-component-manager
# install the development version (from the main branch)
python -m pip install git+https://github.com/espressif/idf-component-manager.git@main
```

**On Windows:**

Run `ESP-IDF PowerShell Environment` or `ESP-IDF Command Prompt (cmd.exe)` from the Start menu and run the following command:

```powershell
# remove old version of the Component Manager
python -m pip uninstall -y idf-component-manager
# install the development version (from the main branch)
python -m pip install git+https://github.com/espressif/idf-component-manager.git@main
```

## Disabling the Component Manager

The Component Manager can be explicitly disabled by setting `IDF_COMPONENT_MANAGER` environment variable to `0`.

## Using with a project

You can add `idf_component.yml` manifest files with the list of dependencies to any component in your project.

IDF Component Manager will download dependencies automatically during the project build process.

When CMake configures the project (e.g. `idf.py reconfigure`) Component Manager does a few things:

- Processes `idf_component.yml` manifests for every component in the project
- Creates a `dependencies.lock` file in the root of the project with a full list of dependencies
- Downloads all dependencies to the `managed_components` directory

The Component Manager won't try to regenerate `dependencies.lock` or download any components if manifests, lock file, and content of `managed_component` directory weren't modified since the last successful build.

## Defining dependencies in the manifest

All dependencies are defined in the manifest file.

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
    public: true
  anotheruser/component: "<3.2.20"
  # For components hosted on non-default registry:
  company_user/component:
    version: "~1.0.0"
    registry_url: "https://componentregistry.company.com"
  # For components in git repository:
  test_component:
    path: test_component
    git: ssh://git@gitlab.com/user/components.git
  # For test projects during component development
  # components can be used from a local directory
  # with relative or absolute path
  some_local_component:
    path: ../../projects/component
  # For optional dependencies
  optional_component:
    version: "~1.0.0"
    rules: # will add "optional_component" only when all if clauses are True
      - if: "idf_version >=3.3,<5.0" # supports all SimpleSpec grammars (https://python-semanticversion.readthedocs.io/en/latest/reference.html#semantic_version.SimpleSpec)
      - if: "target in [esp32, esp32c3]" # supports boolean operator ==, !=, in, not in.
  # For example of the component
  namespace/component_with_example:
    version: "~1.0.0" # if there is no `override_path` field, use component from registry
    override_path: "../../" # use component in a local directory, not from registry
  namespace/no_required_component:
    version: "*"
    require: no # Download component but don't add it as a requirement
  namespace/pre_release_component:
    version: "*"
    pre_release: true # Allow downloading of pre-release versions
```

## Component metadata caching

By default, information about available versions of components not cached. If you make many requests to the registry from one machine, you can enable caching by setting `IDF_COMPONENT_API_CACHE_EXPIRATION_MINUTES` environment variable to the number of minutes to cache the data.

## External links

You can add links to the `idf_component.yml` file to the root of the manifest:

```yaml
url: "https://example.com/homepage" # URL of the component homepage
repository: "https://gitexample.com/test_project" # URL of the public repository with component source code, i.e GitHub, GitLab, etc.
documentation: "https://example.com/documentation" # URL of the component documentation
issues: "https://git.example.com/test_project/tracker" # URL of the issue tracker
discussion: "https://discord.example.com/test_project" # URL of the component discussion, i.e. Discord, Gitter, forum, etc.
```

A link should be a correct HTTP(S) URL like `https://example.com/path` except the `repository` field,
it is expected to be a valid [Git remote](https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes) URL.

## Add examples to the component

To add examples to your component, place them in the `examples` directory inside your component.
Examples are discovered recursively in subdirectories at this path.
A directory with `CMakeLists.txt` that registers a project is considered as an example.

## Custom example paths

You can specify custom example paths for uploading them to the component registry.
For that, add `examples` field to the root of the manifest:

```yaml
examples:
  - path: ../some/path
  - path: ../some/other_path
  # - path: examples/some_example # this example will be discovered automatically
```

## Environment variables

| Variable                                     | Default value (or example for required) | Description                                                                                                   |
| -------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| IDF_COMPONENT_API_TOKEN                      |                                         | API token to access the component registry                                                                    |
| IDF_COMPONENT_REGISTRY_URL                   | https://components.espressif.com/       | URL of the default component registry                                                                         |
| IDF_COMPONENT_STORAGE_URL                    | https://components-file.espressif.com/  | URL of the default file storage server                                                                        |
| IDF_COMPONENT_PROFILE                        | default                                 | Profile in the config file to use                                                                             |
| IDF_COMPONENT_CACHE_PATH                     | \* Depends on OS                        | Cache directory for Component Manager                                                                         |
| IDF_COMPONENT_VERSION_PROCESS_TIMEOUT        | 300                                     | Timeout in seconds to wait for component processing                                                           |
| IDF_COMPONENT_OVERWRITE_MANAGED_COMPONENTS   | 0                                       | Overwrite files in the managed_component directory, even if they have been modified by the user               |
| IDF_COMPONENT_SUPPRESS_UNKNOWN_FILE_WARNINGS | 0                                       | Ignore unknown files in managed_components directory                                                          |
| IDF_COMPONENT_CHECK_NEW_VERSION              | 1                                       | Check for new versions of components                                                                          |
| IDF_COMPONENT_VERIFY_SSL                     | 1                                       | Verify SSL certificates when making requests to the registry, set it 0 to disable or provide a CA bundle path |
| IDF_COMPONENT_CACHE_HTTP_REQUESTS            | 1                                       | Cache HTTP requests to the registry during runtime, set it 0 to disable                                       |
