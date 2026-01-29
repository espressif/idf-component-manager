#################
 Component Files
#################

An ESP-IDF component is a modular piece of code compiled into your project by the build system. A component typically contains source files, headers, and a required ``CMakeLists.txt`` file that registers it with the build system. A component may also include ``Kconfig`` (and, less commonly, ``Kconfig.projbuild``) to expose configuration options via ``menuconfig``. For full details on build system concepts, the component model, and configuration, see the `ESP-IDF Build System guide <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/build-system.html>`_.

This page explains which files should be present in a component and how the ESP Component Registry processing treats them. It is written for component authors who want predictable behaviour when publishing components.

*******************************************
 Core files every component should include
*******************************************

CMakeLists.txt
==============

The file must live in the component root so ESP-IDF recognizes the component. Typical contents call ``idf_component_register`` and set include paths and sources. For details see `Component CMakeLists Files <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/build-system.html#component-cmakelists-files>`_.

idf_component.yml (recommended)
===============================

The manifest file for describing metadata of the component and its dependencies located in the root of the component. The manifest is optional for uploads.

Recommended manifest fields include: ``version``, ``description``, ``url``, and ``maintainers``. The manifest controls which files are included in the published archive via the ``files`` section (``use_gitignore``, ``exclude``, ``include``). See the full manifest reference in :doc:`manifest_file`.

README.md (recommended)
=======================

The registry consumes the component README as the authoritative user documentation. Provide a README at the component root. Language variants are supported (for example ``readme_zh.md``).

When present at the component root the processor also publishes ``API.md`` and ``CHANGELOG.md`` alongside the README. Files named ``API.md`` or ``CHANGELOG.md`` that appear inside example directories are ignored for example records; only example README files are published for examples.

LICENSE / LICENSE.txt
=====================

The registry will detect and copy a license file. You are also advised to set the SPDX identifier in ``idf_component.yml`` using the ``license`` field.

**********
 Examples
**********

Put example projects under an ``examples`` directory in the component root. The registry discovers examples automatically by scanning that directory recursively.

Each example must be self-contained: examples must not depend on files outside their own directory. This guarantees examples can be downloaded and built independently.

The processor repackages each example into its own archives. It also records archive names and sizes for display and download. Name collisions between examples (for instance when examples defined outside of the component directory are merged) are detected and conflicted examples are renamed to avoid collisions.

******************************
 How documentation is handled
******************************

The README (and its language variants) is published as component documentation on the registry. API and changelog files at the component root are published when present; API and changelog files inside examples are ignored.

Language variants: suffix README with an underscore and language code, for example ``readme_zh.md``. The processing code validates and normalises language tags before publishing.

Example README files (``README.md`` and language variants) will be processed and displayed on the example page.

*************************
 Checksums and integrity
*************************

The component processing computes checksums for the packaged files and publishes a checksums file alongside component artifacts so clients can verify integrity.
