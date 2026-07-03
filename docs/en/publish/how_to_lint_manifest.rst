############################
 How to Lint Manifest Files
############################

The ``compote manifest lint`` command validates ``idf_component.yml`` manifest files against the manifest schema without modifying them. Use it locally or in CI to catch manifest mistakes early.

********************
 Validate manifests
********************

Validate every manifest under the current project directory:

.. code-block:: shell

    compote manifest lint

Validate specific files or directories by passing them as arguments:

.. code-block:: shell

    # A single manifest file
    compote manifest lint components/my_component/idf_component.yml

    # Every manifest under a directory (searched recursively)
    compote manifest lint components/

Valid manifests produce no output. If a manifest is invalid, the command prints the validation errors and exits with status code ``1``, which fails CI jobs.

*******************
 What gets skipped
*******************

When searching a directory, downloaded dependencies (``managed_components``), packaging artifacts (``dist``), and hidden directories are skipped automatically. To limit what is checked, pass the specific files or directories you want to validate.

*********
 Related
*********

- Manifest reference: :doc:`/reference/manifest_file`
- Full command reference: :doc:`/reference/compote_cli`
