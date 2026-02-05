############################################
 How to Configure the IDF Component Manager
############################################

This page shows common configuration tasks: choosing a registry, improving download speeds, and using a local mirror.

The Component Manager reads settings from the ``idf_component_manager.yml`` configuration file (profiles), and you can override selected settings with environment variables.

For the complete configuration file schema and field semantics, see :doc:`../../reference/config_file`.

******************
 Common scenarios
******************

Use the default registry
========================

If you do not need any customization, you can rely on the defaults (the public ESP Component Registry). A minimal configuration looks like:

.. code-block:: yaml

    profiles:
      default:
        registry_url: "components.espressif.com"

Improve download speeds in China (``storage_url``)
==================================================

If you are located in China, you can configure an alternative storage endpoint to speed up component downloads:

.. code-block:: yaml

    profiles:
      default:
        storage_url:
          - "https://components-file.espressif.cn"

Use a local mirror or offline storage (``local_storage_url``)
=============================================================

If you have created a local mirror (see :doc:`how_to_partial_mirror`), set ``local_storage_url`` so the solver checks your mirror first:

.. code-block:: yaml

    profiles:
      default:
        local_storage_url:
          - file:///Users/username/storage/  # Unix path
          # - file://C:/storage/             # Windows path

***********************************
 Environment variables (overrides)
***********************************

Environment variables have higher precedence than the configuration file. Use them as temporary overrides (for example, in CI), or when you cannot edit the configuration file.

.. autopydantic_settings:: idf_component_tools.environment.ComponentManagerEnvVariables
    :settings-show-json: false
    :settings-signature-prefix: class
    :settings-show-field-summary: false
    :field-doc-policy: description
    :field-signature-prefix: attribute
