Configuration of the IDF Component Manager
==========================================

IDF Component Manager can be configured using two methods:

1. **Configuration File**: A YAML file named ``idf_component_manager.yml`` that defines profiles for component management. More details about this file can be found in the :doc:`Configuration File <../reference/config_file>`.
2. **Environment Variables**: A set of environment variables that can override the settings in the configuration file. These variables are documented below.

.. note::

    Environment variables have higher precedence than the configuration file. If a setting is defined in both the configuration file and an environment variable, the value from the environment variable will be used.

.. autopydantic_settings:: idf_component_tools.environment.ComponentManagerEnvVariables
    :settings-show-json: false
    :settings-signature-prefix: class
    :settings-show-field-summary: false
    :field-doc-policy: description
    :field-signature-prefix: attribute
