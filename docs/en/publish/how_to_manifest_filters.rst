#########################################
 How to Control Which Files are Uploaded
#########################################

When you upload a component, the tool packages the component directory into an archive. By default, most source and documentation files are included, while build artifacts, IDE configuration, and other common non-source files are excluded automatically.

This page explains how the filtering works and how to customize it.

*******************
 Default behaviour
*******************

If you do not add a ``files`` block to your ``idf_component.yml``, the tool:

1. Starts with **all files** in the component directory.
2. Removes files matching a built-in exclusion list (build artifacts, IDE settings, VCS metadata, etc.). See ``files`` in :doc:`/reference/manifest_file` for the full list.

This is usually sufficient. You only need the ``files`` field when you want to change what is included.

****************************
 Customizing with ``files``
****************************

Add a ``files`` block to ``idf_component.yml`` to customize filtering. There are three options:

.. code-block:: yaml

    files:
       use_gitignore: true
      exclude:
        - "**/.vscode/**"
      include:
        - "include/**"
        - "src/**"

``use_gitignore``
=================

When set to ``true``, the tool uses your ``.gitignore`` rules to decide which files to exclude **instead of** the built-in exclusion list. It creates a temporary Git index in the component directory and asks Git which files are ignored, so standard ``.gitignore`` syntax and inheritance apply.

This is useful when your ``.gitignore`` already describes exactly what should not be shipped.

.. note::

    When ``use_gitignore`` is ``true``, the built-in exclusion list is **not** applied. Only ``.gitignore`` rules (plus any ``exclude`` patterns you add) are used.

``exclude``
===========

A list of glob patterns. Files matching any pattern are removed from the archive. These patterns are applied **after** the built-in exclusion list (or ``.gitignore``, if enabled).

``include``
===========

A list of glob patterns. Files matching any pattern are **added back**, even if they were removed by ``exclude``, ``.gitignore``, or the built-in list. Use this to override specific exclusions.

*************************
 Filter evaluation order
*************************

In short: built-in exclusions (or ``.gitignore``) run first, then ``exclude``, then ``include``. Because ``include`` is applied last, it can override any previous exclusion.

For the precise step-by-step order, see the ``files`` section in :doc:`/reference/manifest_file`.

.. note::

    Filters also apply to example projects located inside the component directory.

*********
 Related
*********

- Full ``files`` schema and default exclusion list: see ``files`` in :doc:`/reference/manifest_file`
