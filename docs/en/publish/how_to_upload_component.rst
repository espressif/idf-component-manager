###########################
 How to Upload a Component
###########################

There are two ways to upload a component to the ESP Component Registry:

- **From GitHub Actions** (recommended for ongoing development): automate uploads on every push or tag. See :doc:`how_to_github_actions_upload`.
- **From the command line**: upload manually using the ``compote`` CLI. This page covers the CLI approach.

Before uploading, make sure you have authenticated. See :doc:`how_to_authenticate`.

*************************************
 Upload from the component directory
*************************************

From the component directory (where ``idf_component.yml`` is located), run:

.. code-block:: console

    $ compote component upload --name my_component

*******************
 Upload to staging
*******************

If you use a staging profile, upload with:

.. code-block:: console

    $ compote component upload --profile "staging" --name my_component

********************************
 Upload to a specific namespace
********************************

If you have permissions for multiple namespaces, you can set the namespace explicitly:

.. code-block:: console

    $ compote component upload --name my_component --namespace my_namespace

*****************
 Troubleshooting
*****************

- Authentication and profile setup: :doc:`how_to_authenticate`
- If you see manifest validation errors, check the manifest reference: :doc:`/reference/manifest_file`
