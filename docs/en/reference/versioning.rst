Versioning
==========

The IDF Component Manager enforces a strict versioning scheme on all components it manages. Component versioning allows ESP-IDF applications to have more fine-grained control on what features and bug fixes are included in a particular managed component. Furthermore, the IDF Component Manager implements a version solver that allows ESP-IDF applications to specify multiple versions based on a range of versions for a particular component dependency. The version solver will automatically select the most appropriate version of the component based on a predefined set of rules. This document describes the versioning scheme and the rules used by the version solver.

Versioning Scheme
-----------------

A managed component's version number contains the following fields:

.. code-block:: none

   major.minor.patch~revision-prerelease+build

.. list-table:: Version Number Fields
   :widths: 10 10 80
   :header-rows: 1

   *  - Field
      - Optional
      - Description
   *  - Major
      - N
      - There are incompatible API changes between two major versions.
   *  - Minor
      - N
      - There are new features with compatible APIs between two minor versions.
   *  - Patch
      - N
      - There are only bug fixes between two patch versions.
   *  - Revision
      - Y
      -
         - This version should be used when the package mainly depends on an upstream package.
         - There are only downstream code changes between two revision versions.
         - The prepend separator is ``~``, like ``~1``, ``~2``, ``~100``.
         - The revision field has a default value of ``0``.
   *  - Pre-release
      - Y
      -
         - Represents the prerelease version, like ``a1``, ``b2``, ``rc0``.
         - The prepend separator is ``-``, like ``-a1``, ``-b2``, ``-rc0``.
         - This field could be separated into several identifiers by ``.``, like ``-a1.b2``, ``-foo.bar``.
   *  - Build
      - Y
      -
         - Represents the build version, like ``build1``, ``build2``.
         - The prepend separator is ``+``, like ``+a1``, ``+b2``, ``+rc0``.
         - This field could be separated into several identifiers by ``.``, like ``+a1.b2``, ``+foo.bar``.

A full version number containing all fields such as ``0.1.2~3-dev4.7+git5.66`` would be parsed into the following:

- ``major``: ``int`` 0
- ``minor``: ``int`` 1
- ``patch``: ``int`` 2
- ``revision``: ``int`` 3
- ``prerelease``: (``str`` “dev4”, ``int`` 7)
- ``build``: (``str`` “git5”, ``int`` 66)

.. note::
   CLI commands ``compote component pack`` and ``compote component upload`` accept ``--version=git`` to read version from the current git tag. However, ``~`` is not allowed in git tags. Therefore, you must replace ``~`` with  ``.`` in the git tag if your version contains revision. For example, for version ``0.1.2~3`` use git tag ``0.1.2.3`` or ``v0.1.2.3``.


Version Precedence
------------------

When the version solver compares two different version numbers, the solver determines the preeminent version by comparing each field of the two versions from left to right. The version with the leftmost larger field will be the preeminent version. For example:

.. list-table:: Version Precedence Example
   :widths: 35 65
   :header-rows: 1

   *  - Expression
      - Explanation
   *  - ``1.0.0`` > ``0.9.0``
      - First compare the ``major`` field. 1 > 0.
   *  - ``0.2.0`` > ``0.1.9``
      -
         - The ``major`` fields are equal.
         - Secondly compare the ``minor`` field. 2 > 1.
   *  - ``1.2.4`` > ``1.2.3``
      -
         - The ``major``, ``minor`` fields are equal.
         - Thirdly compare the ``patch`` field. 4 > 3.
   *  - ``0.1.2~3`` > ``0.1.2~2``
      -
         - The ``major``, ``minor``, ``update`` fields are equal.
         - Compare the ``revision`` field. 3 > 2.
   *  -
         - ``0.1.2~0`` == ``0.1.2``
         - ``0.1.2~0-a4`` == ``0.1.2-a4``
      - The default value of the revision field is ``0``.
   *  - ``0.1.2-b0`` > ``0.1.2-a3``
      -
         - The ``major``, ``minor``, ``update`` fields are equal.
         - The first identifier of the prerelease field ``b0`` is larger than ``a3`` in alphabetical order.
   *  - ``0.1.2-a0.9`` < ``0.1.2-a0.10``
      -
         - The ``major``, ``minor``, ``update`` fields are equal.
         - The first identifiers of the prerelease fields are equal.
         - The second identifers of the prerelease fields only include the numeric digits. Compare them in numerical order. 9 < 10.
   *  - ``0.1.2-a0`` > ``0.1.2-1000``
      -
         - The ``major``, ``minor``, ``update`` fields are equal.
         - Non-numeric identifier has higher precedence than numeric identifier. ``a0`` > ``1000``.
   *  - ``0.1.2-a.b.c.d`` > ``0.1.2-a.b.c``
      -
         - The ``major``, ``minor``, ``update`` fields are equal.
         - The prerelease field with more identifiers has higher precedence if all the preceding ones are equal.
         - The first three identifiers of the prerelease fields are equal.
         - The prerelease field of the left version has the fourth identifier ``d``, which indicates it has a higher precedence.
   *  - ``0.1.2-a1`` < ``0.1.2``
      -
         - The ``major``, ``minor``, ``update`` fields are equal.
         - The version that includes a prerelease field has lower precedence than its ``major.minor.patch`` version.

.. warning::

   Build version is a special case. According to `semantic versioning <https://semver.org/#spec-item-10>`_, ``build`` must be ignored when determining version precedence. If two version numbers only differ in the ``build`` field, the comparison will yield an unexpected result.

Range Specifications
--------------------

When specifying a range of versions for a component dependency (in an `idf_component.yml`), the range specification should be one of the following:

- A clause
- A comma separated list of clauses (No extra spaces)

Clauses
~~~~~~~

A typical clause includes one operator and one version number. If the clause does not have an operator, the clause will default to the ``==`` operator. For example, the clause ``1.2.3`` is equivalent to the clause ``==1.2.3``.

Comparison Clause
^^^^^^^^^^^^^^^^^

Comparison clauses use one of the following operators: ``>=``, ``>``, ``==``, ``<``, ``<=``, ``!=``

For more detailed information regarding comparing two version numbers, please refer to `the earlier section <#version-precedence>`__

Wildcard Clause
^^^^^^^^^^^^^^^

A wildcard clause uses the symbol ``*`` in one or more fields of the version number. Usually the ``*`` symbol means it could be replaced with anything in this field.

.. warning::

   You may only use the ``*`` symbol in the ``major``, ``minor``, and ``patch`` field.

You may also use the wildcard symbol in the comparison clauses, which make them into wildcard clauses. For example:

- ``==0.1.*`` is equal to ``>=0.1.0,<0.2.0``.
- ``>=0.1.*`` is equal to ``>=0.1.0``.
- ``==1.*`` or ``==1.*.*`` is equal to ``>=1.0.0,<2.0.0``.
- ``>=1.*`` or ``>=1.*.*`` is equal to ``>=1.0.0``.
- ``*``, ``==*`` or ``>=*`` is equal to ``>=0.0.0``.

Compatible Release Clause
^^^^^^^^^^^^^^^^^^^^^^^^^

Compatible release clauses always use the ``~=`` operator. It matches the version that is expected to be compatible with the specified version.

For example:

- ``~=1.2.3-alpha4`` is equal to ``>=1.2.3-alpha4,==1.2.*``.
- ``~=1.2.3`` is equal to ``>=1.2.3,==1.2.*``.
- ``~=1.2`` is equal to ``>=1.2.0,==1.*``.
- ``~=1`` is equal to ``>=1.0,==1.*``.

Compatible Minor Release Clause
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Compatible minor release clauses always use the ``~`` operator. Usually it allows patch-level changes, but it would also allow minor level changes if only a major version is specified.

For example:

- ``~1.2.3-alpha4`` is equal to ``>=1.2.3-alpha4,==1.2.*``.
- ``~1.2.3`` is equal to ``>=1.2.3,==1.2.*``.
- ``~1.2`` is equal to ``>=1.2.0,==1.2.*``.
- ``~1`` is equal to ``>=1.0,==1.*``.

Compatible Major Release Clause
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Compatible major release clauses always use the ``^`` operator. It allows the changes that do not modify the left-most non-zero version.

For example:

- ``^1.2.3-alpha4`` is equal to ``>=1.2.3-alpha4,==1.*``.
- ``^1.2.3`` is equal to ``>=1.2.3,==1.*``.
- ``^1.2`` is equal to ``>=1.2.0,==1.*``.
- ``^1`` is equal to ``>=1.0,==1.*``.
- ``^0.2.3-alpha4`` is equal to ``>=0.2.3-alpha4,==0.2.*``.
- ``^0.2.3`` is equal to ``>=0.2.3,==0.2.*``.
- ``^0.2`` is equal to ``>=0.2.0,==0.2.*``.
- ``^0`` is equal to ``>=0.0.0,==0.0.0*``.

Version Solving
---------------

An ESP-IDF project with component dependencies will specify those dependencies via one or more manifest files (i.e., ``idf_component.yml``), where each dependency will have a range representing the component version(s) of that dependency. Version solving is the process of collecting all component dependencies of an ESP-IDF project, and calculating the most appropriate component version of each dependency. The version solving process generally involves the following steps:

1. Collect all the local manifest files from your main component and subcomponents.
2. Collect all the root dependencies from the manifest files.
3. Recursively collect all the available versions of each root dependency.
4. Calculate the version solving solution.
