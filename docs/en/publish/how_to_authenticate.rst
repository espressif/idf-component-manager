####################################
 How to Authenticate for Publishing
####################################

The ESP Component Registry uses your GitHub account to verify that you have permission to upload components to a namespace. You must authenticate before uploading.

.. _login-via-cli:

*********************************
 Login via browser (recommended)
*********************************

Use the CLI to start a browser-based login flow. This opens a browser window where you authenticate with your GitHub account. After logging in, the credentials are saved into your configuration file automatically.

.. code-block:: console

    $ compote registry login --profile "default" --registry-url "https://components.espressif.com" --default-namespace <your_github_username>

Passing ``--default-namespace`` is recommended so you don't have to specify the namespace on every upload. By default, your GitHub username is used as the namespace.

.. _login-staging-registry:

*******************************
 Login to the staging registry
*******************************

To log in to the staging registry, create a separate ``staging`` profile:

.. code-block:: console

    $ compote registry login --profile "staging" --registry-url "https://components-staging.espressif.com" --default-namespace <your_github_username>

After logging in, the configuration will be saved under the ``staging`` profile.

*********
 Related
*********

- Configuration file schema and login reference: :doc:`/reference/config_file`
