###############################################
 How to Add a Dependency to an ESP-IDF Project
###############################################

This page shows how to add a component dependency to your ESP-IDF project.

***************
 Prerequisites
***************

- An ESP-IDF project with the ESP-IDF environment activated.

******************
 Add a dependency
******************

From your project directory, run:

.. code-block:: console

    $ idf.py add-dependency example/cmp^3.3.8

This adds the dependency to your project's manifest (typically ``main/idf_component.yml``).

*******************************************
 Add a dependency from a specific registry
*******************************************

If you need to pull from a registry other than the default, set the registry URL for the command:

.. code-block:: console

    $ idf.py add-dependency --registry-url https://components-staging.espressif.com example/cmp^3.3.8

This writes a ``registry_url`` for the dependency into the manifest.

***************************
 Add a dependency from Git
***************************

To add a dependency sourced from a Git repository, provide ``--git`` and optionally ``--git-path`` and ``--git-ref``:

.. code-block:: console

    $ idf.py add-dependency my_component --git https://github.com/<org>/<repo>.git --git-path components/my_component --git-ref v1.2.3

*********
 Related
*********

- Manifest file format and version specs: :doc:`/reference/manifest_file`
- Version range syntax: :doc:`/reference/versioning`
- How dependency solving and lockfiles work: :doc:`/use/explanation_version_solver`
