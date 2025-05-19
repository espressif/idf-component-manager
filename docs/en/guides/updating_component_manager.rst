###################################################
 Installing and Updating the IDF Component Manager
###################################################

To update the IDF Component Manager to the latest version, run the following commands.

.. note::

   If your version of ESP-IDF does not include the IDF Component Manager, you can install it using the same commands.

.. tabs::

   .. group-tab::

      Windows

      Open the ``ESP-IDF PowerShell Environment`` or ``ESP-IDF Command Prompt (cmd.exe)`` from the Start menu, then run:

      .. code:: powershell

         > python -m pip install --upgrade idf-component-manager

   .. group-tab::

      macOS and Linux (bash or zsh)

      .. code:: bash

         $ source $IDF_PATH/export.sh
         $ python -m pip install --upgrade idf-component-manager

   .. group-tab::

      macOS and Linux (fish)

      .. code:: fishshell

         $ . $IDF_PATH/export.fish
         $ python -m pip install --upgrade idf-component-manager
