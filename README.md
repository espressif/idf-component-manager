# IDF Component Manager

The IDF Component manager is a tool that downloads dependencies for any [ESP-IDF](https://www.espressif.com/en/products/sdks/esp-idf) CMake project. It makes sure that the right versions of all components required for a successful build of your project are in place. The download happens automatically during a run of CMake. It can source components either from [the component registry](https://components.espressif.com/) or from a git repository.

**A list of components can be found at https://components.espressif.com/**

## Installing the IDF Component Manager

IDF component manager can be used with ESP-IDF v4.1 and later.
It is installed by default with ESP-IDF v4.4+ and recent bug-fix releases of ESP-IDF 4.1+.

To check the installed version of the IDF component manager, first, activate [ESP-IDF environment](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/index.html#installation). On macOS and Linux:

```bash
source $IDF_PATH/export.sh
```

Then run the command:

```bash
python -m idf_component_manager -h
```

To update to the most recent version:

```bash
pip install idf-component-manager --upgrade
```

## Disabling the Component Manager

The component manager can be explicitly disabled by setting `IDF_COMPONENT_MANAGER` environment variable to `0`.

## Using with a project

You can add `idf_component.yml` manifest files with the list of dependencies to any component in your project.

IDF Component Manager will download dependencies automatically during the project build process.

When CMake configures the project (e.g. `idf.py reconfigure`) component manager does a few things:

- Processes `idf_component.yml` manifests for every component in the project
- Creates a `dependencies.lock` file in the root of the project with a full list of dependencies
- Downloads all dependencies to the `managed_components` directory

The component manager won't try to regenerate `dependencies.lock` or download any components if manifests, lock file, and content of `managed_component` directory weren't modified since the last successful build.

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

## Environment variables in manifest

You can use environment variables in values in `idf_component.yml` manifests. `$VAR` or `${VAR}` is replaced with the value of the `VAR` environment variable. If the environment variable is not defined, the component manager will raise an error.

Variable name should be ASCII alphanumeric string (including underscores) and start with an underscore or ASCII letter. The first non-identifier character after the `$` terminates this placeholder specification. You can escape `$` with one more`$` character, i.e., `$$` is replaced with `$`.

One possible use-case is providing authentication to git repositories accessed through HTTPS:

```yaml
dependencies:
  my_component:
    git: https://git:${ACCESS_TOKEN}@git.my_git.com/my_component.git
```

## Component metadata caching

By default information about available versions of components is cached for 5 minutes. You can adjust caching period by setting the duration in minutes to `IDF_COMPONENT_API_CACHE_EXPIRATION_MINUTES` environment variable or disable the cache entirely by setting it to 0.

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

To add examples to your component place them in the `examples` directory inside your component.
Examples are discovered recursively in subdirectories at this path.
A directory with `CMakeLists.txt` that registers a project is considered as an example.

## Custom example paths

You can specify custom example paths for uploading them to the component registry.
For that, add `examples` field to the root of the manifest:

```yaml
examples:
  - path: ../some/path
  - path: ../some/other_path
```

## Contributions Guide

We welcome all contributions to the Component Manager project.

You can contribute by fixing bugs, adding features, adding documentation, or reporting an [issue](https://github.com/espressif/idf-component-manager/issues). We accept contributions via [Github Pull Requests](https://docs.github.com/en/github/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests).

Before reporting an issue, make sure you've searched for a similar one that was already created. If you are reporting a new issue, please follow the Issue Template.

## Resources

- The Python Package Index project page https://pypi.org/project/idf-component-manager/
- The Component Manager section in the [ESP-IDF Programming Guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/tools/idf-component-manager.html)
