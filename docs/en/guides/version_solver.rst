################
 Version Solver
################

This document describes how the version solver works in the IDF Component Manager. The version solver is responsible for determining the best component versions that satisfy the constraints defined in your project.

*****************
 Version Solving
*****************

An ESP-IDF project declares its component dependencies through one or more manifest files (e.g., ``idf_component.yml``), where each dependency specifies a version or version range.

Version solving is the process of analyzing all component dependencies and determining the most suitable component version for each one. This process involves the following steps:

#. Collect all local manifest files from your main component and subcomponents.
#. Collect all root dependencies defined in those manifest files.
#. Recursively collect all available versions for each root dependency.
#. Calculate the final set of resolved component versions.

The IDF Component Manager uses the `PubGrub <https://github.com/dart-lang/pub/blob/master/doc/solver.md>`_ algorithm to perform version solving. Once completed, the solver generates a :doc:`../reference/dependencies_lock` file that records the exact versions of the components selected by the version solver.

When Will the Version Solver Run?
=================================

The version solver is triggered by the ESP-IDF build system (e.g., via ``idf.py reconfigure``) under the following conditions:

#. When there is no ``dependencies.lock`` file in the project root.

#. When the :ref:`manifest-hash` in the existing :doc:`../reference/dependencies_lock` file does not match the current manifest hash.

   This can happen when components are added or removed, or when a manifest is modified.

#. When the :ref:`dependencies-lock-target` in the :doc:`../reference/dependencies_lock` does not match the current manifest target.

   A common case is when the user runs ``idf.py set-target`` to change the target.

#. When the user runs the project with a different ESP-IDF version.

#. When the user runs ``idf.py update-dependencies``.

Note: The ``dependencies.lock`` file will only be updated if the version solver produces a different result than the current contents.

.. _update-dependencies:

Update Dependencies
===================

By default, the version solver prefers to reuse component versions that already satisfy the constraints. This speeds up solving and reduces network usage.

If the solver fails to find a valid solution using the current versions, it will retry without using any presets to determine a suitable set of versions.

To manually update all dependencies, run:

.. code:: console

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
