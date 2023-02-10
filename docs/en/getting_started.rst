Getting Started
===============

Supported ESP-IDF versions
--------------------------

The IDF Component Manager requires `ESP-IDF <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/index.html#installation>`_ v4.1 and later.

The IDF Component Manager is included and enabled by default in all ESP-IDF versions starting with v4.4. For older minor versions of ESP-IDF, the component manager is enabled by default in the following bugfix releases:

- ESP-IDF v4.1.3 and later
- ESP-IDF v4.2.4 and later
- ESP-IDF v4.3.3 and later

Checking the IDF Component Manager version
------------------------------------------

If you don't know whether your version of ESP-IDF includes the IDF Component Manager, you can check the version of the IDF Component Manager.

To check the installed version of the IDF component manager, first, activate `ESP-IDF environment <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/index.html#installation>`_ then run help command:

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

Recent versions of the component manager also support ``compote version`` command.

Installing and Upgrading the IDF Component Manager
--------------------------------------------------

If you your version ESP-IDF doesn't come with IDF Component Manager you can install it manually. You can use the same command to upgrade the IDF Component Manager to the latest version:

.. tabs::

    .. group-tab:: Windows

        Run ``ESP-IDF PowerShell Environment`` or ``ESP-IDF Command Prompt (cmd.exe)`` from the Start menu and run the following command:

        .. code-block:: powershell

            > python -m pip --upgrade idf-component-manager

    .. group-tab:: macOS and Linux (bash or zsh)

        .. code-block:: bash

            $ source $IDF_PATH/export.sh
            $ python -m pip --upgrade idf-component-manager

    .. group-tab:: macOS and Linux (fish)

        .. code-block:: fishshell

            $ . $IDF_PATH/export.fish
            $ python -m pip --upgrade idf-component-manager
