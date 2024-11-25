################
 Partial Mirror
################

.. note::

   This feature is available in version 2.1 and later.

A partial mirror contains only a subset of the components available in the main mirror. This can be useful when you have limited network connectivity or bandwidth, or when you want to restrict the versions of components available to your developers.

******************************
 Sync from Component Registry
******************************

To sync from the component registry, use the following command:

.. code:: shell

   compote registry sync --component <component> /path/to/mirror

For example, to sync the ``example/cmp`` component, use the following command:

.. code:: shell

   compote registry sync --component example/cmp /path/to/mirror

Sync with Version Range
=======================

This command will download all versions of the ``example/cmp`` component to the specified path.

To sync only specific versions of the component, specify the version range in the command:

.. code:: shell

   compote registry sync --component "example/cmp>=1.0.0,<4.0.0" /path/to/mirror

You can find the detailed version range syntax in the :ref:`version-range-specifications` section.

Sync Only the Latest Version
============================

To minimize the size of the mirror, you can sync only the latest version of the component:

.. code:: shell

   compote registry sync --component "example/cmp" --resolution latest /path/to/mirror

This command will download only the latest version of the ``example/cmp`` component to the specified path.

Sync all Components Required by Project
=======================================

To sync all components required by a project, specify the project directory instead of the components:

.. code:: shell

   compote registry sync --project-dir /path/to/project /path/to/mirror

To go through all the projects in the directory and sync the components required by each project, use the ``--recursive`` option:

.. code:: shell

   compote registry sync --project-dir /path/to/parent_directory --recursive /path/to/mirror

You can also use it with the ``--resolution latest`` option to sync only the latest versions of the components:

.. code:: shell

   compote registry sync --project-dir /path/to/parent_directory --recursive --resolution latest /path/to/mirror

.. note::

   You don't have to worry about components with different versions required by different projects when you're using ``--resolution latest``. The version solver will find the versions that satisfy the requirements of all the projects.

   For example, if project A requires ``example/cmp<3.1``, and project B requires ``example/cmp<4``, both versions ``3.0.3`` and ``3.3.9~1`` will be downloaded to the mirror to satisfy the requirements of both projects.

***********************************************************
 Apply to Configuration File ``idf_component_manager.yml``
***********************************************************

After the partial mirror is created, you can apply it to a profile in the :doc:`../reference/config_file` by adding the mirror URL to the ``local_storage_url`` field. For example, if your mirror is located at ``/opt/compote-mirror``, add the following to the configuration file:

.. code:: yaml

   profiles:
     default:
       local_storage_url:
         - file:///opt/compote-mirror

The version solver will look for the versions in the partial mirror before looking in the main mirror. For more information, see :ref:`url_precedence`.

You may also run a file server to serve the mirror. For example, to serve the mirror at ``http://localhost:9004``, add the following to the configuration file:

.. code:: yaml

   profiles:
     default:
       local_storage_url:
         - http://localhost:9004
