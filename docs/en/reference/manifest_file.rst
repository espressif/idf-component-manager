#####################################
 ``idf_component.yml`` Manifest File
#####################################

This reference manual describes the attributes of the ``idf_component.yml`` manifest file. The manifest file is used to describe the component and its dependencies. The file is located in the root directory of the component.

.. contents::
   :local:
   :depth: 1

**************************
 Build-Related Attributes
**************************

Here is a list of attributes that affects the build process. These attributes are the most important when working with the component manager.

``targets``
===========

A list of targets that the component supports. The field is optional and can be omitted if the component supports all targets.

Example:

.. code:: yaml

   targets:
     - esp32
     - esp32c3

``dependencies``
================

A dictionary of dependencies of the component. This field is optional and can be omitted if the component does not have any dependencies. The detailed usage is described in the `component dependencies`_ section.

*********************
 Metadata Attributes
*********************

Here is a list of attributes that provide additional information about the component. These attributes are only used when the component is uploaded to the ESP Component Registry.

``version``
===========

The version of the component. The version should follow the :ref:`versioning scheme <reference/versioning:Versioning Scheme>`.

This field is required when uploading the component to the ESP Component Registry. You may declare the version by:

-  specifying the version in the ``idf_component.yml`` file
-  tagging the commit in the Git repository with the version number
-  pass the version as an argument to the ``compote component upload --version [version]`` command

Example:

.. code:: yaml

   version: "1.0.0"

``maintainers``
===============

A list of maintainers of the component. The field is optional.

Example:

.. code:: yaml

   maintainers:
     - First Last <email@example.com>

``description``
===============

A brief description of the component. This field is optional, but highly recommended. If it's missing, a warning message will appear when the component is uploaded to the registry.

Example:

.. code:: yaml

   description: "This is a component that does something useful."

``license``
===========

The license of the component. It should be a valid SPDX license identifier listed in https://spdx.org/licenses/.

This field is optional.

If not specified, the license will be automatically detected according to the ``LICENSE``, or ``LICENSE.txt`` file in the component directory if it exists.

Example:

.. code:: yaml

   license: "MIT"

``tags``
========

A list of keywords related to the component functionality. This field is optional.

Example:

.. code:: yaml

   tags:
     - wifi
     - networking

``files``
=========

A dictionary containing two lists of ``include`` and ``exclude`` patterns. This field is optional and can be omitted if the component contains all files in the root directory with the default list of exceptions.

Example:

.. code:: yaml

   files:
     exclude:
       - "*.py" # Exclude all Python files
       - "**/*.list" # Exclude `.list` files in all directories
       - "big_dir/**/*" # Exclude files in `big_dir` directory (but the empty directory will be added to the archive anyway)
     include:
       - "**/.DS_Store" # Include files excluded by default

.. collapse:: Click to expand the list of files and directories excluded by default

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

   The ``file`` field is only taken into account during the preparation of the archive before uploading to the registry.

``examples``
============

A list of directories with examples. This field is optional and can be omitted if all the component examples are located in the ``examples`` directory.

Example:

.. code:: yaml

   examples:
     - custom_example_path_1
     - custom_example_path_2
     # - examples/foo  # no need to be listed if the example is under "examples" folder

``url``
=======

The homepage of the component. This field is optional, but highly recommended. If it's missing, a warning message will appear when the component is uploaded to the registry.

Example:

.. code:: yaml

   url: "https://example.com"

``repository``
==============

The URL of the component repository. This field is optional, but highly recommended. The repository URL should be a valid `Git remote URL <https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes>`_. Could be passed as an argument to the ``compote component upload --repository [repository]`` command.

Example:

.. code:: yaml

   repository: "https://example.com/component.git"

If your component is not at the root of the repository, you can specify the path to the component in the repository with an additional field ``repository_info``.

.. code:: yaml

   repository: "https://example.com/component.git"
   repository_info:
     commit_sha: "1234567890abcdef1234567890abcdef12345678"
     path: "path/to/component"

``commit_sha``
==============

The commit SHA of the component. This field is optional. Must be used together with the ``repository`` field. Could be passed as an argument to the ``compote component upload --commit-sha [commit_sha]`` command. Could be placed under the ``repository_info`` field.

Example:

.. code:: yaml

   commit_sha: "1234567890abcdef1234567890abcdef12345678"

Or (recommended):

.. code:: yaml

   repository_info:
     commit_sha: "1234567890abcdef1234567890abcdef12345678"

``documentation``
=================

The URL of the component documentation. This field is optional.

Example:

.. code:: yaml

   documentation: "https://docs.example.com"

``issues``
==========

The URL of the component issue tracker. This field is optional.

Example:

.. code:: yaml

   issues: "https://issues.example.com"

``discussion``
==============

The URL of the component discussion forum or chat. This field is optional.

Example:

.. code:: yaml

   discussion: "https://chat.example.com"

************************
 Component Dependencies
************************

Dependencies are specified in the ``dependencies`` field of the manifest file. The field is a dictionary of dependencies, where the key is the name of the dependency.

Component manager supports several sources of dependencies: `Local Directory Dependencies`_, `Git Dependencies`_, `ESP Component Registry Dependencies`_, and `ESP-IDF Dependency`_.

.. warning::

   `Local Directory Dependencies`_ and `Git Dependencies`_ are not supported when uploading the component to the ESP Component Registry.

Local Directory Dependencies
============================

If you work on a component that is not yet published to the ESP Component Registry, you can add it as a dependency from a local directory. To specify a local dependency, at least one of the following attributes should be specified:

``path`` (local)
----------------

The path to the local directory containing the dependency. The path is relative to the ``idf_component.yml`` manifest file. You can use absolute paths as well.

Example:

.. code:: yaml

   dependencies:
     some_local_component:
        path: ../../projects/some_local_component

This field supports `environment variables`_.

``override_path``
-----------------

This field is mainly used for :ref:`example projects inside components <guides/packaging_components:Add example projects>`. You can specify a local path in this field, and it will be used instead of the one downloaded from the registry.

Example:

.. code:: yaml

   dependencies:
     some_local_component:
       override_path: ../../projects/some_local_component

This field supports `environment variables`_.

Git Dependencies
================

You can add dependencies from a Git repository by specifying the following attributes:

``git``
-------

The URL of the Git repository. The URL should be a valid `Git remote URL <https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes>`_ or a path to the local Git repository. This field is required for Git dependencies.

Example:

.. code:: yaml

   dependencies:
     some_git_component:
       git: /home/user/projects/some_git_component.git
       # git: https://gitlab.com/user/components.git # remote repository

This field supports `environment variables`_. One possible use-case is providing authentication to Git repositories accessed through HTTPS:

.. code:: yaml

   dependencies:
    my_component:
      git: https://git:${ACCESS_TOKEN}@git.my_git.com/my_component.git

``path`` (git)
--------------

The path to the component in the Git repository. The path is relative to the root directory of the Git repository. If the ``path`` field is omitted, the root directory of the Git repository is used as the path to the component.

Example:

.. code:: yaml

   dependencies:
     # The component is located in /home/user/projects/some_git_component.git/some_git_component
     some_git_component:
       git: /home/user/projects/some_git_component.git
       path: some_git_component

This field supports `environment variables`_.

``version`` (git)
-----------------

The version of the dependency. The version of a Git dependency can be specified by any valid Git reference: a tag, a branch, or a commit hash. If the ``version`` field is omitted, the default branch of the Git repository is used.

Example:

.. code:: yaml

   dependencies:
     some_git_component:
       git: /home/user/projects/some_git_component.git
       version: feature/test  # branch
       # version: v1.0.0  # tag
       # version: 1234567890abcdef1234567890abcdef12345678  # commit hash

ESP Component Registry Dependencies
===================================

If no ``path``, ``override_path``, or ``git`` attributes are specified, the component manager will try to resolve the dependency from the ESP Component Registry. Components in the ESP Component Registry are specified by their name in the ``namespace/component_name`` format. You may specify the following attributes:

``version`` (registry)
----------------------

The version of the dependency. This field is required and could be either a :ref:`specific version <reference/versioning:Versioning Scheme>` or a :ref:`version range <reference/versioning:Range Specifications>`.

Example:

.. code:: yaml

   dependencies:
     espressif/led_strip:
       version: ">=2.0"  # a version range
       # version: "2.0.0"  # a specific version

.. note::

   The default namespace for components in the ESP Component Registry is ``espressif``. You can omit the namespace part for components in the default namespace. For example, the following code is equivalent to the previous example:

   .. code:: yaml

      dependencies:
        led_strip:
          version: ">=2.0"

``pre_release``
---------------

A boolean flag that indicates whether the prerelease versions of the dependency should be used. This field is optional and can be omitted. By default, the prerelease versions are ignored.

Example:

.. code:: yaml

   dependencies:
     espressif/led_strip:
       version: ">=2.0"
       pre_release: true

Or you may include the prerelease field in the version string to specify the prerelease version:

.. code:: yaml

   dependencies:
     espressif/led_strip:
       version: ">=2.0-beta.1"

Shorthand Syntax
----------------

You can use the shorthand syntax to specify the version of the dependency if there's only ``version`` field specified:

.. code:: yaml

   dependencies:
     espressif/component_name:
       version: ">=1.0"

is equivalent to:

.. code:: yaml

   dependencies:
     component_name: ">=1.0"

ESP-IDF Dependency
==================

The ``idf`` dependency is a special case. It is used to specify the version of ESP-IDF that the component is compatible with. The version is specified in the ``version`` field of the ``idf`` dependency, and could be either a :ref:`specific version <reference/versioning:Versioning Scheme>` or a :ref:`version range <reference/versioning:Range Specifications>`.

.. code:: yaml

   dependencies:
     idf:
       version: ">=5.0"

You can use the shorthand syntax to specify the version of ESP-IDF:

.. code:: yaml

   dependencies:
     idf: ">=5.0"

Common Fields for All Dependency Types
======================================

The following attributes are supported for all types of dependencies. They are optional and can be omitted if not needed.

``require``
-----------

A string specifies component visibility. Possible values are:

-  ``private``: This is the default value. The required component is added as a private dependency. This is equivalent to adding the component to the ``PRIV_REQUIRES`` argument of ``idf_component_register`` in the component's ``CMakeLists.txt`` file.
-  ``public``: Sets the transient dependency. This is equivalent to adding the component to the ``REQUIRES`` argument of ``idf_component_register`` in the component's ``CMakeLists.txt`` file.
-  ``no``: Can be used to only download the component but not add it as a requirement.

Example:

.. code:: yaml

   require: public
   # require: private # by default

``matches``
-----------

A list of `conditional dependencies`_ that should be applied to the dependency. The dependency is only included when any of the if-clauses is true.

``rules``
---------

A list of `conditional dependencies`_ that should be applied to the dependency. The dependency is only included when all of the if-clauses are true.

**************************
 Conditional Dependencies
**************************

``matches`` and ``rules`` attributes are specified to control the dependency inclusion. The dependency is only included when:

-  any of the if clauses in ``matches`` is true
-  all of the if clauses in ``rules`` are true

``matches`` and ``rules`` are optional attributes. If they are omitted, the dependency is always included.

``matches`` and ``rules`` support the same syntax. The field is a list of conditional dependencies. Each conditional dependency has an ``if`` field, and an optional ``version`` field.

``if``
======

The ``if`` field is a boolean expression that is evaluated to determine if the dependency should be included. An expression consists of three parts: left value, operator, and right value.

The left value could be

-  keyword ``idf_version``: the version of ESP-IDF that is used to build the component
-  keyword ``target``: the current target selected for the project
-  a string
-  `environment variables`_

The right value could be

-  a string
-  a list of strings

The operator to compare with a string could be

-  ``<=``
-  ``<``
-  ``>=``
-  ``>``
-  ``~=``
-  ``~``
-  ``=``
-  ``^``
-  ``!=``
-  ``==``

The operator to compare with a list of strings could be

-  ``not in``
-  ``in``

To make a complex boolean expression, you can use nested parentheses with boolean operators ``&&`` and ``||``.

.. code:: yaml

   dependencies:
     optional_component:
      version: "~1.0.0"
      rules:
        - if: "idf_version >=3.3,<5.0"
        - if: "target in [esp32, esp32c3]"
        # the above two conditions equals to
        - if: idf_version >=3.3,<5.0 && target in [esp32, esp32c3]

The left value of the if clause could be `environment variables`_. If the environment variable is not set, an error will be raised.

One possible use-case is to test it in the CI/CD pipeline. For example:

.. code:: yaml

   dependencies:
     optional_component:
       matches:
         - if: "$TESTING_COMPONENT in [foo, bar]"

The dependency will only be included when the environment variable ``TESTING_COMPONENT`` is set to ``foo`` or ``bar``.

``version`` (if clause)
=======================

The ``version`` field is optional, and it could be either a :ref:`specific version <reference/versioning:Versioning Scheme>` or a :ref:`version range <reference/versioning:Range Specifications>`. The version specified here will override the ``version`` field of the dependency when the corresponding if clause is true.

For example,

.. code:: yaml

   dependencies:
     optional_component:
       matches:
         - if: "idf_version >=3.3"
           version: "~2.0.0"
         - if: "idf_version <3.3"
           version: "~1.0.0"

The ``optional_component`` will be included with version ``~2.0.0`` when the ``idf_version >=3.3``, and it will be included with version ``~1.0.0`` when the ``idf_version <3.3``.

***********************
 Environment Variables
***********************

.. warning::

   Environment variables are not allowed in manifests when uploading components to the ESP Component Registry.

You can use environment variables for the attributes that support them. The component manager will replace the environment variables with their values. Follow the syntax:

-  ``$VAR``
-  ``${VAR}``

To escape the dollar sign, use two dollar signs, for example, ``$$VAR`` will be replaced with ``$VAR``, but not with the value of the environment variable ``VAR``.
