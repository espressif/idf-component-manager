##################################################
 ``idf_component_manager.yml`` Configuration File
##################################################

The IDF Component Manager configuration file, which is named ``idf_component_manager.yml``, a YAML file that contains a set of different profiles. Each profile is a set of configurations that are used to define the behavior of where to upload or download the components.

By default, the configuration file is located at the following path:

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

   -  -  Field
      -  Type
      -  Default
      -  Upload
      -  Download
      -  Require Internet?

   -  -  registry_url
      -  URI
      -  components.espressif.com
      -  ✅
      -  ✅
      -  ✅

   -  -  storage_url
      -  URI or a list of URIs
      -  None
      -  ❌
      -  ✅
      -  ✅

   -  -  local_storage_url
      -  URI or a list of URIs
      -  None
      -  ❌
      -  ✅
      -  ❌

While doing the version solving, the version solver will always start with the URLs defined in `local_storage_url`, then `storage_url`, and finally `registry_url`. If the versions found in the first URL could satisfy the requirements, the version solver will not try to find the versions in the next URLs. If the version solver could not find the versions in any of the URLs, it will return an error.

Besides the URLs, each profile supports the following fields:

.. list-table::

   -  -  Field
      -  Type
      -  Default
      -  Description
      -  Required?

   -  -  api_token
      -  string
      -  None
      -  The API token to authenticate with the `registry_url`.
      -  Required when uploading the components.

   -  -  default_namespace
      -  string
      -  espressif
      -  The default namespace to use when uploading the components.
      -  ❌

By default, the configuration file should behave as follows:

.. code:: yaml

   profiles:
     default:
       registry_url: "components.espressif.com"

For Chinese users, we recommend to use the following storage URL to experience faster download speed:

.. code:: yaml

   profiles:
     default:
       storage_url:
         - "https://components-file.espressif.cn"

Besides, if you have a local storage server, you can also add the local storage URL to the configuration file:

.. code:: yaml

   profiles:
     default:
       local_storage_url:
         - file:///Users/username/storage/  # Unix path
         # - file://C:/storage/ # Windows path
         - http://localhost:9004

*******
 Usage
*******

All CLI commands accept ``--profile`` parameter to specify the service profile to use. If the parameter is not provided, the CLI will use the default profile.

For testing purpose, it's recommended to upload the components to the staging server first. To upload components to our staging server, you may use the following configuration file:

.. code:: yaml

   profiles:
     staging:
       registry_url: "https://components-staging.espressif.com"
       api_token: "your_api_token"
       default_namespace: "my_namespace"

Instead of manually login, create an access token, and create the configuration file, you may also use the command ``compote registry login`` to login to the registry server interactively and save the configuration to the configuration file.

For example, ``compote registry login --profile "staging" --registry-url https://components-staging.espressif.com --default-namespace my_namespace`` will open a browser window to login to the registry server. Once you created the token and copy-paste it to the terminal, the CLI will login to the registry server and save the configuration same as the above example.

To upload a component to the staging server, you may use the following command:

.. tabs::

   .. group-tab::

      ``compote``

      .. code:: shell

         compote component upload --profile=staging --name test_cmp

   .. group-tab::

      ``idf.py`` (deprecated)

      .. code:: shell

         idf.py upload-component --profile=staging --name test_cmp

The component ``my_component`` will be uploaded to the staging server with the namespace ``my_namespace``.
