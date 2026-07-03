############################
 How to Lint Manifest Files
############################

The ``compote manifest lint`` command validates ``idf_component.yml`` manifest files against the manifest schema without modifying them. Use it locally, in CI, or as a pre-commit hook to catch manifest mistakes early.

Unlike other ``compote manifest`` commands, ``lint`` intentionally accepts only positional paths. It does not support options such as ``--path`` or ``--component``.

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

Valid manifests produce no output. If a manifest is invalid, the command prints the validation errors and exits with status code ``1``, which fails CI jobs and pre-commit runs.

*******************
 What gets skipped
*******************

When searching a directory, downloaded dependencies (``managed_components``), packaging artifacts (``dist``), and hidden directories are skipped automatically. To limit what is checked, pass the specific files or directories you want to validate. These exclusions only apply while discovering manifests under a parent directory; if you explicitly pass ``managed_components/`` or ``dist/``, manifests under those directories are checked. Under pre-commit, use pre-commit's own ``exclude`` option.

*********************
 Use with pre-commit
*********************

The component manager ships a `pre-commit <https://pre-commit.com/>`_ hook. Add it to your ``.pre-commit-config.yaml``:

.. code-block:: yaml

    repos:
      - repo: https://github.com/espressif/idf-component-manager
        rev: <release tag>  # v3.1.0 or newer
        hooks:
          - id: manifest-lint

pre-commit finds the changed ``idf_component.yml`` files and passes them to the linter. To skip files, use pre-commit's own ``exclude`` option:

.. code-block:: yaml

    - id: manifest-lint
      exclude: '^tests/fixtures/'

*********
 Related
*********

- Manifest reference: :doc:`/reference/manifest_file`
- Full command reference: :doc:`/reference/compote_cli`
