################
 Version Solver
################

This document describes how the version solver works in IDF Component Manager. The version solver is responsible for finding the best version of a component that satisfies the constraints of the project.

*****************
 Version Solving
*****************

An ESP-IDF project with component dependencies will specify those dependencies via one or more manifest files (e.g., ``idf_component.yml``), where each dependency will have a range representing the component version(s) of that dependency. Version solving is the process of collecting all component dependencies of an ESP-IDF project and calculating the most appropriate component version for each dependency. The version solving process generally involves the following steps:

#. Collect all the local manifest files from your main component and subcomponents.
#. Collect all the root dependencies from the manifest files.
#. Recursively collect all the available versions of each root dependency.
#. Calculate the version solving solution.

In IDF Component Manager, the version solver uses the `PubGrub <https://github.com/dart-lang/pub/blob/master/doc/solver.md>`_ algorithm to calculate the version solving solution. Once the version solving solution is calculated, the version solver generates a :doc:`../reference/dependencies_lock` that contains the exact versions of the components selected by the version solver.

When Will the Version Solver Run?
=================================

The version solver will be triggered by the ESP-IDF build system (i.e., ``idf.py reconfigure``) in the following scenarios:

#. When there is no ``dependencies.lock`` file present in the project root directory.

#. When the :ref:`manifest-hash` recorded in the :doc:`../reference/dependencies_lock` does not match the current manifest hash.

   A common scenario is when the user adds or removes a component from the project or modifies the manifest file of a component.

#. When the :ref:`dependencies-lock-target` recorded in the :doc:`../reference/dependencies_lock` does not match the current manifest target.

   A common scenario is when the user calls ``idf.py set-target`` to change the target.

#. When the user runs the project with a different ESP-IDF version.

#. When the user runs ``idf.py update-dependencies``.

Please note that the ``dependencies.lock`` file will only be updated when the output of the version solver differs from the current ``dependencies.lock`` file.

.. _update-dependencies:

Update Dependencies
===================

By default, the version solver will prefer to reuse the existing version of a component if it satisfies the constraints of the project. This approach helps reduce network traffic and speeds up the version solving process. If version solving fails, the solver will run without the presets and try to find the best version of the components.

To update the dependencies of the project, you can run the following command explicitly:

.. code:: console

   $ idf.py update-dependencies

Environment Variables for Version Solver
========================================

Some environment variables can be used to control the behavior of the version solver.

``IDF_COMPONENT_CHECK_NEW_VERSION``
-----------------------------------

By default, the IDF Component Manager checks for new versions of dependencies while compiling the ESP-IDF project, even if the version solver is not triggered.

If new versions are available, the version solver will print the new versions in the console without updating the ``dependencies.lock`` file.

To disable the check, you can set the environment variable ``IDF_COMPONENT_CHECK_NEW_VERSION`` to ``0``.

To update the dependencies of the project, you may refer to the :ref:`update-dependencies` section.
