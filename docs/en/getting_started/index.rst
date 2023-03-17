Getting Started
===============

Supported ESP-IDF Versions
--------------------------

The IDF Component Manager requires `ESP-IDF <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/index.html#installation>`_ v4.1 and later.

The IDF Component Manager is included and enabled by default in all ESP-IDF versions starting with v4.4. For older minor versions of ESP-IDF, the component manager is enabled by default in the following bugfix releases:

- ESP-IDF v5.x and later
- ESP-IDF v4.4.x and later
- ESP-IDF v4.3.3 and later
- ESP-IDF v4.2.4 and later

.. warning::

    If you are using ESP-IDF versions 4.2.0, 4.2.1, 4.2.2, 4.2.3, 4.3.0, 4.3.1, or 4.3.2, you need to install the IDF Component Manager manually. See :doc:`Installing the IDF Component Manager </guides/updating_component_manager>`.

Checking the IDF Component Manager Version
------------------------------------------

If you don't know whether your version of ESP-IDF includes the IDF Component Manager, you can check the version of the IDF Component Manager.

To check the installed version of the IDF component manager, first, activate the `ESP-IDF environment <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/index.html#installation>`_, then run the help command:

.. tabs::

    .. group-tab:: Windows

        Run ``ESP-IDF PowerShell Environment`` or ``ESP-IDF Command Prompt (cmd.exe)`` from the Start menu and run the following command:

        .. code-block:: powershell

            > python -m idf_component_manager -h

    .. group-tab:: macOS and Linux (bash or zsh)

        .. code-block:: bash

            $ source $IDF_PATH/export.sh
            $ python -m idf_component_manager -h

    .. group-tab:: macOS and Linux (fish)

        .. code-block:: fishshell

            $ . $IDF_PATH/export.fish
            $ python -m idf_component_manager -h

Recent versions of the component manager also support the ``compote version`` command. If the ``compote`` command is not available in your IDF Component Manager, please consider upgrading it to the latest version. See `Upgrading the IDF Component Manager <#installing-and-upgrading-the-idf-component-manager>`_.
