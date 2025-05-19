##################################################
 ``idf_component_manager.yml`` Configuration File
##################################################

The IDF Component Manager configuration file, named ``idf_component_manager.yml``, is a YAML file that defines a set of profiles. Each profile is a collection of configurations that determines where components are uploaded from or downloaded to.

By default, the configuration file is located in the following paths:

.. tabs::

   .. group-tab::

      Windows

      C:/Users/YOUR_USERNAME/.espressif

   .. group-tab::

      Unix-like

      $HOME/.espressif

You can also override the path by setting the ``IDF_TOOLS_PATH`` environment variable.

********************
 Configuration File
********************

.. versionadded:: 2.1

   Support for local storage mirrors and the ``local_storage_url`` field.

Each profile supports the following URL-related fields:

.. list-table::
   :stub-columns: 1

   -  -  Field
      -  ``registry_url``
      -  ``storage_url``
      -  ``local_storage_url``

   -  -  Type
      -  URI
      -  URI or list of URIs
      -  URI or list of URIs

   -  -  Default
      -  components.espressif.com
      -  None
      -  None

   -  -  |  Override by
         |  Environment Variable?
      -  ``IDF_COMPONENT_REGISTRY_URL``
      -  ``IDF_COMPONENT_STORAGE_URL``
      -  ❌

   -  -  Supports Upload?
      -  ✅
      -  ❌
      -  ❌

   -  -  Supports Download?
      -  ✅
      -  ✅
      -  ✅

   -  -  Requires Internet?
      -  ✅
      -  ✅
      -  ❌

In addition to URLs, each profile supports the following fields:

.. list-table::

   -  -  Field
      -  Type
      -  Default
      -  Description
      -  Required?

   -  -  ``api_token``
      -  string
      -  None
      -  The API token used to authenticate with the ``registry_url``.
      -  Required for uploading components.

   -  -  ``default_namespace``
      -  string
      -  espressif
      -  The default namespace for uploading components.
      -  ❌

Here is a minimal default configuration:

.. code:: yaml

   profiles:
     default:
       registry_url: "components.espressif.com"

For users in China, we recommend using the following `storage_url` to improve download speeds:

.. code:: yaml

   profiles:
     default:
       storage_url:
         - "https://components-file.espressif.cn"

If you have a :doc:`local mirror set <../guides/partial_mirror>`, you can also define the `local_storage_url` in the configuration file:

.. code:: yaml

   profiles:
     default:
       local_storage_url:
         - file:///Users/username/storage/  # Unix path
         # - file://C:/storage/             # Windows path
         - http://localhost:9004

.. _url_precedence:

***************************************
 URL Precedence During Version Solving
***************************************

When solving versions, the resolver checks sources in the following order:

#. ``local_storage_url``
#. ``storage_url``
#. ``registry_url``

If a valid version is found in one of the earlier sources, the resolver does not check the remaining ones. If no source provides a valid version, an error is returned.

Given the following configuration:

.. code:: yaml

   profiles:
     default:
       registry_url: a.com
       storage_url:
         - b.com
         - c.com
       local_storage_url:
         - http://localhost:9004
         - http://localhost:9005

The version solver will check sources in this order:

-  ``registry_url`` defined in the manifest ``dependencies`` field
-  http://localhost:9004
-  http://localhost:9005
-  b.com
-  c.com
-  a.com

.. _login-via-cli:

***************
 Login via CLI
***************

To log in to the registry server, use the following command:

.. code:: shell

   compote registry login --profile "default" --registry-url "https://components.espressif.com" --default-namespace <your_github_username>

This command will open a browser window where you can authenticate with your GitHub account. After logging in, you’ll be redirected to a page displaying your token. Copy and paste it into the terminal.

Passing the ``--default-namespace`` option is recommended to avoid specifying the namespace on every upload. By default, your GitHub username will be used as the namespace and you will be given permission to upload components to that namespace.

The token will be stored in the configuration file automatically, so you don't have to create it manually..

.. _login-staging-registry:

***************************
 Login to Staging Registry
***************************

To log in to the staging registry, use the command:

.. code:: shell

   compote registry login --profile "staging" --registry-url "https://components-staging.espressif.com" --default-namespace <your-github-username>

After logging in, the configuration will be saved under the ``staging`` profile.
