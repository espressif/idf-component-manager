# Integration test framework

The integration tests are configured to run in parallel sub-test groups with [pytest-split](https://pypi.org/project/pytest-split/).

This `pytest` plugin enables dividing the test suite for a specific combination of ESP-IDF and Python versions into several test groups. The tests are evenly divided into groups by the plugin.

## Run integration tests locally

1. Navigate to the root of this repository.
2. Install the Python dependencies:
   ```sh
   pip install '.[test]'
   ```
3. Install ESP-IDF.
4. Run `source ./export.sh` from the ESP-IDF root directory.
5. Navigate to the `integration_tests` directory.
6. Run the integration tests locally with the following command
   ```
   python -m pytest -c "../pytest_integration.ini" --log-cli-level=INFO
   ```
   1. To run tests from specific file run:
      ```
      python -m pytest file_name.py -c "../pytest_integration.ini" --log-cli-level=INFO
      ```
   2. To run specific test case run:
      ```
      python -m pytest -k 'name_of_test_case' -c "../pytest_integration.ini" --log-cli-level=INFO
      ```

## Configure integration tests in the CI/CD pipeline

Configure the Gitlab CI/CD pipeline with the `integration_tests.yml` pipeline definition file:

1. In the `parallel:matrix` job definition, add a new matrix dimension `PYTEST_SPLIT_TEST_GROUP`, and define a number of test groups to create. Use a number range starting from 1 to the desired number of groups, for example to split the test suite into 5 groups, use `PYTEST_SPLIT_TEST_GROUP: [1, 2, 3, 4, 5]`.

   - **Note**: The `parallel:matrix` enables running test suites for a specific ESP-IDF development branch and a Python version in parallel jobs. So this pipeline implements two levels of parallelization.

2. Enter a number of groups in `<number_of_groups>` and configure the pipeline to run the following command. The number of the splits have to be the same as the number of the groups defined in the `PYTEST_SPLIT_TEST_GROUP` list:

   ```sh
   python -m pytest -c "pytest_integration.ini" \
   --log-cli-level=INFO \
   --splits <number_of_groups> \
   --group ${PYTEST_SPLIT_TEST_GROUP}
   ```

If you want to run all integration tests with ESP-IDF CMake build system v2, set `IDF_COMPONENT_TESTS_BUILD_SYSTEM_VERSION` environment variable to `2`. There is also a manual job for running integration tests with build system v2.

## Create an integration test

To create an integration test scenario add the declaration of the test case into the file with prefix
`test_`. Generally, the test structure should look like the following code. Decorator of the test procedure should
contain the test declaration and check some assertion. Variable `project` contains path to the project with declared
structure.

Please try to avoid using real components in integration tests if it is not strictly necessary.
There is a namespace [test](https://components.espressif.com/components?q=namespace%3Atest) with a collection of components for testing.

```python
@pytest.mark.parametrize(
    'project',
    [
        {
            'components': {
                'component_name': {
                    'dependencies': {
                        'some_component_dep': {
                            'git': 'https://github.com/espressif/esp-idf.git',
                            'path': 'components/some_component_dep/',
                            'include': 'some_component_dep.h',
                        }
                    }
                }
            }
        }
    ],
    indirect=True,
)
def test_single_dependency(project):
    assert some_action_with_project(project)
```

Currently, the project declaration supports assembling project from components. One component should be declared as one
dictionary in the project list of the decorator. Dictionary contains name of the component as a key and dictionary
denoting other properties of the component as a value. Following example demonstrates all possible declarations in the
component dictionary.

```python
{
    'components': {
        'component_name': {
            'dependencies': {
                'some_component_dep': {
                    'git': 'https://github.com/espressif/esp-idf.git',
                    'path': 'components/some_component_dep/',
                    'include': 'some_component_dep.h',
                },
                'some_component_dep2': {'version': '^1.0.0', 'include': 'some_component_dep2.h'},
            },
            'cmake_lists': {
                'priv_requires': 'another_component',
            },
        }
    }
}
```

- `dependencies` - denotes on what components the component depends.

  - `git` - denotes the url address for the git repository of the component (combine with `path`)
  - `path` - denotes the path to the component from the root of the git repository
  - `include`- value that is included in the source file of the component
  - `version` - version of the component in the ESP Component Registry

- `cmake_lists` - key-value in this dictionary will be used as the name of parameter and its value in the
  function `idf_component_register` of the `CMakeLists.txt`.

The framework will create declared project with some random name and following structure:

```
tmp7F1Ssf
├── main
│   ├── main.c
|   ├── CMakeLists.txt
|   ├── idf_component.yml
|   └── include
|       ├── main.h
├── components
│   └── some_component
│       ├── some_component.c
|       ├── CMakeLists.txt
|       ├── idf_component.yml
|       └── include
|           ├── some_component.h
└── CMakeLists.txt
```

You can also choose version of ESP-IDF build system.
By default, all projects are using V1 of ESP-IDF Cmake build system, but you can add `build_system_version`

```python
@pytest.mark.parametrize(
    'project',
    [{'build_system_version': 2}],
    indirect=True,
)
def test_build_system_v2(project):
    assert some_action_with_project(project)
```

## Examples of integration tests

1. The project contains only one component - main. This test adds git path and path to the component in the manifest and
   also includes `unity.h` in the `main.c`. Test is successful when build of the project is successful.

```python
{
    'components': {
        'main': {
            'dependencies': {
                'unity': {
                    'git': 'https://github.com/espressif/esp-idf.git',
                    'path': 'components/unity/',
                    'include': 'unity.h',
                }
            }
        }
    }
}
```

2. The project contains only one component - main. Test adds version of the component into manifest and assumes
   dependency from the ESP Component Registry. Test is successful when build of the project is successful.

```python
{
    'components': {
        'main': {'dependencies': {'mag3110': {'version': '^1.0.0', 'include': 'mag3110.h'}}}
    }
}
```

3. The project contains two components - the main and "new_component". The "new_component"
   privately requires the component button. This component is added into manifest of the main component
   as a ESP Component Registry dependency. The `main.c` of the main component includes `new_component.h`
   and `button.h`. Test is successful when build of the project is successful.

```python
    {
    'components': {
        'main': {
            'dependencies': {
                'new_component': {
                    'include': 'new_component.h',
                },
                'button': {
                    'version': '^1.0.0',
                    'include': 'button.h'
                }
            }
        },
        'new_component': {
            'cmake_lists': {
                'priv_requires': 'button',
            },
        }
    },
}
```
