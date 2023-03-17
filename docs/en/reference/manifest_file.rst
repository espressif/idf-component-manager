Manifest File ``idf_component.yml`` Format Reference
====================================================

The ``idf_component.yml`` file is a YAML file that describes the component. The file is located in the root directory of the component.

The file contains the following fields:

- ``dependencies``: A dictionary of dependencies of the component. This field is optional and can be omitted if the component does not have any dependencies.
- ``description``: A short description of the component. This field is optional.
- ``examples``: A list of directories with examples. This field is optional and can be omitted if all the component examples are located in the ``examples`` directory.
- ``files``: A dictionary containing two lists of ``include`` and ``exclude`` patterns. This field is optional and can be omitted if the component contains all files in the root directory with the default list of exceptions.
- ``maintainers``: A list of maintainers of the component, while format is not fixed, we recommend using the ``First Last <email@example.com>`` format. This field is optional.
- ``tags``: A list of tags related to the component functionality. This field is optional.
- ``targets``: A list of targets that the component supports. This field is optional and can be omitted if the component supports all targets.
- ``version``: The version of the component. This field is always present for a component in the component registry. At the same time, it is optional for components in the local component directory or in git.

External Links:

- ``discussion``: The URL of the component discussion forum or chat, i.e., Discord, Gitter, etc. This field is optional.
- ``documentation``: The URL of the component documentation, if it is not included in the component itself. This field is optional.
- ``issues``: The URL of the component issue tracker. This field is optional.
- ``repository``: The URL of the component repository. This field is optional, but highly recommended.
- ``url``: The homepage of the component. This field is optional.

All links should be correct HTTP(S) URLs like ``https://example.com/path`` except for the ``repository`` field, which is expected to be a valid [Git remote](https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes) URL.

Dependencies
------------

Dependencies are specified in the ``dependencies`` field of the manifest file. The field is a dictionary of dependencies, where the key is the name of the dependency.

Component manager supports several sources of dependencies: local directory, git repository, and component registry.

Common Fields for All Dependency Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``version``: The version of the dependency. This field is optional and can be omitted if the dependency is in a local directory.
- ``pre_release``: A boolean flag that indicates whether the prerelease versions of the dependency should be used.
- ``require``: Specifies component visibility. Possible values are:
   - ``private``: This is the default value. The required component is added as a private dependency. This is equivalent to adding the component to the ``PRIV_REQUIRES`` argument of ``idf_component_register`` in the component's ``CMakeLists.txt`` file.
   - ``public``: Sets the transient dependency. This is equivalent to adding the component to the ``REQUIRES`` argument of ``idf_component_register`` in the component's ``CMakeLists.txt`` file.
   - ``no``: Can be used to only download the component but not add it as a requirement.
- ``rules``: A list of rules that should be applied to the dependency. The rules are applied in the order they are specified in the list. The dependency is only included when all rules are true. More details on :ref:`rules<reference/manifest_file:Rules>`.

Dependencies from the Component Registry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Components in the component registry are specified by their name in the ``namespace/component_name`` format. The version of the dependency is specified in the ``version`` field of the dependency.

.. code-block:: yaml

    dependencies:
      namespace/component_name:
        version: ">=1.0"

You can use the shorthand syntax to specify the version of the dependency:

.. code-block:: yaml

    dependencies:
      namespace/component_name: ">=1.0"

For components in the default namespace ``espressif``, you can omit the namespace part:

.. code-block:: yaml

    dependencies:
      led_strip: "^2.0"

This will be equivalent to:

.. code-block:: yaml

    dependencies:
      espressif/led_strip: "^2.0"

Override Path
^^^^^^^^^^^^^

Dependencies from the component registry may also contain the ``override_path`` field. You can specify a local path in this field, and it will be used instead of the one downloaded from the registry. This field is mainly used for :ref:`example projects inside components<guides/packaging_components:Add example projects>`.

Dependencies from Local Directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you work on a component that is not yet published to the component registry, you can add it as a dependency from a local directory. The dependency is specified by the ``path`` field of the dependency. The path is relative to the ``idf_component.yml`` manifest file. You can use absolute paths as well.

.. code-block:: yaml

    dependencies:
      some_local_component:
        path: ../../projects/component

Dependencies from Git
~~~~~~~~~~~~~~~~~~~~~

You can add dependencies from a Git repository by specifying the ``git`` field of the dependency. It is possible to specify the Git repository by its URL or by its path on the local file system.

Dependencies from Git support two additional fields:

- ``path`` field can be used to specify the path to the component in the Git repository. The path is relative to the root directory of the Git repository. If the ``path`` field is omitted, the root directory of the Git repository is used as the path to the component.
- ``version`` field can be used to specify the version of the dependency. The version of a Git dependency can be specified by any valid Git reference: a tag, a branch, or a commit hash. If the ``version`` field is omitted, the default branch of the Git repository is used.


.. note::

    ``version`` and ``path`` fields of Git dependencies have a different meaning than the same fields of dependencies from the component registry or local dependencies.

.. code-block:: yaml

    dependencies:
      test_component:
        version: feature/test
        path: test_component
        git: ssh://git@gitlab.com/user/components.git


ESP-IDF Version
---------------

The ``esp-idf`` dependency is a special case. It is used to specify the version of ESP-IDF that the component is compatible with. The version is specified in the ``version`` field of the ``esp-idf`` dependency.

.. code-block:: yaml

    dependencies:
      esp-idf:
        version: ">=5.0"

You can use the shorthand syntax to specify the version of ESP-IDF:

.. code-block:: yaml

    dependencies:
      esp-idf: ">=5.0"

Rules
-----

Rules are specified in the ``rules`` field of the dependency. The field is a list of rules, where each rule is a dictionary with an ``if`` field. The dependency is only included when all if clauses are true.

The ``if`` field supports ``idf_version`` and ``target`` variables. The ``idf_version`` variable contains the version of ESP-IDF that is used to build the component. The ``target`` variable contains the current target selected for the project.

The ``if`` field supports all :ref:`Range Specifications<reference/versioning:Range Specifications>`. It also supports the ``in`` and ``not in`` operators, which can be used to check if the value is in the list of values.

.. code-block:: yaml

   dependencies:
     optional_component:
      version: "~1.0.0"
      rules:
        - if: "idf_version >=3.3,<5.0"
        - if: "target in [esp32, esp32c3]"

Examples
--------

Examples from the ``examples`` directory are handled automatically. If you want to add examples from other directories, you can specify them in the ``examples`` field of the manifest file.

The ``examples`` field is a list of directories with examples. Each directory is specified as a dictionary with the ``path`` field.

.. code-block:: yaml

   examples:
     - path: ../some/path
     - path: ../some/other_path

Please check the :ref:`example projects guide<guides/packaging_components:Add example projects>` for more details.

Choosing What Files to Upload
-----------------------------

As a component developer, you may want to choose which files from the component directory will be uploaded to the registry. Your ``idf_component.yml`` manifest may include and exclude filters. For example:

.. code:: yaml

    files:
      exclude:
        - "*.py" # Exclude all Python files
        - "**/*.list" # Exclude `.list` files in all directories
        - "big_dir/**/*" # Exclude files in `big_dir` directory (but the empty directory will be added to the archive anyway)
      include:
        - "**/.DS_Store" # Include files excluded by default



.. collapse:: List of files and directories excluded by default

    .. code:: python

         [
              # Python files
              '**/__pycache__',
              '**/*.pyc',
              '**/*.pyd',
              '**/*.pyo',
              # macOS files
              '**/.DS_Store',
              # Git
              '**/.git/**/*',
              # SVN
              '**/.svn/**/*',
              # dist and build artefacts
              '**/dist/**/*',
              '**/build/**/*',
              # artifacts from example projects
              '**/managed_components/**/*',
              '**/dependencies.lock',
              # CI files
              '**/.github/**/*',
              '**/.gitlab-ci.yml',
              # IDE files
              '**/.idea/**/*',
              '**/.vscode/**/*',
              # Configs
              '**/.settings/**/*',
              '**/sdkconfig',
              '**/sdkconfig.old',
              # Hash file
              '**/.component_hash'
          ]

.. note::

    The file field is only taken into account during the preparation of the archive before uploading to the registry.

Environment Variables in Manifest
---------------------------------

You can use environment variables in values in ``idf_component.yml`` manifests. ``$VAR`` or ``${VAR}`` is replaced with the value of the ``VAR`` environment variable. If the environment variable is not defined, the component manager will raise an error.

Variable names should be ASCII alphanumeric strings (including underscores) and start with an underscore or ASCII letter. The first non-identifier character after the ``$`` terminates this placeholder specification. You can escape ``$`` with one more ``$`` character, i.e., ``$$`` is replaced with ``$``.

One possible use-case is providing authentication to Git repositories accessed through HTTPS:

.. code-block:: yaml

   dependencies:
    my_component:
      git: https://git:${ACCESS_TOKEN}@git.my_git.com/my_component.git


Special Rules
-------------

Ignore Prerelease Versions by Default
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Normally, the version solver would skip the prerelease versions while collecting all the available versions of each dependency. To use the prerelease versions for one dependency, please either include the prerelease field in the range specification, or add the keyword ``pre_release: true``.

For example:

.. code-block:: yaml

   dependencies:
     namespace/pre_release_component:
       version: "*"
       pre_release: true

Or

.. code-block:: yaml

   dependencies:
     namespace/pre_release_component:
       version: "~1.0.0-a1"


Local Dependencies First
~~~~~~~~~~~~~~~~~~~~~~~~
.. versionadded:: 1.3.0

While collecting the root dependencies, local file system components are given precedence.

For example, this is our main component `idf_component.yml`:

.. code-block:: yaml

   dependencies:
     test/dependency_b: "==1.0.0"
     test/dependency_a:
       path: '../test__dependency_a'

``test/dependency_b`` 1.0.0 version depends on ``test/dependency_a``. When a local component with the same name is defined, we would replace the dependency of all collected component versions with this local one. The final dependency chain would be:

- ``root`` depends on ``test/dependency_a (local)``
- ``root`` depends on ``test/dependency_b (1.0.0)``
- ``test/dependency_b (1.0.0)`` replaces the original dependency ``test/dependency_a (2.0.0)`` with ``test/dependency_a (local)``
