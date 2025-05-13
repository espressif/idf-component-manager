#######################################
 ESP Component Registry Badge Endpoint
#######################################

The ESP Component Registry provides an endpoint for generating a badge that displays the version of uploaded components. These badges are useful for documentation and other resources to indicate the version status of a component.

By default, the badge shows the latest **stable** version of the component. If only **pre-release** versions are available, the badge displays the latest pre-release version. If only **yanked** versions are available, the badge will display the latest yanked version. Clicking the badge redirects users to the component's page on the ESP Component Registry.

The badge endpoint is available at the following URL:

``https://components.espressif.com/components/<namespace>/<name>/badge.svg``

Example:

.. image:: https://components.espressif.com/components/example/cmp/badge.svg
   :target: https://components.espressif.com/components/example/cmp
   :alt: Example Component Registry Badge

******************
 Query Parameters
******************

The badge endpoint supports the following query parameters:

#. **version**

   Displays a specific version of the component on the badge. To specify the version, use the ``version`` query parameter:

   ``https://components.espressif.com/components/<namespace>/<name>/badge.svg?version=1.0.0``

   If the specified version does not exist, an error badge is shown.

   Example:

   .. image:: https://components.espressif.com/components/example/cm/badge.svg
      :target: https://components.espressif.com/components/example/cm
      :alt: Error Badge Example

#. **prerelease**

   Enables display of the latest pre-release version using the ``prerelease`` query parameter:

   ``https://components.espressif.com/components/<namespace>/<name>/badge.svg?prerelease=1``

   If there are no newer pre-release versions than the latest stable release, the badge defaults to showing the latest stable version.

********************************************
 Additional Notes on Badge Display Behavior
********************************************

-  **Stable versions**: Displayed by default, if available.
-  **Pre-release versions**: Displayed if explicitly requested via the ``prerelease`` parameter or when no stable versions exist.
-  **Yanked versions**: Displayed only if no stable or pre-release versions exist.
-  **Error badges**: Displayed when the specified version or component does not exist.
