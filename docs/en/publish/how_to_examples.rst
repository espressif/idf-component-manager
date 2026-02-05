####################################
 How to Package and Upload Examples
####################################

This page explains how example projects are discovered and included when you upload a component.

*****************************
 Declare example directories
*****************************

By default, the registry auto-discovers examples under the ``examples`` directory.

If your examples live elsewhere, list them explicitly in the manifest:

.. code-block:: yaml

    examples:
      - path: custom_example_path_1
      - path: custom_example_path_2

*************************************************
 Using local overrides while developing examples
*************************************************

When developing an example project that depends on your component, you may want to temporarily use a local copy of a registry component. Use ``override_path`` in a project's manifest dependencies.

*********
 Related
*********

- Manifest reference (``examples`` and ``override_path``): :doc:`/reference/manifest_file`
