# IDF Component Management

Component manager for ESP IDF

## Use with idf.py

To use component manager with `idf.py` install `idf-component-manager` python package to idf's virtual environment. Then `idf_component.yml` manifests will be processed automatically when CMake is running.

## Use without IDF

Some features, like uploading a component to the service are available without IDF. It's useful for CI pipelines where IDF may not be available.

The component manager may be executed as a python module, for example:

```
python -m idf_component_manager create-remote-component --namespace espressif --name test
```

## Writing the manifest

Example of a component manifest:

```yaml
version: "2.3.1" # Component version, required only for components pushed to the service
targets: # List of supported targets (optional, if missing all targets are considered to be supported)
    - esp32
description: Test project # Description (optional)
url: https://github.com/espressif/esp-idf # Original repository (optional)
dependencies:
    # Required IDF version
    idf:
        version: ">=4.1"
    # For components maintained by Espressif:
    # Same as `espressif/component`
    component:
        version: "~1.0.0"
    # For 3rd party components :
    username/component:
        version: "~1.0.0"
        public: true # For transient dependencies
    # For components hosted on non-official web service:
    company_user/component:
        version: "~1.0.0"
        service_url: "https://componentservice.company.com"
    # For components in git repository:
    test_component:
        path: test_component
        git: ssh://git@gitlab.com/user/components.git
    # For components in local folder:
    some_local_component:
        path: ../../projects/component
```
