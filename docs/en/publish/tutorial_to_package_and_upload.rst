#####################################################
 Tutorial to Package and Upload an ESP-IDF Component
#####################################################

This tutorial walks through packaging a simple ESP-IDF component and uploading it to the `ESP Component Registry <https://components.espressif.com>`_.

******************
 Expected outcome
******************

By the end of this tutorial, you will have:

- A component directory with the required packaging metadata (manifest, README, license)
- A version uploaded to the staging registry for testing
- Optionally, the same version uploaded to the production registry for general use

***************
 Prerequisites
***************

This tutorial assumes you already have ESP-IDF installed. If not, follow the `ESP-IDF Get Started Guide <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/index.html>`_.

You also need:

- A GitHub account (used to authenticate to the registry)
- The ``compote`` CLI available in your ESP-IDF environment

************************************
 Stage 1: Create a simple component
************************************

You can create a new ESP-IDF component using the following command:

.. code-block:: shell

    idf.py create-component test_cmp

After running the command, the local file structure of your component will look like this:

.. code-block:: text

    .
    └── test_cmp
        ├── CMakeLists.txt
        ├── include
        │   └── test_cmp.h
        └── test_cmp.c

You have now created a minimal component. These files are sufficient for local use. However, to publish your component on the ESP Component Registry, additional details are required. Navigate to the component directory and follow the steps below.

******************************
 Stage 2: Add packaging files
******************************

In this section, you will add files that help the ESP Component Registry better understand your component. After completing this section, your directory should look like this:

.. code-block:: text

    .
    └── test_cmp
        ├── CMakeLists.txt
        ├── idf_component.yml
        ├── include
        │   └── test_cmp.h
        ├── LICENSE
        ├── README.md
        └── test_cmp.c

Add ``idf_component.yml``
=========================

The ``idf_component.yml`` manifest file is required for the ESP Component Registry to recognize your component.

Start with a minimal ``idf_component.yml`` in the component root directory:

.. code-block:: yaml

    version: "0.0.1"
    description: "A simple example component"
    url: "https://github.com/<user>/<repo>"
    license: "MIT"

The only required field is ``version`` (see :ref:`versioning scheme <versioning-scheme>`). The other fields are strongly recommended for discoverability.

For more details, refer to the :doc:`manifest file reference <../../reference/manifest_file>`.

Add a license file
==================

Once your component is published, others can discover, download, and use it. Include a license so users know what they are allowed to do.

- Choose a license: see `Choose an open source license <https://choosealicense.com/>`_ (check the "How to apply this license" section).
- Add the full license text as ``LICENSE`` (or ``LICENSE.txt``) in the component root directory.
- Set ``license`` in ``idf_component.yml`` to the SPDX identifier for your license: see the `SPDX License List <https://spdx.org/licenses/>`_.

Add ``README.md``
=================

A README helps users understand what your component does and how to use it.

Keep it short, but include at least:

- What the component provides (and any supported chips/IDF versions)
- How to add it as a dependency
- A minimal usage example or API entry point

For general guidance, see `About READMEs <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes>`_.

.. _staging-registry:

*****************************************
 Stage 3: Upload to the staging registry
*****************************************

Use the staging registry to validate your packaging, permissions, and upload workflow before publishing to production.

1. Authenticate to staging

Follow :ref:`login-staging-registry` to log in and create a ``staging`` profile.

2. Upload the component

From the component directory, upload using the staging profile:

.. code-block:: shell

    compote component upload --profile "staging" --name test_cmp

3. Use the staging build (optional)

To add the staging registry component to an ESP-IDF project, point the dependency to the staging registry URL:

.. code-block:: yaml

    dependencies:
      <your_default_namespace>/test_cmp:
        version: "*"
        registry_url: https://components-staging.espressif.com

********************************
 Stage 4: Publish to production
********************************

Publishing to production makes the version available from the public registry.

Using GitHub Actions (recommended)
==================================

If your component source is on GitHub, the easiest way to publish is to automate uploads with GitHub Actions. This way, new versions are published automatically whenever you push a tag or merge to your main branch.

See :doc:`how_to_github_actions_upload` for setup instructions and example workflows.

Using the CLI
=============

You can also upload manually from the command line.

1. Authenticate to production

Follow :ref:`login-via-cli`.

After successfully logging in, upload with:

.. code-block:: shell

    compote component upload --name test_cmp

Once uploaded, your component will be available at:

``https://components.espressif.com/components/<your_default_namespace>/test_cmp``

To upload the component to another namespace, you can specify the namespace in the command:

.. code-block:: shell

    compote component upload --name test_cmp --namespace another_namespace

Currently, creating a custom namespace requires approval from Espressif. You may submit a request via the `Namespace Request Form <https://components.espressif.com/settings/permissions/>`_. Once we approve your request, you can upload components to the new namespace. You can check the approval status on the same page. We will also notify you via email once the request is approved.

***************************
 Next steps and variations
***************************

Once you can package and upload a basic component, you will often want to:

- Configure profiles, tokens, and registry URLs: :doc:`/reference/config_file`
- Control which files are included in uploads: see ``files`` in :doc:`/reference/manifest_file`
- Add examples and understand how downloaded examples behave: :ref:`manifest-examples` and ``override_path`` in :doc:`/reference/manifest_file`
