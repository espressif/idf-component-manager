##############################
 Packaging ESP-IDF Components
##############################

This tutorial will guide you through packaging a simple ESP-IDF component. You will learn how to create all the necessary files and upload your component to the `ESP Component Registry <https://components.espressif.com>`_.

***************
 Prerequisites
***************

In this tutorial, we assume that you have already installed ESP-IDF. If it is not installed, please refer to our `ESP-IDF Get Started Guide <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/index.html>`_.

****************************
 A Simple ESP-IDF Component
****************************

An ESP-IDF component can be created by running the following command:

.. code:: shell

   idf.py create-component test_cmp

After running the command, your component's local file tree will look like this:

.. code:: text

   .
   └── test_cmp
       ├── CMakeLists.txt
       ├── include
       │   └── test_cmp.h
       └── test_cmp.c

You have created your first bare minimum component. These files are sufficient for local use; however, to publish your component on the ESP Component Registry, it is necessary to provide more details. Please navigate to the component directory and continue with the next steps.

***********************
 Extra Packaging Files
***********************

In this section, you will add files that help the ESP Component Registry understand your component better. When this section is finished, the file structure will look like:

.. code:: text

   .
   └── test_cmp
       ├── CMakeLists.txt
       ├── idf_component.yml
       ├── include
       │   └── test_cmp.h
       ├── LICENSE
       ├── README.md
       └── test_cmp.c

Create ``idf_component.yml``
============================

A manifest file, ``idf_component.yml``, is required to let the ESP Component Registry recognize your ESP-IDF component.

Here's the minimal ``idf_component.yml``:

.. code:: yaml

   version: "0.0.1"

The ESP Component Registry only requires the ``version`` of the component in the `idf_component.yml`. The ``version`` must follow :ref:`versioning scheme <versioning-scheme>`.

However, we recommend adding ``url`` and ``description``. Otherwise, a warning will be printed.

.. code:: yaml

   version: "0.0.1"
   description: "This is a test component"
   url: "https://mycomponent.com"  # The homepage of the component. It can be a GitHub repository page.

For information about additional fields in the manifest, please check the :doc:`manifest file reference <../reference/manifest_file>`.

Create a License File
=====================

Once you've uploaded your component, other users can discover, download, and use it. Including a license with your component is crucial to ensure proper usage.

If you need help choosing a license for your component, you can check the https://choosealicense.com website. Once you've selected your license, be sure to include the full text of the license in the ``LICENSE`` or ``LICENSE.txt`` file in your component's root directory. Be sure to check the "How to apply this license" section to see if there are additional actions required to apply the license.

After selecting a license, you can add the ``license`` field in your ``idf_component.yml`` file. The value should be the SPDX license identifier of the chosen license. You can check the identifier list at https://spdx.org/licenses/. For example, if you choose the MIT license, the ``idf_component.yml`` should look like:

.. code:: yaml

   version: "0.0.1"
   license: "MIT"

Create README.md
================

A README file will help users understand your component better. It typically includes a brief introduction, installation steps, and a simple getting-started tutorial.

.. code:: text

   # Test Component

   This is a simple example component.

   ## Installation

   - step 1
   - step 2

   ## Getting Started

   - step 1
   - step 2

.. _staging-registry:

**************************
 Test on Staging Registry
**************************

For testing purposes, it's recommended to upload the components to the staging server first. To upload components to our staging server, you may follow the steps in the :ref:`login-staging-registry` section.

After logging in, you can upload your component to the staging registry by running the following command:

.. code:: shell

   compote upload --profile "staging" --component test_cmp

To use the uploaded component in your project, you need to specify the registry URL in the ``idf_component.yml`` file:

.. code:: yaml

   dependencies:
     <your_default_namespace>/test_cmp:
       version: "*"
       registry_url: https://components-staging.espressif.com

***********************
 Publish the Component
***********************

To upload components to the ESP Component Registry, you may follow the steps in the :ref:`login-via-cli` section.

After successfully logging in, you can upload your component to the ESP Component Registry (production registry) by running the following command:

.. code:: shell

   compote component upload --name test_cmp

Once uploaded, your component should be viewable at `https://components.espressif.com/components/<your_default_namespace>/test_cmp`.

To upload the component to another namespace, you can specify the namespace in the command:

.. code:: shell

   compote component upload --name test_cmp --namespace another_namespace

Currently, creating a custom namespace requires approval from Espressif. You may submit a request using the `Namespace Request Form <https://components.espressif.com/settings/permissions/>`_. Once we approve your request, you can upload components to the new namespace. You can check the approval status on the same page. We will also notify you via email once the request is approved.

*****************
 Advanced Usages
*****************

What we mentioned above is the basic usage for uploading a component. Here are more use cases and tips.

Authentication with Environment Variables
=========================================

In CI/CD pipelines, using environment variables to log in is more convenient. You can set the following environment variables:

-  ``IDF_COMPONENT_REGISTRY_URL``: The registry URL to log in.
-  ``IDF_COMPONENT_API_TOKEN``: The API token to authenticate with the registry URL.

Filter Component Files
======================

As a component developer, you may want to specify which files from the component directory will be uploaded to the ESP Component Registry. There are two ways to achieve this: either by `using a .gitignore file`_ or by `using manifest filters`_.

.. warning::

   You are not allowed to use both methods simultaneously.

Using a .gitignore File
-----------------------

First, you need to specify the ``use_gitignore`` option in the ``idf_component.yml`` manifest file.

.. code:: yaml

   files:
      use_gitignore: true

Then, patterns specified in the ``.gitignore`` file will be automatically excluded before packaging or uploading the component.

.. code:: yaml

   test_dir/   # Exclude files in all `test_dir` directories (including the directories themselves)

More information on how ``.gitignore`` works can be found in the `official documentation <https://git-scm.com/docs/gitignore/en>`_.

Using Manifest Filters
----------------------

In this case, your ``idf_component.yml`` manifest may have ``include`` and ``exclude`` filters. For example:

.. code:: yaml

   files:
      exclude:
         - "*.py"          # Exclude all Python files
         - "**/*.list"     # Exclude `.list` files in all directories
         - "big_dir/**/*"  # Exclude `big_dir` directory and its content
      include:
         - "**/.DS_Store"  # Include files excluded by default

Files and directories that are excluded by default can be found `here <https://github.com/espressif/idf-component-manager/blob/main/idf_component_tools/file_tools.py#L16>`_.

.. warning::

   When including or excluding an entire directory and its contents, avoid using the ``some_path/**`` pattern. Instead, use ``some_path/**/*``.

   The IDF Component Manager relies on Python's `pathlib.Path.glob <https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob>`_ function for file inclusion and exclusion. In Python versions prior to 3.13, the ``**`` pattern matches directories but does not match files. This limitation was corrected in Python 3.13. For additional details, refer to the `glob` `pattern language documentation <https://docs.python.org/3/library/pathlib.html#pattern-language>`_.

Add Dependencies
================

When your component depends on another component, you need to specify this dependency relationship in your component's manifest file as well. Our :doc:`Version Solver <../guides/version_solver>` would collect all dependencies and calculate the final versioning solution. For example:

.. code:: yaml

   dependencies:
     idf:
       version: ">5.0.0"
     example/cmp:
       version: "^3.0.0"

Please refer to our :ref:`version range specification <version-range-specifications>` for detailed information on the ``version`` field.

.. note::

   Unlike the other dependencies, ``idf`` is a keyword that points to ESP-IDF itself, not a component.

.. _add-example-projects:

Add Example Projects
====================

You may want to provide example projects to help users get started with your component. By default, the examples directory is located at ``examples`` within the component directory. All example projects are discovered recursively. To customize the path to the examples directory, you can set it in the :ref:`manifest file <manifest-examples>`.

When an archive containing the component is uploaded to the registry, all examples are repacked into individual archives. Therefore, every example must be self-sufficient, meaning it should not depend on any files in the examples directory outside its own directory. For convenience, the ``examples`` directory is also included in the component archive.

Adding Dependency on the Component for Examples
-----------------------------------------------

When a component repository is cloned from a Git repository, it is essential for the example in the ``examples`` directory to use the component that resides right here in the tree. However, when a single example is downloaded using CLI from the registry, and there is no dependency around, it must be downloaded from the registry.

This behavior can be achieved by setting the ``override_path`` for the dependency in the manifest file. When ``override_path`` is defined for a dependency from the registry, it will be used with higher priority. When you download an example from the registry, it doesn't contain ``override_path`` since all ``override_path`` fields are automatically removed. During the build process, it won't attempt to look for the component nearby.

For example, for a component named ``cmp`` published in the registry as ``watman/cmp``, the ``idf_component.yml`` manifest in the ``examples/hello_world/main`` may look like:

.. code:: yaml

   version: "1.2.7"
   description: My hello_world example
   dependencies:
     watman/cmp:
       version: '~1.0.0'
       override_path: '../../../' # three levels up, pointing to the directory with the component itself

.. note::

   You shouldn't add your component's directory to ``EXTRA_COMPONENT_DIRS`` in the example's ``CMakeLists.txt``, as it will break the examples downloaded with the repository.

Upload Component with GitHub Action
===================================

We provide a `GitHub action <https://github.com/espressif/upload-components-ci-action>`_ to help you upload your components to the registry as part of your GitHub workflow.
