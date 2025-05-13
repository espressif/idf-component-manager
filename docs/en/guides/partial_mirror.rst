################
 Partial Mirror
################

.. note::

   This feature is available in version 2.1 and later.

A partial mirror contains only a subset of the components available in the main mirror. This is useful when you have limited network connectivity or bandwidth, or when you want to restrict which versions of components are available to your developers.

******************************
 Sync from Component Registry
******************************

To sync from the component registry, use the following command:

.. code:: shell

   compote registry sync --component <component> /path/to/mirror

For example, to sync the ``example/cmp`` component, use the command:

.. code:: shell

   compote registry sync --component example/cmp /path/to/mirror

Sync with a Version Range
=========================

This command downloads all versions of the ``example/cmp`` component to the specified path.

To sync only specific versions of the component, provide a version range:

.. code:: shell

   compote registry sync --component "example/cmp>=1.0.0,<4.0.0" /path/to/mirror

You can find detailed version range syntax in the :ref:`version-range-specifications` section.

Sync Only the Latest Version
============================

To minimize the mirror size, you can sync only the latest version of the component:

.. code:: shell

   compote registry sync --component "example/cmp" --resolution latest /path/to/mirror

This command downloads only the most recent version of the ``example/cmp`` component to the specified path.

Sync All Components Required by a Project
=========================================

To sync all components required by a project, specify the project directory instead of individual components:

.. code:: shell

   compote registry sync --project-dir /path/to/project /path/to/mirror

To scan all projects in a directory and sync the components required by each one, use the ``--recursive`` option:

.. code:: shell

   compote registry sync --project-dir /path/to/parent_directory --recursive /path/to/mirror

You can also use it with the ``--resolution latest`` option to sync only the latest versions of each component:

.. code:: shell

   compote registry sync --project-dir /path/to/parent_directory --recursive --resolution latest /path/to/mirror

.. note::

   You don’t need to worry about components required in different versions by different projects when using ``--resolution latest``. The version solver will find versions that satisfy all project requirements.

   For example, if project A requires ``example/cmp<3.1`` and project B requires ``example/cmp<4``, then both versions ``3.0.3`` and ``3.3.9~1`` will be downloaded to the mirror to fulfill the dependencies.

***********************************************************
 Apply to Configuration File ``idf_component_manager.yml``
***********************************************************

After creating the partial mirror, apply it to a profile in the :doc:`../reference/config_file` by adding the mirror URL to the ``local_storage_url`` field. For example, if your mirror is located at ``/opt/compote-mirror``, update the configuration file like this:

.. code:: yaml

   profiles:
     default:
       local_storage_url:
         - file:///opt/compote-mirror

The version solver will check the versions in the partial mirror before looking in the main mirror. For more information, see :ref:`url_precedence`.

You can also serve the mirror using a file server. For example, to serve it at ``http://localhost:9004``, update the configuration file as follows:

.. code:: yaml

   profiles:
     default:
       local_storage_url:
         - http://localhost:9004
