#################
 Getting Started
#################

The IDF Component Manager comes pre-installed and enabled by default in all `supported ESP-IDF versions <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/versions.html>`_.

********************************************
 Checking the IDF Component Manager Version
********************************************

If you're unsure which version of the IDF Component Manager is included in your ESP-IDF installation, you can check it using a CLI command.

First, activate the `ESP-IDF environment <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/index.html#installation>`_, then run the help command:

.. tabs::

   .. group-tab::

      Windows

      Open ``ESP-IDF PowerShell Environment`` or ``ESP-IDF Command Prompt (cmd.exe)`` from the Start menu and run the following command:

      .. code:: powershell

         > compote version

   .. group-tab::

      macOS and Linux (bash or zsh)

      .. code:: bash

         $ source $IDF_PATH/export.sh
         $ compote version

   .. group-tab::

      macOS and Linux (fish)

      .. code:: fishshell

         $ . $IDF_PATH/export.fish
         $ compote version

If you're using an older version of the Component Manager, the ``compote version`` command might not be available. In that case, consider upgrading to the latest version. For details, see `Upgrading the IDF Component Manager <#installing-and-upgrading-the-idf-component-manager>`_.
