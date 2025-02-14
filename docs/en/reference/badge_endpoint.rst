#######################################
 ESP Component Registry Badge Endpoint
#######################################

The ESP Component Registry provides an endpoint for generating a badge that displays the version of uploaded components. These badges are useful for documentation or other resources to indicate the version status of a component.

By default, the badge displays the latest stable version of the component. If only pre-release versions are available, the badge will show the latest pre-release version. If only yanked versions are available, the badge will display the latest yanked version. Clicking the badge redirects the user to the component page on the ESP Component Registry.

The endpoint is available at the following URL:

``https://components.espressif.com/components/<namespace>/<name>/badge.svg``

Example:

.. image:: https://components.espressif.com/components/example/cmp/badge.svg
   :target: https://components.espressif.com/components/example/cmp
   :alt: Example Component Registry Badge

******************
 Query Parameters
******************

The endpoint supports the following query parameters:

#. **version**

   Specify the version of the component to display on the badge by adding the ``version`` query parameter to the URL. For example:

   ``https://components.espressif.com/components/<namespace>/<name>/badge.svg?version=1.0.0``

   If the specified version is not available, the badge will display an error message.

   Example:

   .. image:: https://components.espressif.com/components/example/cm/badge.svg
      :target: https://components.espressif.com/components/example/cm
      :alt: Error Badge Example

#. **prerelease**

   Specify whether to use the ``pre-release`` query parameter to display the latest prerelease version or not. For example:

   ``https://components.espressif.com/components/<namespace>/<name>/badge.svg?prerelease=1``

   If there are no pre-release versions newer than the latest stable version, the badge will display the latest stable version.

********************************************
 Additional Notes on Badge Display Behavior
********************************************

-  **Stable versions**: Displayed by default if available.
-  **Pre-release versions**: Displayed when explicitly requested via the ``prerelease`` query parameter or if no stable version exists.
-  **Yanked versions**: Displayed only when no stable or pre-release versions exist.
-  **Error badges**: Displayed if the specified version or component does not exist.
