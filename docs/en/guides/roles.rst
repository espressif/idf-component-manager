#############################################
 Authorization in the ESP Component Registry
#############################################

Users can authenticate into the ESP Component Registry using their GitHub account. This allows them to:

-  Upload and manage components in the registry
-  Access the registry's API
-  Manage access and permission settings

Roles are used to control access within the ESP Component Registry. They can be assigned at two levels:

#. **Namespace Level** – Grants access and permissions within a specific namespace.
#. **Component Level** – Provides more fine-grained control over individual components.

.. _what_is_namespace:

**********************
 What Is a Namespace?
**********************

A *namespace* in the ESP Component Registry is a logical container for your components. By default, when you first log in with GitHub, a namespace matching your GitHub username is automatically created. For example, if your GitHub username is `jdoe`, your namespace will be `jdoe`.

-  **Why use namespaces?** Namespaces keep components organized and prevent naming collisions between different users. For instance, if two users create a component called `wifi-utilities`, namespaces ensure they don't conflict.
-  **How to find or create namespaces?** Each user gets a default namespace automatically. Organizations or teams can request additional namespaces (e.g., a `my-company` namespace). See :ref:`namespace_requests` for more information.

*****************
 Namespace Roles
*****************

When a user logs into the ESP Component Registry, they automatically gain access to their personal namespace (matching their GitHub username), allowing them to upload and manage components.

To grant access to your namespace to other users (e.g., collaborators), assign them one of the following roles:

-  **owner** – Automatically assigned to the creator of the namespace. - Can manage all components in the namespace. - Can upload new versions, yank, or delete components. - Can manage namespace roles for other users (assign, modify or revoke their roles).
-  **member** – Can manage components in the namespace: - Can upload new versions, yank, and delete components.

.. note::

   Only a user with the **owner** role can assign or revoke roles at the namespace level.

*****************
 Component Roles
*****************

While namespace roles apply to all components within a namespace, component roles offer more granular control over individual components. That's where component roles come in. Assigning roles at the component level allows collaboration on specific components without granting broader access.

Available component-level roles:

-  **maintainer** – Full control over a single component. - Can upload, yank, or delete versions. - Can manage component roles for other users. - Useful for delegating control over a specific component.
-  **developer** – Limited control. - Can upload new versions, yank, and delete existing versions.

***************************************
 Managing Roles in the Permissions Tab
***************************************

You can manage roles for both namespaces and components using the ESP Component Registry web interface. To access role management:

#. Open the dropdown menu
#. Click on the **Permissions** tab

Here, you can:

-  Create a request for a new namespace (see :ref:`namespace_requests`)
-  View a list of all namespaces you have access to

Clicking a namespace name opens its permissions page, where you can:

-  View a list of all users with roles in the namespace
-  Assign or revoke roles for users in the namespace
-  View a list of all components in the namespace
-  Click a component name to open its permissions page

On the component permissions page, you can:

-  View a list of users and their roles for the component
-  Assign or revoke roles for users at the component level

.. _namespace_requests:

Namespace Requests
==================

If you need a namespace other than your default (e.g., for an organization), request one by following these steps:

#. **Log in** to the ESP Component Registry using your GitHub account.
#. **Go to** the **Permissions** tab.
#. Fill out the **Request a new namespace** form with your desired namespace name.
