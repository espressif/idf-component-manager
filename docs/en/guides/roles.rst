#############################################
 Authorization in the ESP Component Registry
#############################################

Users can authenticate into the ESP Component Registry using their GitHub account. This allows them to:

-  Upload and manage components in the registry
-  Access the registry's API
-  Manage various access and permission settings

Roles are used to control access in the ESP Component Registry. They can be assigned at two levels:

#. **Namespace Level** - Grants access and permissions within a particular namespace.
#. **Component Level** - Grants more fine-grained control for individual components.

.. _what_is_namespace:

**********************
 What Is a Namespace?
**********************

A *namespace* in the ESP Component Registry is a logical container for your components. By default, when you first log in using GitHub, you automatically get a namespace that matches your GitHub username. For example, if your GitHub username is `jdoe`, you will have a namespace named `jdoe` in the registry.

-  **Why use namespaces?** Namespaces keep your components organized and prevent naming collisions with components of other users. If two users want to create a component named `wifi-utilities`, having separate namespaces ensures that the components don't conflict.
-  **How to find or create namespaces?** The default namespace for each user is created automatically. Organizations or teams can request or create additional namespaces (for example, an organization might have a `my-company` namespace). See :ref:`namespace_requests` for more details on creating additional namespaces.

*****************
 Namespace Roles
*****************

When a user logs into the ESP Component Registry, they automatically gain access to the namespace that corresponds to their GitHub username. This means they can start uploading components and managing them under that namespace.

If you want to grant access to your namespace to other users (e.g., collaborators), you can assign one of the following roles:

-  **owner** - Automatically assigned to the user who created the namespace. - Can manage components in the namespace - upload new component versions, yank and delete existing component versions - Can manage namespace roles for other users (assign, modify or revoke their roles).
-  **member** - Can manage components in the namespace - upload new component versions, yank and delete component versions

.. note::

   Only a user with the **owner** role can assign or revoke roles from others at the namespace level.

*****************
 Component Roles
*****************

While namespace roles apply to all components under a namespace, sometimes you need more granular control over a specific component. That's where **component roles** come in. By assigning roles at the component level, you can let others collaborate on a single component without giving them control over all components in your namespace.

The following component-level roles are available:

-  **maintainer** - Can manage all aspects of a single component - upload new versions, yank and delete existing versions - Managing component roles for other users - Useful when you want someone else to help maintain a component but not all components in your namespace.
-  **developer** - Can perform actions needed to develop a component - upload new versions, yank and delete existing versions

***************************************
 Managing Roles in the Permissions Tab
***************************************

You can manage roles for both your namespaces and components through the ESP Component Registry web interface. Navigate to the dropdown, and click on the **Permissions** tab. Here, you can:

-  Create a request for a new namespace (see :ref:`namespace_requests`)
-  View a list of all namespaces you have access to

Clicking on a namespace name will lead you to the namespace's permissions page, where you can:

-  View a list of all users with roles in the namespace
-  Assign or revoke roles for users in the namespace
-  View a list of all components in the namespace
-  Click on a component name to view its permissions page

On the component permissions page, you can:

-  View a list of all users with roles for the component
-  Assign or revoke roles for users for the component

.. _namespace_requests:

Namespace Requests
==================

If you need a namespace, which is not your default namespace (e.g., you want a namespace for your organization), you can request one by following these steps:

#. **Log in** to the ESP Component Registry using your GitHub account.
#. **Navigate** to the **Permissions** tab.
#. Fill in the **Request a new namespace** form with the name you want for your new namespace.
