##############################
 Packaging ESP-IDF Components
##############################

This tutorial will walk you through the process of packaging a simple ESP-IDF component. You will learn how to create the required files and upload your component to the `ESP Component Registry <https://components.espressif.com>`_.

***************
 Prerequisites
***************

This tutorial assumes you already have ESP-IDF installed. If not, please follow the instructions in the `ESP-IDF Get Started Guide <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/index.html>`_.

*****************************
 Creating a Simple Component
*****************************

You can create a new ESP-IDF component using the following command:

.. code:: shell

   idf.py create-component test_cmp

After running the command, the local file structure of your component will look like this:

.. code:: text

   .
   └── test_cmp
       ├── CMakeLists.txt
       ├── include
       │   └── test_cmp.h
       └── test_cmp.c

You have now created a minimal component. These files are sufficient for local use. However, to publish your component on the ESP Component Registry, additional details are required. Navigate to the component directory and follow the steps below.

***********************
 Extra Packaging Files
***********************

In this section, you will add files that help the ESP Component Registry better understand your component. After completing this section, your directory should look like this:

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

The ``idf_component.yml`` manifest file is required for the ESP Component Registry to recognize your component.

Here’s a minimal example of an ``idf_component.yml`` file:

.. code:: yaml

   version: "0.0.1"

The only required field is `version`, which must follow the :ref:`versioning scheme <versioning-scheme>`.

We also recommend including `url` and `description`. Otherwise, a warning will be displayed.

.. code:: yaml

   version: "0.0.1"
   description: "This is a test component"
   url: "https://mycomponent.com"  # The homepage of the component. It can be a GitHub repository page.

For more details, refer to the :doc:`manifest file reference <../reference/manifest_file>`.

Create a License File
=====================

Once your component is published, others can discover, download, and use it. Including a license is essential for proper use.

If you’re unsure which license to choose, visit https://choosealicense.com. Once selected, add the full license text in a ``LICENSE`` or ``LICENSE.txt`` file in your component’s root directory. Be sure to check the "How to apply this license" section to see if there are additional actions required to apply the license.

After selecting a license, you can add the ``license`` field in your ``idf_component.yml`` file. The value should be the SPDX license identifier of the chosen license. You can check the identifier list at https://spdx.org/licenses/. For example, if you choose the MIT license, the ``idf_component.yml`` should look like:

.. code:: yaml

   version: "0.0.1"
   license: "MIT"

Create README.md
================

A README helps users understand your component. It usually includes a brief intro, installation steps, and a basic usage example.

.. code:: text

   # Test Component

   This is a simple example component.

   ## Installation

   - Step 1
   - Step 2

   ## Getting Started

   - Step 1
   - Step 2

.. _staging-registry:

****************************
 Test with Staging Registry
****************************

For testing purposes, we recommend to upload the components to the staging server first.

First, follow the steps in the :ref:`login-staging-registry` section to log in.

Then, upload your component to the staging registry by running the following command:

.. code:: shell

   compote component upload --profile "staging" --name test_cmp

To use it in your project, add the registry URL in your manifest:

.. code:: yaml

   dependencies:
     <your_default_namespace>/test_cmp:
       version: "*"
       registry_url: https://components-staging.espressif.com

************************
 Publish Your Component
************************

To publish components to the ESP Component Registry (production registry), follow the steps in :ref:`login-via-cli`.

After successfully logging in, upload with:

.. code:: shell

   compote component upload --name test_cmp

Once uploaded, your component will be available at:

``https://components.espressif.com/components/<your_default_namespace>/test_cmp``

To upload the component to another namespace, you can specify the namespace in the command:

.. code:: shell

   compote component upload --name test_cmp --namespace another_namespace

Currently, creating a custom namespace requires approval from Espressif. You may submit a request via the `Namespace Request Form <https://components.espressif.com/settings/permissions/>`_. Once we approve your request, you can upload components to the new namespace. You can check the approval status on the same page. We will also notify you via email once the request is approved.

*****************
 Advanced Usages
*****************

What we mentioned above is the basic usage for uploading a component. Here are more use cases and tips.

Authentication via Environment Variables
========================================

For CI/CD, use these environment variables:

-  ``IDF_COMPONENT_REGISTRY_URL``: Registry URL to log in.
-  ``IDF_COMPONENT_API_TOKEN``: The API token to authenticate with the registry URL.

Filter Component Files
======================

As a component developer, you may want to specify which files from the component directory will be uploaded to the ESP Component Registry. This can be achieved by using `manifest filters`_ and a `.gitignore file`_.

Manifest Filters
----------------

Example:

Your ``idf_component.yml`` manifest may have ``files`` section with ``include`` and ``exclude`` filters. For example:

.. code:: yaml

   files:
      exclude:
         - "*.py"          # Exclude all Python files
         - "**/*.list"     # Exclude `.list` files in all directories
         - "big_dir/**/*"  # Exclude `big_dir` directory and its content
      include:
         - "**/.DS_Store"  # Include files excluded by default

Files and directories that are excluded by default are listed `here <https://github.com/espressif/idf-component-manager/blob/main/idf_component_tools/file_tools.py#L16>`_.

.gitignore File
---------------

If you have a ``.gitignore`` file in your component directory, you can use it to filter files. All you need to do, is to specify the ``use_gitignore`` option in the ``idf_component.yml`` manifest file.

.. code:: yaml

   files:
     use_gitignore: true

Patterns specified in the ``.gitignore`` file will be automatically excluded before packaging or uploading the component.

.. code:: yaml

   test_dir/   # Exclude files in all `test_dir` directories (including the directories themselves)

More information on how ``.gitignore`` works can be found in the `official documentation <https://git-scm.com/docs/gitignore>`_.

You can also use both manifest filters and a ``.gitignore`` file. In this case, the patterns from the ``.gitignore`` file will be applied first. Example:

.. code:: yaml

   files:
      use_gitignore: true
      exclude:
         - ".env"          # Exclude `.env` file
      include:
         - "test_dir/**/*" # Include all files in `test_dir` directory
                           # which were excluded by `.gitignore`

When using ``.gitignore``, files specified `here <https://github.com/espressif/idf-component-manager/blob/main/idf_component_tools/file_tools.py#L16>`_ will not be excluded by default.

.. warning::

   When including or excluding an entire directory and its contents, avoid using the ``some_path/**`` pattern. Instead, use ``some_path/**/*``.

   The IDF Component Manager relies on Python's `pathlib.Path.glob <https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob>`_ function for file inclusion and exclusion. In Python versions prior to 3.13, the ``**`` pattern matches directories but does not match files. This limitation was corrected in Python 3.13. For additional details, refer to the `glob` `pattern language documentation <https://docs.python.org/3/library/pathlib.html#pattern-language>`_.

Add Dependencies
================

When your component depends on another component, you need to specify this dependency relationship in your component's manifest file as well. Our :doc:`Version Solver <../guides/version_solver>` would collect all dependencies and calculate the final versioning solution. Example:

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

You may want to provide example projects to help users get started with your component. By default, the ``examples`` directory is located within the component directory, and all example projects are discovered recursively. To customize the path to the examples directory, you can specify it in the :ref:`manifest file <manifest-examples>`.

When an archive containing the component is uploaded to the registry, all examples are repackaged into individual archives. Therefore, each example must be self-contained—meaning it should not depend on any files outside its own directory within the ``examples`` folder. For convenience, the entire ``examples`` directory is also included in the component archive.

Adding Dependency on the Component for Examples
-----------------------------------------------

When a component repository is cloned from a Git repository, it is essential for the example in the ``examples`` directory to use the component located within the same repository tree. However, when a single example is downloaded via the CLI from the registry and no local dependency is present, the component must be fetched from the registry.

This behavior can be controlled by setting the ``override_path`` for the dependency in the manifest file. When ``override_path`` is defined for a registry dependency, it takes precedence. However, when an example is downloaded from the registry, the ``override_path`` field is automatically removed. As a result, during the build process, the system will not attempt to locate the component locally.

For example, for a component named ``cmp`` published in the registry as ``watman/cmp``, the ``idf_component.yml`` manifest in the ``examples/hello_world/main`` may look like:

.. code:: yaml

   version: "1.2.7"
   description: My hello_world example
   dependencies:
     watman/cmp:
       version: '~1.0.0'
       override_path: '../../../' # three levels up, pointing to the directory with the component itself

.. note::

   Do not add your component's directory to ``EXTRA_COMPONENT_DIRS`` in the example's ``CMakeLists.txt``, as this will break examples downloaded from the registry.

Upload Component via GitHub Action
==================================

We provide a `GitHub action <https://github.com/espressif/upload-components-ci-action>`_ to help you upload your components to the registry as part of your GitHub workflow.
