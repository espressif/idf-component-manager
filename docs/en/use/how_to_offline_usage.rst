######################################
 How to Use Component Manager Offline
######################################

By default, the component manager downloads components from the ESP Component Registry over the internet during builds. If you are working in an air-gapped environment, on a restricted network, or simply want reproducible builds without network dependencies, you can point the version solver at a local mirror instead.

The workflow is to synchronize the required components to a local directory while having connectivity, then configure builds to resolve from that directory.

*************************
 Create a partial mirror
*************************

Create a mirror directory and sync the components you need:

.. code-block:: console

    $ compote registry sync --project-dir /path/to/project /path/to/mirror

For more options (sync a single component, version ranges, recursive projects), see :doc:`how_to_partial_mirror`.

****************************************
 Configure the solver to use the mirror
****************************************

Add your mirror to ``local_storage_url`` in ``idf_component_manager.yml`` so it is checked before online sources. See :doc:`how_to_partial_mirror` for a full example, and :ref:`url_precedence` for how the solver picks between local and remote sources.

*********
 Related
*********

- Create and manage partial mirrors: :doc:`how_to_partial_mirror`
- Configuration file reference: :doc:`/reference/config_file`
