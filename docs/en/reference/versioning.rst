Versioning
==========

The IDF Component Manager enforces a strict versioning scheme on all components it manages. Component versioning allows ESP-IDF applications to have more fine-grained control over which features and bug fixes are included in a particular managed component. Additionally, the IDF Component Manager implements a version solver that allows ESP-IDF applications to specify a range of acceptable versions for a component dependency. The version solver will automatically select the most appropriate version of the component based on predefined rules. This document describes the versioning scheme and the rules used by the version solver.

.. _versioning-scheme:

Versioning Scheme
-----------------

A managed component’s version number contains the following fields:

.. code-block:: none

    major.minor.patch~revision-prerelease+build

.. list-table:: Version Number Fields
    :widths: 10 10 80
    :header-rows: 1

    - - Field
      - Optional
      - Description
    - - Major
      - N
      - There are incompatible API changes between two major versions.
    - - Minor
      - N
      - There are new features with compatible APIs between two minor versions.
    - - Patch
      - N
      - There are only bug fixes between two patch versions.
    - - Revision
      - Y
      - - This version should be used if the package mainly depends on an upstream package.
        - There are only downstream code changes between two revisions.
        - The prefix separator is ``~``, such as ``~1``, ``~2``, ``~100``.
        - The revision field defaults to ``0``.
    - - Pre-release
      - Y
      - - Represents the prerelease version, such as ``a1``, ``b2``, ``rc0``.
        - The prefix separator is ``-``, like ``-a1``, ``-b2``, ``-rc0``.
        - This field may be separated into multiple identifiers by ``.``, such as ``-a1.b2``, ``-foo.bar``.
    - - Build
      - Y
      - - Represents the build version, like ``build1``, ``build2``.
        - The prefix separator is ``+``, like ``+a1``, ``+b2``, ``+rc0``.
        - This field may be separated into multiple identifiers by ``.``, such as ``+a1.b2``, ``+foo.bar``.

A full version number with all fields, such as ``0.1.2~3-dev4.7+git5.66``, would be parsed as follows:

- ``major``: ``int`` 0
- ``minor``: ``int`` 1
- ``patch``: ``int`` 2
- ``revision``: ``int`` 3
- ``prerelease``: (``str`` “dev4”, ``int`` 7)
- ``build``: (``str`` “git5”, ``int`` 66)

.. note::

    CLI commands ``compote component pack`` and ``compote component upload`` accept ``--version=git`` to read the version from the current Git tag. However, ``~`` is not allowed in Git tags. Therefore, if your version contains a revision, you must replace ``~`` with ``.`` in the Git tag. For example, for version ``0.1.2~3``, use the Git tag ``0.1.2.3`` or ``v0.1.2.3``.

Version Precedence
------------------

When the version solver compares two different version numbers, it determines the higher version by comparing each field from left to right. The version with the first larger (leftmost) field is considered the higher version. For example:

.. list-table:: Version Precedence Example
    :widths: 35 65
    :header-rows: 1

    - - Expression
      - Explanation
    - - ``1.0.0`` > ``0.9.0``
      - First compare the ``major`` field. 1 > 0.
    - - ``0.2.0`` > ``0.1.9``
      - - The ``major`` fields are equal.
        - Secondly compare the ``minor`` field. 2 > 1.
    - - ``1.2.4`` > ``1.2.3``
      - - The ``major``, ``minor`` fields are equal.
        - Thirdly compare the ``patch`` field. 4 > 3.
    - - ``0.1.2~3`` > ``0.1.2~2``
      - - The ``major``, ``minor``, ``update`` fields are equal.
        - Compare the ``revision`` field. 3 > 2.
    - - - ``0.1.2~0`` == ``0.1.2``
        - ``0.1.2~0-a4`` == ``0.1.2-a4``
      - The default value of the revision field is ``0``.
    - - ``0.1.2-b0`` > ``0.1.2-a3``
      - - The ``major``, ``minor``, ``update`` fields are equal.
        - The first identifier of the prerelease field ``b0`` is larger than ``a3`` in alphabetical order.
    - - ``0.1.2-a0.9`` < ``0.1.2-a0.10``
      - - The ``major``, ``minor``, ``update`` fields are equal.
        - The first identifiers of the prerelease fields are equal.
        - The second identifiers of the prerelease fields only include the numeric digits. Compare them in numerical order. 9 < 10.
    - - ``0.1.2-a0`` > ``0.1.2-1000``
      - - The ``major``, ``minor``, ``update`` fields are equal.
        - Non-numeric identifier has higher precedence than numeric identifier. ``a0`` > ``1000``.
    - - ``0.1.2-a.b.c.d`` > ``0.1.2-a.b.c``
      - - The ``major``, ``minor``, ``update`` fields are equal.
        - The prerelease field with more identifiers has higher precedence if all the preceding ones are equal.
        - The first three identifiers of the prerelease fields are equal.
        - The prerelease field of the left version has the fourth identifier ``d``, which indicates it has a higher precedence.
    - - ``0.1.2-a1`` < ``0.1.2``
      - - The ``major``, ``minor``, ``update`` fields are equal.
        - The version that includes a prerelease field has lower precedence than its ``major.minor.patch`` version.

.. warning::

    The build version is a special case. According to `Semantic Versioning <https://semver.org/#spec-item-10>`_, the ``build`` field must be ignored when determining version precedence. If two version numbers differ only in the ``build`` field, the comparison may yield an unexpected result.

.. _version-range-specifications:

Range Specifications
--------------------

When specifying a version range for a dependency (in `idf_component.yml`), the specification must be:

- A single clause, or
- A comma-separated list of clauses (no extra spaces).

Clauses
~~~~~~~

A typical clause includes one operator and one version number. If a clause does not specify an operator, it defaults to the ``==`` operator. For example, the clause ``1.2.3`` is equivalent to ``==1.2.3``.

Comparison Clause
+++++++++++++++++

Comparison clauses use one of the following operators: ``>=``, ``>``, ``==``, ``<``, ``<=``, or ``!=``.

For more detailed information about comparing two version numbers, refer to `the earlier section <#version-precedence>`__.

Wildcard Clause
+++++++++++++++

A wildcard clause uses the symbol ``*`` in one or more fields of the version number. Typically, the ``*`` symbol means that any value is acceptable in that field.

.. warning::

    You may use the ``*`` symbol only in the ``major``, ``minor``, and ``patch`` fields.

You can also use the wildcard symbol in comparison clauses, turning them into wildcard clauses. For example:

- ``==0.1.*`` is equivalent to ``>=0.1.0,<0.2.0``.
- ``>=0.1.*`` is equivalent to ``>=0.1.0``.
- ``==1.*`` or ``==1.*.*`` is equivalent to ``>=1.0.0,<2.0.0``.
- ``>=1.*`` or ``>=1.*.*`` is equivalent to ``>=1.0.0``.
- ``*``, ``==*``, or ``>=*`` is equivalent to ``>=0.0.0``.

Compatible Release Clause
+++++++++++++++++++++++++

Compatible release clauses always use the ``~=`` operator. They match versions that are expected to be compatible with the specified version.

For example:

- ``~=1.2.3-alpha4`` is equivalent to ``>=1.2.3-alpha4,==1.2.*``.
- ``~=1.2.3`` is equivalent to ``>=1.2.3,==1.2.*``.
- ``~=1.2`` is equivalent to ``>=1.2.0,==1.*``.
- ``~=1`` is equivalent to ``>=1.0,==1.*``.

Compatible Minor Release Clause
+++++++++++++++++++++++++++++++

Compatible minor release clauses always use the ``~`` operator. They usually allow patch-level changes, but also allow minor-level changes if only the major version is specified.

For example:

- ``~1.2.3-alpha4`` is equivalent to ``>=1.2.3-alpha4,==1.2.*``.
- ``~1.2.3`` is equivalent to ``>=1.2.3,==1.2.*``.
- ``~1.2`` is equivalent to ``>=1.2.0,==1.2.*``.
- ``~1`` is equivalent to ``>=1.0,==1.*``.

Compatible Major Release Clause
+++++++++++++++++++++++++++++++

Compatible major release clauses always use the ``^`` operator. They allow changes that do not modify the left-most non-zero version field.

For example:

- ``^1.2.3-alpha4`` is equivalent to ``>=1.2.3-alpha4,==1.*``.
- ``^1.2.3`` is equivalent to ``>=1.2.3,==1.*``.
- ``^1.2`` is equivalent to ``>=1.2.0,==1.*``.
- ``^1`` is equivalent to ``>=1.0,==1.*``.
- ``^0.2.3-alpha4`` is equivalent to ``>=0.2.3-alpha4,==0.2.*``.
- ``^0.2.3`` is equivalent to ``>=0.2.3,==0.2.*``.
- ``^0.2`` is equivalent to ``>=0.2.0,==0.2.*``.
- ``^0`` is equivalent to ``>=0.0.0,==0.0.0*``.
