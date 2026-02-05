###################################
 How to Upload from GitHub Actions
###################################

If you host your component source on GitHub, you can automate uploads so that new versions are published whenever you push a tag or merge to your main branch.

There are two ways to authenticate GitHub Actions with the ESP Component Registry:

- **OIDC (recommended)**: GitHub proves the identity of your workflow to the registry directly. No secrets to store or rotate.
- **API token**: Store a registry API token as a GitHub secret and pass it to the action. Simpler to set up, but you are responsible for keeping the token secure and rotating it.

*********************************************
 Option 1: OIDC authentication (recommended)
*********************************************

With OIDC, GitHub Actions requests a short-lived token from the registry on every run. You never store long-lived credentials.

Setup
=====

1. Sign in to the `ESP Component Registry <https://components.espressif.com>`_.
2. Navigate to the **Permissions** page (click the dropdown with your username).
3. Select the namespace where your component will be uploaded. If the component does not exist yet, create it first using the ``+`` button in the **Components** table.
4. Click on the component name in the **Components** table.
5. Add a **trusted uploader** by clicking the ``+`` button in the **Trusted Uploaders** table.

   .. list-table::
       :header-rows: 1

       - - Field
         - Required
         - Description
       - - Repository
         - Yes
         - GitHub repository in the form ``<owner>/<repo>`` (for example, ``espressif/my_component``).
       - - Workflow
         - Yes
         - The workflow filename (for example, ``upload.yml``) or the workflow display name (for example, ``Upload component``). Must match the workflow that performs the upload.
       - - Branch
         - No
         - Restrict uploads to a specific branch (for example, ``main``). If omitted, any branch is allowed.
       - - Environment
         - No
         - Restrict uploads to a specific `GitHub environment <https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment>`_. If omitted, any environment is allowed.

6. In your workflow file, grant the job permission to request an OIDC token (``id-token: write``).
7. Use the ``upload-components-ci-action`` to upload.

Example workflow
================

.. code-block:: yaml

    name: Upload component
    on:
      push:
        branches: [ main ]

    jobs:
      upload_components:
        runs-on: ubuntu-latest
        permissions:
          id-token: write
        steps:
          - uses: actions/checkout@v4
          - uses: espressif/upload-components-ci-action@v2
            with:
              components: "my_component: ."
              namespace: "my_namespace"

*********************
 Option 2: API token
*********************

If you cannot use OIDC (for example, self-hosted runners without OIDC support), you can authenticate with an API token instead.

1. Log in to the registry and copy your API token (see :doc:`how_to_authenticate`).
2. Add the token as a `GitHub Actions secret <https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions>`_ (for example, ``IDF_COMPONENT_API_TOKEN``).
3. Pass it to the action:

.. code-block:: yaml

    name: Upload component
    on:
      push:
        branches: [ main ]

    jobs:
      upload_components:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: espressif/upload-components-ci-action@v2
            with:
              components: "my_component: ."
              namespace: "my_namespace"
              api_token: ${{ secrets.IDF_COMPONENT_API_TOKEN }}

*********
 Related
*********

- `upload-components-ci-action <https://github.com/espressif/upload-components-ci-action>`_ (full documentation and options)
- Publish tutorial: :doc:`/publish/tutorial_to_package_and_upload`
