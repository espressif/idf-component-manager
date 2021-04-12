# Framework for integration tests

### Running tests:

```
py.test -s -c pytest_integration.ini
```

### Contribution

To create an integration test scenario add the declaration of the test case into the file with prefix
`test_`. Generally, the test structure should look like the following code. Decorator of the test procedure should
contain the test declaration and check some assertion. Variable `project` contains path to the project with declared
structure.

```python
@pytest.mark.parametrize(
    'project', [
        {
            'components': {
                'component_name': {
                    'dependencies': {
                        'some_component_dep': {
                            'git': 'https://github.com/espressif/esp-idf.git',
                            'path': 'components/some_component_dep/',
                            'include': 'some_component_dep.h'
                        }
                    }
                }
            }
        }
    ],
    indirect=True)
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
                    'include': 'some_component_dep.h'
                },
                'some_component_dep2': {
                    'version': '^1.0.0',
                    'include': 'some_component_dep2.h'
                }
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
    - `version` - version of the component in the component registry

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

### Tests

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
                    'include': 'unity.h'
                }
            }
        }
    }
}
```

2. The project contains only one component - main. Test adds version of the component into manifest and assumes
   dependency from the component registry. Test is successful when build of the project is successful.

```python
{
    'components': {
        'main': {
            'dependencies': {
                'mag3110': {
                    'version': '^1.0.0',
                    'include': 'mag3110.h'
                }
            }
        }
    }
}
```

3. The project contains two components - the main and "new_component". The "new_component"
privately requires the component button. This component is added into manifest of the main component 
   as a component registry dependency. The `main.c` of the main component includes `new_component.h` 
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
