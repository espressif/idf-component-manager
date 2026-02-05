############################
 How to Update Dependencies
############################

This page shows how to update component dependencies for an ESP-IDF project.

*************************
 Update all dependencies
*************************

From your project directory, run:

.. code-block:: console

    $ idf.py update-dependencies

This triggers dependency resolution and updates ``dependencies.lock`` if the resolved set changes.

****************
 What to expect
****************

- If your manifests did not change and the existing locked versions still satisfy constraints, the solver may keep the current versions.
- If constraints changed (or previously selected versions no longer satisfy them), the solver picks a new consistent set.

*********
 Related
*********

- How solving works and when it runs: :doc:`/use/explanation_version_solver`
- Lockfile reference: :doc:`/reference/dependencies_lock`
