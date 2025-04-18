########################
 Dependencies.lock File
########################

The ``dependencies.lock`` file is generated by the version solver and contains the exact versions of the selected components. It ensures reproducible builds by using the same component versions when the project is built in the future.

If your project includes only the :ref:`web-source` or :ref:`git-source`, it is recommended to check in the ``dependencies.lock`` file to ensure all developers use the same component versions when building locally.

If your project includes :ref:`local-source`, the ``dependencies.lock`` file should not be checked into version control. This is because the lock file will contain local paths specific to your environment, which are not available to other developers.

.. warning::

   The ``dependencies.lock`` file should not be manually edited. It should only be modified by the version solver.

*****************
 Root Attributes
*****************

``dependencies``
================

The ``dependencies`` attribute is a dictionary containing all the project's flattened dependencies. The keys represent the dependency names, and the values are explained in the `Dependency Attributes`_ section.

``direct_dependencies``
=======================

The ``direct_dependencies`` attribute is a list of the project's direct dependencies, meaning the dependencies that are directly specified in the project's manifest files. This list is used to ensure that the build system is re-triggered when a component is moved from :ref:`web-source` to :ref:`local-source`.

.. _manifest-hash:

``manifest_hash``
=================

The ``manifest_hash`` attribute is a hash of all the manifest files tracked in the project. This hash ensures that the ``dependencies.lock`` file is generated based on the latest manifest files.

.. _dependencies-lock-target:

``target``
==========

The ``target`` attribute specifies the target for which the ``dependencies.lock`` file was generated. This ensures that the :ref:`conditional-dependencies` are resolved correctly based on the current target.

``version``
===========

The ``version`` attribute indicates the version of the ``dependencies.lock`` file. It ensures that this version matches the version of the IDF Component Manager.

For example, IDF Component Manager 1.x uses version ``1.0.0`` for the ``dependencies.lock`` file, while IDF Component Manager 2.x uses version ``2.0.0``.

***********************
 Dependency Attributes
***********************

Each dependency in the ``dependencies`` dictionary has the following attributes:

``component_hash``
==================

The ``component_hash`` attribute is a hash of the component, ensuring that the component remains unchanged after the ``dependencies.lock`` file is generated.

``dependencies``
================

The ``dependencies`` attribute is a dictionary containing the direct dependencies of the component.

``source``
==========

The ``source`` attribute specifies the type of the component. For more details, please refer to the :ref:`component-dependencies` section.

``version``
===========

The ``version`` attribute indicates the version of the component selected by the :doc:`../guides/version_solver`.

``targets``
===========

The ``targets`` attribute lists the targets compatible with the component. This field can be omitted if the component is compatible with all targets.
