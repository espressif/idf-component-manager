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

You have created your first bare minimum component. These files are sufficient for local use, however, to publish your component on the ESP Component Registry it is necessary to provide more details. Please navigate to the component directory and continue with the next steps.

***********************
 Extra Packaging Files
***********************

In this section, you would add files that are used to help the ESP Component Registry know your component better. When this section is finished, the file structure would look like:

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

A manifest file ``idf_component.yml`` is required to let the ESP Component Registry recognize your ESP-IDF component.

Here's the minimal ``idf_component.yml``:

.. code:: yaml

   version: "0.0.1"

The ESP Component Registry only requires the ``version`` of the component in the `idf_component.yml`. ``version`` must follow :ref:`versioning scheme <reference/versioning:Versioning Scheme>`.

However, we recommend adding ``url`` and ``description``. Otherwise, a warning will be printed.

.. code:: yaml

   version: "0.0.1"
   description: "This is a test component"
   url: "https://mycomponent.com"  # The homepage of the component. It can be a GitHub repository page.

For information about additional fields in the manifest please check the :doc:`manifest file reference <../reference/manifest_file>`.

Create License File
===================

Once you've uploaded your component, other users can discover, download, and use it. Including a license with your component is crucial to ensure proper usage.

If you need help choosing a license for your component, you can check the https://choosealicense.com website. Once you've selected your license, be sure to include the full text of the license in the ``LICENSE`` or ``LICENSE.txt`` file in your component's root directory. Better to check the "How to apply this license" section to see if there's additional action items to apply the license.

After selecting a license, you can add the ``license`` field in your ``idf_component.yml`` file. The value should be the SPDX license identifier of the chosen license. You may check the identifier list at https://spdx.org/licenses/. For example, if you choose MIT license, the ``idf_component.yml`` should look like:

.. code:: yaml

   version: "0.0.1"
   license: "MIT"

Create README.md
================

A README file would help users know better about your component. Usually it includes a brief introduction, the installation steps, and a simple getting-started tutorial.

.. code:: text

   # Test Component

   This is a simple example component.

   ## Installation

   - step 1
   - step 2

   ## Getting Started

   - step 1
   - step 2

***********************
 Publish the Component
***********************

Authentication
==============

To publish your component to the ESP Component Registry, you need to provide the authentication token. The simplest way is to set it via the environment variable ``IDF_COMPONENT_API_TOKEN``.

All components would be published under their namespace. If ``--namespace`` is not passed, the default namespace is ``espressif``.

.. note::

   For now, creating custom namespace is not supported. Please contact us if you have such needs.

.. versionadded:: 1.2

   New CLI, ``compote``. Now you may skip install ``ESP-IDF`` for packaging your component. This would be helpful when publishing your component in CI/CD pipelines.

.. tabs::

   .. group-tab::

      ``compote``

      .. code:: shell

         compote component upload --namespace [YOUR_NAMESPACE] --name test_cmp

   .. group-tab::

      ``idf.py`` (deprecated)

      .. code:: shell

         idf.py upload-component --namespace [YOUR_NAMESPACE] --name test_cmp

Once uploaded, your component should be viewable on `<https://components.espressif.com/components/YOUR_NAMESPACE/test_cmp>`

*****************
 Advanced Usages
*****************

What we mentioned above is the basic usage to upload a component. Here are more use cases and tips.

Authentication with a Config File
=================================

You can control which registry you upload to, and provide the authentication token via a config file. For detailed information, please refer to our :doc:`config file reference <../reference/config_file>`.

Filter Component Files
======================

As a component developer, you may want to choose what files from the component directory will be uploaded to the ESP Component Registry. In this case, your ``idf_component.yml`` manifest may have ``include`` and ``exclude`` filters. For example:

.. code:: yaml

   files:
     exclude:
       - "*.py"         # Exclude all Python files
       - "**/*.list"    # Exclude `.list` files in all directories
       - "big_dir/**/*" # Exclude `big_dir` directory and its content
     include:
       - "**/.DS_Store" # Include files excluded by default

Files and directories that are excluded by default can be found `here <https://github.com/espressif/idf-component-manager/blob/main/idf_component_tools/file_tools.py#L16>`_

.. note::

   The ``file`` field is only taken into account during the preparation of the archive before uploading to the registry.

Add Dependencies
================

When your component depends on another component, you need to add this dependency relationship in your component's manifest file as well. Our :ref:`version solver <reference/versioning:Version Solving>` would collect all dependencies and calculate the final versioning solution. For example:

.. code:: yaml

   dependencies:
     idf:
       version: ">5.0.0"
     example/cmp:
       version: "^3.0.0"

Please refer to our :ref:`version range specification <reference/versioning:Range Specifications>` for detailed information on the ``version`` field.

.. note::

   Unlike the other dependencies, ``idf`` is a keyword that points to ESP-IDF itself, not a component.

Add example projects
====================

You may want to provide example projects to help users get started with your component. You place them in the ``examples`` directory inside your component. Examples are discovered recursively in subdirectories at this path. A directory with ``CMakeLists.txt`` that registers a project is considered as an example.

When an archive with the component is uploaded to the registry all examples are repacked to individual archives. So every example must be self-sufficient, i.e. doesn't depend on any files in the examples directory except its own directory. For convenience the ``examples`` directory is available in the component archive too.

Adding dependency on the component for examples
-----------------------------------------------

When a component repo is cloned from a git repository, then it's essential that for the example in the ``examples`` directory to use the component that lays right here in the tree. However, when a single example is downloaded using CLI from the registry, and there is no dependency laying around it must be downloaded from the registry.

This behavior can be achieved by setting ``override_path`` for dependency in the manifest file. When ``override_path`` is defined for a dependency from the registry it will be used with higher priority. When you download an example from the registry, it doesn't contain ``override_path``, because all ``override_path`` fields are automatically removed. During the build process, it won't try to look for the component nearby.

I.E. for a component named ``cmp`` published in the registry as ``watman/cmp`` the ``idf_component.yml`` manifest in the ``examples/hello_world/main`` may look like:

.. code:: yaml

   version: "1.2.7"
   description: My hello_world example
   dependencies:
   watman/cmp:
     version: '~1.0.0'
     override_path: '../../../' # three levels up, pointing the directory with the component itself

.. note::

   You shouldn't add your component's directory to ``EXTRA_COMPONENT_DIRS`` in example's ``CMakeLists.txt``, because it will break the examples downloaded with the repository.

Upload Component with GitHub Action
===================================

We provide a `GitHub action <https://github.com/espressif/upload-components-ci-action>`_ to help you upload your components to the registry as a part of your GitHub workflow.
