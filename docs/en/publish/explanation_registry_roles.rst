##############################################
 Explanation of Registry Namespaces and Roles
##############################################

This page explains how authorization works in the ESP Component Registry: what namespaces are, which roles exist, and how permissions are modeled.

****************
 Authentication
****************

The registry uses GitHub for authentication. After you log in, the registry can identify you and apply your permissions when you upload or manage components.

*******************************
 Permission model (two scopes)
*******************************

Roles can be granted at two scopes:

- **Namespace scope**: permissions apply to all components in a namespace.
- **Component scope**: permissions apply to a single component (useful for collaborating without granting broad access).

.. _what_is_namespace:

**********************
 What Is a Namespace?
**********************

A *namespace* is a logical container for components. Component names are qualified by namespace to avoid collisions.

By default, when you first log in with GitHub, a namespace matching your GitHub username is automatically created. For example, if your GitHub username is ``jdoe``, your namespace is ``jdoe``.

- **Why use namespaces?** Namespaces keep components organized and prevent naming collisions between different users. For instance, if two users create a component called ``wifi-utilities``, namespaces ensure they don't conflict.
- **How to find or create namespaces?** Each user gets a default namespace automatically. Organizations or teams can request additional namespaces (for example, a ``my-company`` namespace). See :ref:`namespace_requests` for more information.

*****************
 Namespace Roles
*****************

Namespace roles determine what you can do across a namespace.

To collaborate, grant other users a role in your namespace:

- **owner**: full control of the namespace, including managing roles for other users.
- **member**: can manage components in the namespace (for example, upload new versions, yank, and delete).

.. note::

    Only a user with the **owner** role can assign or revoke roles at the namespace level.

*****************
 Component Roles
*****************

Component roles are used when you want to collaborate on a specific component without granting access to the entire namespace.

Available component-level roles:

- **maintainer**: full control over a single component, including managing component roles.
- **developer**: can upload new versions and manage existing versions.

***********************
 Where to manage roles
***********************

You manage roles in the registry web UI under the Permissions area. The UI lets you review which namespaces and components you have access to, and grant or revoke roles.

.. _namespace_requests:

Namespace Requests
==================

If you need a namespace other than your default (for example, an organization namespace), you can request one in the Permissions UI.
