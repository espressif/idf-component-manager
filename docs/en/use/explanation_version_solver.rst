###################################
 Explanation of the Version Solver
###################################

This document describes how the version solver works in the IDF Component Manager. The version solver is responsible for determining the best component versions that satisfy the constraints defined in your project.

*****************
 Version Solving
*****************

An ESP-IDF project declares its component dependencies through one or more manifest files (e.g., ``idf_component.yml``), where each dependency specifies a version or version range.

Version solving is the process of analyzing all component dependencies and determining the most suitable component version for each one. This process involves the following steps:

1. Collect all local manifest files from your main component and subcomponents.
2. Collect all root dependencies defined in those manifest files.
3. Recursively collect all available versions for each root dependency.
4. Calculate the final set of resolved component versions.

The IDF Component Manager uses the `PubGrub <https://github.com/dart-lang/pub/blob/master/doc/solver.md>`_ algorithm to perform version solving. Once completed, the solver generates a :doc:`../../reference/dependencies_lock` file that records the exact versions of the components selected by the version solver.

When Will the Version Solver Run?
=================================

The version solver is triggered by the ESP-IDF build system (e.g., via ``idf.py reconfigure``) under the following conditions:

1. When there is no ``dependencies.lock`` file in the project root.
2. When the :ref:`manifest-hash` in the existing :doc:`../../reference/dependencies_lock` file does not match the current manifest hash.

   This can happen when components are added or removed, or when a manifest is modified.

3. When the :ref:`dependencies-lock-target` in the :doc:`../../reference/dependencies_lock` does not match the current manifest target.

   A common case is when the user runs ``idf.py set-target`` to change the target.

4. When the user runs the project with a different ESP-IDF version.
5. When the user runs ``idf.py update-dependencies``.

Note: The ``dependencies.lock`` file will only be updated if the version solver produces a different result than the current contents.

.. _update-dependencies:

Update Dependencies
===================

By default, the version solver prefers to reuse component versions that already satisfy the constraints. This speeds up solving and reduces network usage.

If the solver fails to find a valid solution using the current versions, it will retry without using any presets to determine a suitable set of versions.

To manually update all dependencies, run:

.. code-block:: console

    $ idf.py update-dependencies

Environment Variables for the Version Solver
============================================

Some environment variables can be used to control the behavior of the version solver.

``IDF_COMPONENT_CHECK_NEW_VERSION``
-----------------------------------

By default, the IDF Component Manager checks for new versions of dependencies during the ESP-IDF project build process, even if the version solver is not triggered.

If newer versions are found, they will be displayed in the console, but the ``dependencies.lock`` file will remain unchanged.

To disable this automatic version check, set the following environment variable ``IDF_COMPONENT_CHECK_NEW_VERSION`` to ``0``.

For instructions on explicitly updating dependencies, refer to the :ref:`update-dependencies` section.

``IDF_COMPONENT_CONSTRAINT_FILES``
----------------------------------

You can use constraint files to limit the versions of components that the version solver considers during dependency resolution.

When constraint files are specified, the version solver will check the version range not only from the ``dependencies`` section in the manifest files, but also from the constraint files.

To use constraint files, set the ``IDF_COMPONENT_CONSTRAINT_FILES`` environment variable to one or more constraint file paths separated by semicolons:

.. code-block:: console

    # Single constraint file
    $ export IDF_COMPONENT_CONSTRAINT_FILES="/path/to/constraints.txt"

    # Multiple constraint files (semicolon-separated)
    $ export IDF_COMPONENT_CONSTRAINT_FILES="/path/to/base_constraints.txt;/path/to/project_constraints.txt"

Constraint File Format
^^^^^^^^^^^^^^^^^^^^^^

Constraint files use a simple text format where each line specifies a component name and version constraint:

.. code-block:: text

    # This is a comment
    espressif/esp_timer>=1.0.0
    wifi_provisioning~=2.1.0
    my_namespace/custom_component>=0.5.0,<1.0.0

    # Components without namespace default to espressif namespace
    led_strip==1.2.0

Version constraints follow the same format as dependency specifications in manifest files. For detailed information about supported version constraint formats, see :ref:`version-range-specifications`.

Multiple Constraint Files
^^^^^^^^^^^^^^^^^^^^^^^^^

When multiple constraint files are specified, they are processed in order and later files override constraints from earlier files for the same component.

.. code-block:: console

    # Example: base constraints + project overrides
    $ export IDF_COMPONENT_CONSTRAINT_FILES="org_constraints.txt;project_constraints.txt"

If ``org_constraints.txt`` contains ``example/cmp>=1.0.0`` and ``project_constraints.txt`` contains ``example/cmp==1.2.3``, the final constraint will be ``example/cmp==1.2.3``.

``IDF_COMPONENT_CONSTRAINTS``
-----------------------------

Moreover, you can specify component constraints directly in the environment variable ``IDF_COMPONENT_CONSTRAINTS``. This allows you to define version constraints without needing to create a separate constraint file.

.. note::

    The ``IDF_COMPONENT_CONSTRAINTS`` environment variable has higher priority than the ``IDF_COMPONENT_CONSTRAINT_FILES`` variable. If both are set, the constraints in ``IDF_COMPONENT_CONSTRAINTS`` will override those specified in the constraint files if the same component is listed in both.

.. note::

    The ``IDF_COMPONENT_CONSTRAINTS`` environment variable does NOT support comments.

.. code-block:: console

    # Single constraint
    $ export IDF_COMPONENT_CONSTRAINTS="espressif/esp_timer>=1.0.0"

    # Multiple constraints (separated by newlines or semicolons)
    $ export IDF_COMPONENT_CONSTRAINTS="espressif/esp_timer>=1.0.0;wifi_provisioning~=2.1.0"

    # Using newlines (in shell)
    $ export IDF_COMPONENT_CONSTRAINTS="espressif/esp_timer>=1.0.0
    wifi_provisioning~=2.1.0
    my_namespace/custom_component>=0.5.0,<1.0.0"

The constraint format is the same as in constraint files. Components without a namespace default to the ``espressif`` namespace.
