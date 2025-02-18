FAQ
===

.. contents:: Questions
    :local:
    :depth: 1

Why can't I access the Component Registry?
------------------------------------------

While building ESP-IDF project during dependency resolution, you may see an error message like:

.. code-block:: text

    Cannot establish a connection to the component registry. Are you connected to the internet?

In most cases, the root cause is the configuration of the firewall, either on the computer directly (usually running Windows) or on the corporate network level. In some cases, a firewall can be configured to allow requests from a browser but not from a CLI application.

Please check that these domains are not blocked by any firewall:

- The main registry API server and web interface:

  ``https://components.espressif.com/``

- The main CDN for file storage:

  ``https://components-file.espressif.com/``

If you are located in mainland China, file storage CDN requests may be redirected to the following domain. Please ensure that this domain is also not blocked by any firewall:

    ``https://components-file.espressif.cn/``

- Staging (test) deployment (for development of new components, not required for regular use):

  - API server:

    ``https://components-staging.espressif.com/``

  - File storage CDN:

    ``https://d30mc2df6nu4o1.cloudfront.net``

Connection issues may also be due to TLS certificate verification problems. Some corporate firewalls may replace TLS certificates with custom ones. Starting with IDF Component Manager v2.2.0, if your Python version is 3.10 or newer, it will use system TLS certificates by default.

You can check the current certificate configuration by running the following command in your ESP-IDF Terminal:

.. code-block:: bash

    python -c "import ssl, socket, pprint; hostname='components-file.espressif.com'; context=ssl.create_default_context(); sock=socket.create_connection((hostname, 443)); ssock=context.wrap_socket(sock, server_hostname=hostname); cert=ssock.getpeercert(); sock.close(); pprint.pprint(cert)"

The expected output will contain ``DigiCert Inc`` as the issuer common name and ``*.espressif.com`` as the subject common name, like this:

.. code-block:: python

    {
        "OCSP": ("http://ocsp.digicert.com",),
        "caIssuers": (
            "http://cacerts.digicert.com/DigiCertGlobalG2TLSRSASHA2562020CA1-1.crt",
        ),
        "crlDistributionPoints": (
            "http://crl3.digicert.com/DigiCertGlobalG2TLSRSASHA2562020CA1-1.crl",
            "http://crl4.digicert.com/DigiCertGlobalG2TLSRSASHA2562020CA1-1.crl",
        ),
        "issuer": (
            (("countryName", "US"),),
            (("organizationName", "DigiCert Inc"),),
            (("commonName", "DigiCert Global G2 TLS RSA SHA256 2020 CA1"),),
        ),
        "notAfter": "Jul 10 23:59:59 2026 GMT",
        "notBefore": "Jun  9 00:00:00 2025 GMT",
        "serialNumber": "024F1AAAB75782479831FB77588CA04A",
        "subject": (
            (("countryName", "CN"),),
            (("stateOrProvinceName", "上海市"),),
            (("organizationName", "乐鑫信息科技（上海）股份有限公司"),),
            (("commonName", "*.espressif.com"),),
        ),
        "subjectAltName": (("DNS", "*.espressif.com"), ("DNS", "espressif.com")),
        "version": 3,
    }

If the certificate is different, there are several ways to resolve the issue:

- If you are using a Python version older than 3.10 and the version of IDF Component Manager is less than 2.2.0, consider updating your environment to allow Component Manager to use the system set of certificates.
- You can specify custom CA certificates for verifying HTTPS connections to the Component Registry by setting the ``IDF_COMPONENT_VERIFY_SSL`` environment variable. If you have the root certificate from your IT team in ``.pem`` format, you can save it somewhere on your machine and then set the path to the ``.pem`` file to this environment variable. The component manager will then use the root certificates from the supplied files.
- As a temporary measure, you can disable certificate validation by setting the same ``IDF_COMPONENT_VERIFY_SSL`` to ``0``. However, this option is not recommended for security reasons.

How do I modify a managed component?
------------------------------------

If you want to modify a component that is managed by the Component Manager, the simplest way is to move it from the ``managed_components`` directory to the ``components`` directory.

For example, if you have a component ``namespace__my_component`` in ``managed_components``, you can move it like this:

.. code-block:: bash

    mv managed_components/namespace__my_component components/

After that, you can edit the component files in ``components/namespace__my_component`` as you like. The Component Manager will use the modified component from the ``components`` directory instead of downloading it from the registry.

You can also omit the namespace when moving the component. For example:

.. code-block:: bash

    mv managed_components/namespace__my_component components/my_component

Should I commit the ``managed_components`` directory and ``dependencies.lock`` file?
------------------------------------------------------------------------------------

It is recommended to add the ``managed_components`` directory to your ``.gitignore`` file. The Component Manager will automatically download the required components based on the ``idf_component.yml`` manifest and the ``dependencies.lock`` file.

To ignore the ``managed_components`` directory, add the following line to your ``.gitignore``:

.. code-block:: text

    managed_components/

Whether you should commit the ``dependencies.lock`` file depends on your project. If your project is intended to work with specific hardware, ESP-IDF version and configuration, it is usually a good idea to check it in. This ensures that everyone working on the project (and your CI/CD pipeline) uses the exact same versions of the components, making your builds reproducible.
