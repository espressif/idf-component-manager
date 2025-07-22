``idf_component.yml`` Manifest File
===================================

Use the ``idf_component.yml`` manifest file to describe a component and its dependencies. The file must be located in the root directory of the component.

The manifest supports the following sections:

.. contents::
    :local:
    :depth: 1

Build-Related Attributes
------------------------

Use the following attributes to affect the component’s build process:

.. contents::
    :local:
    :depth: 1

``targets``
~~~~~~~~~~~

A list of targets that the component supports.

This field is optional and can be omitted if the component is compatible with all targets.

Example:

.. code-block:: yaml

    targets:
      - esp32
      - esp32c3

``dependencies``
~~~~~~~~~~~~~~~~

A dictionary of dependencies required by the component.

This field is optional and can be omitted if the component does not have any dependencies. The detailed usage is described in the `component dependencies`_ section.

Metadata Attributes
-------------------

Use metadata attributes to provide additional information about the component. The metadata attributes are only evaluated when the component is uploaded to the ESP Component Registry.

Supported metadata attributes include:

.. contents::
    :local:
    :depth: 1

``version``
~~~~~~~~~~~

The version of the component, following the :ref:`versioning scheme <versioning-scheme>`.

This field is required when uploading the component to the ESP Component Registry. You can specify the version by:

- Defining it in the ``idf_component.yml`` file
- Tagging the commit in the Git repository with the version number
- Passing the version as an argument to the ``compote component upload --version [version]`` command

Example:

.. code-block:: yaml

    version: "1.0.0"

``maintainers``
~~~~~~~~~~~~~~~

A list of maintainers of the component.

The field is optional.

Example:

.. code-block:: yaml

    maintainers:
      - First Last <email@example.com>

``description``
~~~~~~~~~~~~~~~

A short description of the component.

This field is optional but highly recommended. If it is not specified, a warning message will be displayed when the component is uploaded to the registry.

Example:

.. code-block:: yaml

    description: "This is a component that does something useful."

``license``
~~~~~~~~~~~

The license under which the component is released. It must be a valid SPDX license identifier listed in https://spdx.org/licenses/.

Either the ``license`` field or the ``LICENSE`` or ``LICENSE.txt`` file must be present in the component directory.

The license type will be determined as follows:

- If the ``license`` field is specified, its value will be used.
- If not, the license will be parsed from the ``LICENSE`` or ``LICENSE.txt`` file during upload.
- If the license type cannot be determined, it will be set to ``Custom``.

Example:

.. code-block:: yaml

    license: "MIT"

``tags``
~~~~~~~~

A list of keywords related to the component’s functionality.

This field is optional.

Example:

.. code-block:: yaml

    tags:
      - wifi
      - networking

``files``
~~~~~~~~~

Controls which files are included when the component is archived or used as a Git dependency.

This field is a dictionary with the following options:

- ``use_gitignore``: Excludes files based on ``.gitignore`` file.
- ``include``: A list of patterns specifying files to include.
- ``exclude``: A list of patterns specifying files to exclude.

Examples:

1. Use ``.gitignore`` to exclude files:

   .. code-block:: yaml

       files:
          use_gitignore: true

2. Use ``include`` and ``exclude`` patterns:

   .. code-block:: yaml

       files:
          exclude:
             - "*.py"          # Exclude all Python files
             - "**/*.list"     # Exclude all `.list` files in any directory
             - "big_dir/**/*"  # Exclude the `big_dir` directory and all its contents
          include:
             - "**/.DS_Store"  # Explicitly include `.DS_Store` files (normally excluded by default)

3. Use both options. Consider the following ``.gitignore`` file:

   .. code-block:: text

       test_dir/

Then the ``idf_component.yml`` manifest might look like this:

    .. code-block:: yaml

        files:
           use_gitignore: true
           exclude:
              - ".env"          # Exclude the `.env` file
           include:
              - "test_dir/**/*" # Re-include all files in the `test_dir` directory
                                # that were excluded by `.gitignore`

Filters are applied in the following order:

1. All files are included by default.
2. If ``use_gitignore`` is set to ``true``, files are excluded based on the ``.gitignore`` file. Otherwise the default exclusion list is used.
3. If the ``exclude`` field is set, files are excluded based on the specified patterns.
4. If the ``include`` field is set, files matching the specified patterns are re-included, even if they were excluded in the previous steps.

Note: The ``include`` field can be used to override exclusions from the ``exclude`` field, the ``.gitignore`` file, and the default exclusion list.

This field is optional and can be omitted if the component contains all files in the root directory with the default list of exceptions.

.. note::

    The ``files`` field is used in the following scenarios:

    - When creating the archive before the component is uploaded to the registry.
    - When the component is used as a `Git dependency <git-source_>`_.

.. note::

    Filters are also applied to examples located in the component directory.

A list of files and directories that are excluded by default:

|DEFAULT_EXCLUDE|

.. _manifest-examples:

``examples``
~~~~~~~~~~~~

A list of directories containing examples.

This field is optional if all examples are located within the ``examples`` directory. The ESP Component Registry will automatically discover examples in the ``examples`` directory and its subdirectories.

Example:

.. code-block:: yaml

    examples:
      - path: custom_example_path_1
      - path: custom_example_path_2
      # - path: examples/foo  # No need to list this if the example is under the "examples" folder

``url``
~~~~~~~

The component’s website.

This field is optional but highly recommended. If omitted, a warning will appear during upload.

Example:

.. code-block:: yaml

    url: "https://example.com"

``repository``
~~~~~~~~~~~~~~

The Git URL of the component’s source repository. Must be a valid `Git remote URL <https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes>`_.

This field is optional, but highly recommended.

Example:

.. code-block:: yaml

    repository: "https://example.com/component.git"

``repository_info``
~~~~~~~~~~~~~~~~~~~

Additional information about the repository.

This field is optional. However, if it is set, the ``repository`` field must also be specified.

If your component is not located at the root of the repository, use the ``path`` field to specify its location.

.. code-block:: yaml

    repository: "https://example.com/component.git"
    repository_info:
      path: "path/to/component"

You may also specify the Git commit SHA of the component you intend to use in the ``commit_sha`` field.

.. code-block:: yaml

    repository_info:
      commit_sha: "1234567890abcdef1234567890abcdef12345678"

The commit SHA can also be passed as an argument to the ``compote component upload --commit-sha [commit_sha]`` command.

Both ``path`` and ``commit_sha`` sub-fields are optional.

``documentation``
~~~~~~~~~~~~~~~~~

The URL for the component’s documentation.

This field is optional.

Example:

.. code-block:: yaml

    documentation: "https://docs.example.com"

``issues``
~~~~~~~~~~

The URL for the component’s issue tracker.

This field is optional.

Example:

.. code-block:: yaml

    issues: "https://issues.example.com"

``discussion``
~~~~~~~~~~~~~~

The URL for the component’s discussion forum or chat.

This field is optional.

Example:

.. code-block:: yaml

    discussion: "https://chat.example.com"

.. _component-dependencies:

Component Dependencies
----------------------

Use the ``dependencies`` field to specify dependencies. This field is a dictionary where each key represents the name of a dependency.

Before defining dependencies, review the following sections:

- `Common Attributes for All Dependency Types`_
- `Environment Variables`_
- `Conditional Dependencies`_.

The component manager supports the following types of dependency sources:

- `Local Directory Dependencies`_
- `Git Dependencies`_
- `ESP Component Registry Dependencies`_
- `ESP-IDF Dependency`_

.. warning::

    `Local Directory Dependencies`_ and `Git Dependencies`_ are not supported when uploading components to the ESP Component Registry.

Common Attributes for All Dependency Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These attributes are optional and supported across all dependency types.

``require``
+++++++++++

Specifies component visibility. Possible values:

- ``private`` *(default)*: The required component is added as a private dependency. This is equivalent to adding the component to the ``PRIV_REQUIRES`` argument of ``idf_component_register`` in the component's ``CMakeLists.txt`` file.
- ``public``: Marks the component as a transient dependency. This is equivalent to adding the component to the ``REQUIRES`` argument of ``idf_component_register`` in the component's ``CMakeLists.txt`` file.
- ``no``: Downloads the component without adding it as a requirement.

Example:

.. code-block:: yaml

    require: public
    # require: private  # default

``matches``
+++++++++++

A list of `conditional dependencies`_ to be applied to the dependency. The dependency is included if **any** of the ``if`` clauses are true.

``rules``
+++++++++

A list of `conditional dependencies`_ to be applied to the dependency. The dependency is included only if **all** of the ``if`` clauses are true.

.. _conditional-dependencies:

Conditional Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~

The ``matches`` and ``rules`` attributes control whether a dependency is included. A dependency is included only when:

- Any of the ``if`` clauses in ``matches`` is true.
- All of the ``if`` clauses in ``rules`` are true.

Both ``matches`` and ``rules`` are optional. If omitted, the dependency is always included.

``matches`` and ``rules`` support the same syntax. Each is a list of conditional dependencies, where each item includes an ``if`` field and an optional ``version`` field.

``if``
++++++

The ``if`` field is a boolean expression evaluated to determine whether the dependency should be included. An expression consists of three parts: left value, operator, and right value.

The following table outlines the supported comparison types for the ``if`` field:

.. list-table:: Supported Comparison Types
    :header-rows: 1

    - - Left Value Type
      - Operators
      - Right Value Type
    - - Keyword ``idf_version``
      - N/A
      - String representing a :ref:`version range <version-range-specifications>`
    - - Keyword ``target``
      - ``!=``, ``==``
      - string
    - - Keyword ``target``
      - ``in``, ``not in``
      - List of strings
    - - Arbitrary string
      - ``==``, ``!=``
      - String
    - - Arbitrary string
      - ``in``, ``not in``
      - List of strings
    - - `Environment variables`_
      - N/A
      - String representing a :ref:`version range <version-range-specifications>`
    - - `Environment variables`_
      - ``==``, ``!=``
      - String
    - - `Environment variables`_
      - ``in``, ``not in``
      - List of strings
    - - `kconfig options`_
      - ``==``, ``!=``
      - String
    - - `kconfig options`_
      - ``in``, ``not in``
      - List of strings
    - - `kconfig options`_
      - ``==``, ``!=``, ``<=``, ``<``, ``>=``, ``>``
      - Decimal or hexadecimal integer (e.g., ``0x1234``)
    - - `kconfig options`_
      - ``==``, ``!=``
      - Boolean (``True``, ``False``)

.. versionadded:: 2.2.0

    - Support for `kconfig options`_ as left values (requires ESP-IDF >=6.0)
    - Support for ``boolean``, ``integer``, and ``hexadecimal integer`` data types in `kconfig options`_

.. warning::

    Since kconfig supports data types, you MUST use double quotes for strings when comparing with kconfig options. Otherwise, the component manager will treat the value as an integer and raise an error if it's not parsable as such.

    Double quotes are not required for strings when not comparing with kconfig options, but using them is recommended for consistency.

.. warning::

    If you use an `environment variables`_ as the left value of an ``if`` clause and it is not set, an error will be raised.

    If you specified `kconfig options`_ as the left value of the if clause, but the kconfig is included in your project, or components, an error will be raised.

To create complex boolean expressions, use parentheses along with the boolean operators ``&&`` and ``||``.

.. code-block:: yaml

    dependencies:
      optional_component:
       version: "~1.0.0"
       rules:
         - if: "idf_version >=3.3,<5.0"
         - if: target in ["esp32", "esp32c3"]
         # The above two conditions are equivalent to:
         - if: idf_version >=3.3,<5.0 && target in ["esp32", "esp32c3"]

.. hint::

    A common use case for `environment variables`_ is to test it in CI/CD pipelines. For example:

    .. code-block:: yaml

        dependencies:
          optional_component:
            matches:
              - if: "$TESTING_COMPONENT in [foo, bar]"

    The dependency will only be included if the environment variable ``TESTING_COMPONENT`` is set to ``foo`` or ``bar``.

``version`` (if clause)
+++++++++++++++++++++++

The ``version`` field is optional and can be either a :ref:`specific version <versioning-scheme>` or a :ref:`version range <version-range-specifications>`. The version specified here overrides the ``version`` field of the dependency when the corresponding ``if`` clause evaluates to true.

For example:

.. code-block:: yaml

    dependencies:
      optional_component:
        matches:
          - if: "idf_version >=3.3"
            version: "~2.0.0"
          - if: "idf_version <3.3"
            version: "~1.0.0"

In this example, ``optional_component`` will be included with version ``~2.0.0`` when ``idf_version >=3.3``, and with version ``~1.0.0`` when ``idf_version <3.3``.

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

.. warning::

    Environment variables are not allowed in manifests when uploading components to the ESP Component Registry.

.. warning::

    Environment variable names should only contain alphanumeric characters and underscores, and must not start with a number.

You can use environment variables in attributes that support them. The component manager replaces the variables with their values. Use the following syntax:

- ``$VAR``
- ``${VAR}``

To include a literal dollar sign (``$``), escape it with another dollar sign: ``$$string``.

.. _local-source:

Kconfig Options
~~~~~~~~~~~~~~~

You can use Kconfig options for attributes that support them. All Kconfig options should be wrapped with ``$CONFIG{...}`` and don't need to include the ``CONFIG_`` prefix.

For example, to compare with the Kconfig option ``CONFIG_MY_OPTION``, use ``$CONFIG{MY_OPTION}``.

Only Kconfig options defined in the ESP-IDF project or its direct dependency components are supported. For example:

.. code-block:: yaml

    dependencies:
       cmp:
         version: "*"
         matches:
           - if: "$CONFIG{BOOTLOADER_LOG_LEVEL_WARN} == True"

This works, because ``CONFIG_BOOTLOADER_LOG_LEVEL_WARN`` is defined in the ESP-IDF project.

.. code-block:: yaml

    dependencies:
       example/cmp:
         version: "*"
         matches:
           - if: "$CONFIG{MY_OPTION} == True"

This does not work, because ``CONFIG_MY_OPTION`` is not defined in the ESP-IDF project.

.. code-block:: yaml

    dependencies:
       espressif/mdns:
          version: "1.8.1"

       example/cmp:
         version: "*"
         matches:
           - if: "$CONFIG{MDNS_MAX_SERVICES} == 10"

This works, because ``CONFIG_MDNS_MAX_SERVICES`` is defined in the ``espressif/mdns`` component, which is a direct dependency of your project.

.. code-block:: yaml

    dependencies:
       cmp_a:
          version: "*"

       example/cmp:
         version: "*"
         matches:
           - if: "$CONFIG{OPTION_FROM_CMP_B} == True"

This does not work, even if ``CONFIG_OPTION_FROM_CMP_B`` is defined in the ``cmp_b`` component and ``cmp_a`` depends on ``cmp_b``, because ``cmp_b`` is not a direct dependency of your project.

Local Directory Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are working on a component that is not yet published to the ESP Component Registry, you can add it as a dependency from a local directory. To specify a local dependency, at least one of the following attributes must be provided:

``path`` (local)
++++++++++++++++

The path to the local directory containing the dependency. You can use either a path relative to the ``idf_component.yml`` manifest file or an absolute path.

This field supports `environment variables`_.

Example:

.. code-block:: yaml

    dependencies:
      some_local_component:
        path: ../../projects/some_local_component

``override_path``
+++++++++++++++++

Use this field to override the component from the registry with a local one — for example, to define :ref:`example projects inside components <add-example-projects>`.

This field also supports `environment variables`_.

Example:

.. code-block:: yaml

    dependencies:
      some_local_component:
        override_path: ../../projects/some_local_component

.. _git-source:

Git Dependencies
~~~~~~~~~~~~~~~~

You can add dependencies from a Git repository by specifying the following attributes:

.. contents::
    :local:
    :depth: 1

``git``
+++++++

The URL of the Git repository. The URL must be a valid `Git remote URL <https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes>`_ or a path to a local Git repository.

This field is required when using Git dependencies.

Example:

.. code-block:: yaml

    dependencies:
      some_git_component:
        git: /home/user/projects/some_git_component.git
        # git: https://gitlab.com/user/components.git  # Remote repository

This field supports `environment variables`_. One common use case is providing authentication to Git repositories accessed via HTTPS:

.. code-block:: yaml

    dependencies:
      my_component:
        git: https://git:${ACCESS_TOKEN}@git.my_git.com/my_component.git

``path`` (Git)
++++++++++++++

The path to the component within the Git repository. The path is relative to the root directory of the repository. If omitted, the root directory is used as the component path.

This field supports `environment variables`_.

Example:

.. code-block:: yaml

    dependencies:
      # The component is located in /home/user/projects/some_git_component.git/some_git_component
      some_git_component:
        git: /home/user/projects/some_git_component.git
        path: some_git_component

``version`` (Git)
+++++++++++++++++

The version of the dependency. It can be specified by any valid Git reference: a tag, a branch, or a commit hash.

If omitted, the default branch of the Git repository is used.

Example:

.. code-block:: yaml

    dependencies:
      some_git_component:
        git: /home/user/projects/some_git_component.git
        version: feature/test  # Branch
        # version: v1.0.0       # Tag
        # version: 1234567890abcdef1234567890abcdef12345678  # Commit hash

.. _web-source:

ESP Component Registry Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If neither ``path``, ``override_path``, nor ``git`` attributes are specified, the Component Manager will attempt to resolve the dependency from the ESP Component Registry. Components in the registry are specified using the ``namespace/component_name`` format.

.. note::

    If you only need to specify the ``version`` field, you can use the following shorthand syntax:

    .. code-block:: yaml

        dependencies:
          component_name: ">=1.0"

    This is equivalent to:

    .. code-block:: yaml

        dependencies:
          espressif/component_name:
            version: ">=1.0"

``version`` (registry)
++++++++++++++++++++++

The version of the dependency.

This field is required and can either be a :ref:`specific version <versioning-scheme>` or a :ref:`version range <version-range-specifications>`.

Example:

.. code-block:: yaml

    dependencies:
      espressif/led_strip:
        version: ">=2.0"  # A version range
        # version: "2.0.0"  # A specific version

The default namespace for components in the ESP Component Registry is ``espressif``. You can omit the namespace part for components from the default namespace:

.. code-block:: yaml

    dependencies:
      led_strip:
        version: ">=2.0"

``pre_release``
+++++++++++++++

A boolean that indicates whether prerelease versions of the dependency should be used.

This field is optional.

Example:

.. code-block:: yaml

    dependencies:
      espressif/led_strip:
        version: ">=2.0"
        pre_release: true

By default, prerelease versions are ignored. You can also specify a prerelease version directly in the version string:

.. code-block:: yaml

    dependencies:
      espressif/led_strip:
        version: ">=2.0-beta.1"

``registry_url``
++++++++++++++++

The URL of the ESP Component Registry. By default, this URL is ``https://components.espressif.com``.

If you are uploading to the :ref:`staging registry <staging-registry>`, set the URL to ``https://components-staging.espressif.com`` to indicate that dependencies should be resolved from the staging registry instead of the main registry.

When uploading your component into the main registry, this URL should remain at the default value: ``https://components.espressif.com``. This ensures that all dependencies from the main registry are resolved correctly.

ESP-IDF Dependency
~~~~~~~~~~~~~~~~~~

Use the ``idf:version`` field to specify the ESP-IDF version that the component is compatible with.

You can specify either a :ref:`specific version <versioning-scheme>` or a :ref:`version range <version-range-specifications>`.

Example:

.. code-block:: yaml

    dependencies:
      idf:
        version: ">=5.0"

Shorthand syntax:

.. code-block:: yaml

    dependencies:
      idf: ">=5.0"
