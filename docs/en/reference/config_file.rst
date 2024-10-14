##################################################
 ``idf_component_manager.yml`` Configuration File
##################################################

The IDF Component Manager configuration file, named ``idf_component_manager.yml``, is a YAML file that contains a set of different profiles. Each profile is a collection of configurations used to define the behavior of where to upload or download the components.

By default, the configuration file is located at the following paths:

.. tabs::

   .. group-tab::

      Windows

      C:/Users/YOUR_USERNAME/.espressif

   .. group-tab::

      Unix-like

      $HOME/.espressif

You may also set the environment variable ``IDF_TOOLS_PATH`` to specify a different path for the configuration file.

********************
 Configuration File
********************

Each profile supports the following fields related to the URLs:

.. list-table::
   :stub-columns: 1

   -  -  Field
      -  ``registry_url``
      -  ``storage_url``
      -  ``local_storage_url``

   -  -  Type
      -  URI
      -  URI or a list of URIs
      -  URI or a list of URIs

   -  -  Default
      -  components.espressif.com
      -  None
      -  None

   -  -  |  Override by
         |  Environment Variable?
      -  ``IDF_COMPONENT_REGISTRY_URL``
      -  ``IDF_COMPONENT_STORAGE_URL``
      -  ❌

   -  -  Support Upload
      -  ✅
      -  ❌
      -  ❌

   -  -  Support Download
      -  ✅
      -  ✅
      -  ✅

   -  -  Require Internet?
      -  ✅
      -  ✅
      -  ❌

Besides the URLs, each profile supports the following fields:

.. list-table::

   -  -  Field
      -  Type
      -  Default
      -  Description
      -  Required?

   -  -  ``api_token``
      -  string
      -  None
      -  The API token to authenticate with the ``registry_url``.
      -  Required when uploading components.

   -  -  ``default_namespace``
      -  string
      -  espressif
      -  The default namespace to use when uploading components.
      -  ❌

By default, the configuration file should behave as follows:

.. code:: yaml

   profiles:
     default:
       registry_url: "components.espressif.com"

For Chinese users, we recommend using the following storage URL to experience faster download speeds:

.. code:: yaml

   profiles:
     default:
       storage_url:
         - "https://components-file.espressif.cn"

Additionally, if you have a local storage server, you can also add the local storage URL to the configuration file:

.. code:: yaml

   profiles:
     default:
       local_storage_url:
         - file:///Users/username/storage/  # Unix path
         # - file://C:/storage/ # Windows path
         - http://localhost:9004

***************************************
 URLs Precedence While Version Solving
***************************************

While performing version solving, the version solver will always start with the URLs defined in ``local_storage_url``, then ``storage_url``, and finally ``registry_url``. If the versions found in the first URL satisfy the requirements, the version solver will not attempt to find the versions in the next URLs. If the version solver cannot find the versions in any of the URLs, it will return an error.

For example, if your default profile is as follows:

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

While solving the versions, the version solver will look for the versions in this order:

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

To log in to the registry server, you may use the following command:

.. code:: shell

   compote registry login --profile "default" --registry-url "https://components.espressif.com" --default-namespace <your_github_username>

This command will open a browser window where you can log in with your GitHub account. After logging in, you will be redirected to a page that generates a token. Copy this token and paste it into the terminal.

Passing the ``--default-namespace`` option while logging in is recommended. Otherwise, you will need to specify the namespace every time you upload a component. By default, you are granted permission to upload components to the namespace that matches your GitHub username.

The token will be saved in the configuration file, so you don't have to create it manually.

.. _login-staging-registry:

***************************
 Login to Staging Registry
***************************

To log in to the staging registry, use the following command:

.. code:: shell

   compote registry login --profile "staging" --registry-url "https://components-staging.espressif.com" --default-namespace <your-github-username>

After logging in, the configurations will be saved in the ``staging`` profile.
