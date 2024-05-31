Getting Started
===============

The IDF Component Manager is included and enabled by default in all `supported ESP-IDF <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/versions.html>`_ versions.

Checking the IDF Component Manager Version
------------------------------------------

If you are unsure which version of the IDF Component Manager is included in your ESP-IDF installation, you can find out by running a CLI command.

First, activate the `ESP-IDF environment <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/index.html#installation>`_, then run the help command:

.. tabs::

    .. group-tab:: Windows

        Run ``ESP-IDF PowerShell Environment`` or ``ESP-IDF Command Prompt (cmd.exe)`` from the Start menu and run the following command:

        .. code-block:: powershell

            > compote version

    .. group-tab:: macOS and Linux (bash or zsh)

        .. code-block:: bash

            $ source $IDF_PATH/export.sh
            $ compote version

    .. group-tab:: macOS and Linux (fish)

        .. code-block:: fishshell

            $ . $IDF_PATH/export.fish
            $ compote version

Older versions of the component manager may not include the ``compote version`` command. If the command is not available in your IDF Component Manager, please consider upgrading it to the latest version. See `Upgrading the IDF Component Manager <#installing-and-upgrading-the-idf-component-manager>`_.
