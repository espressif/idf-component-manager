# Root Managed Components

This document is for ESP-IDF and IDF Component Manager developers. Root managed
components are an internal ESP-IDF integration mechanism, not a public manifest
feature for application developers.

## Purpose

Root managed components let ESP-IDF declare extra components that are installed
once per ESP-IDF installation and then reused by projects built with that ESP-IDF.
They are declared in:

```text
$IDF_PATH/tools/idf_extra_components.yml
```

The flow is split into two phases:

1. **Install time**: the ESP-IDF installer/EIM runs Component Manager and
   downloads the root managed component inventory.
2. **Configure time**: ESP-IDF project configuration reads the installed
   inventory and selects the records required for the active build target.

Project builds must not download root managed components. If the install state is
missing or stale, configure fails and asks the user to run the installer command.

## Internal commands

The install-time command is:

```text
compote cooking stock
```

It installs root managed components from `$IDF_PATH/tools/idf_extra_components.yml`.

The configure-time Component Manager integration is exposed through the existing
prepare/inject flow. ESP-IDF currently invokes the prepare-components entry point,
and newer integration code can route the same work through hidden `compote cooking`
commands.

## Root manifest validation

`idf_extra_components.yml` is intentionally more restricted than a normal
component manifest:

- direct non-meta dependencies must use the ESP Component Registry source;
- direct root dependencies must not use `rules`;
- direct root dependencies must not use `matches`.

The file is a download catalog for ESP-IDF-managed components. Conditional logic
belongs in the downloaded components' own manifests, where it can be evaluated at
configure time for the active target/environment.

## Storage layout

Root managed components are stored under the Component Manager tools directory,
partitioned by full ESP-IDF version:

```text
$IDF_TOOLS_PATH/root_managed_components/idf<idf-version>/
```

If `IDF_TOOLS_PATH` is not set, the usual Component Manager config directory is
used.

The component payload layout is versioned so multiple versions of the same
component can coexist:

```text
root_managed_components/idf6.2.0/
  namespace/
    component/
      version/
        namespace__component/
```

The final directory keeps the normal managed-component build-name convention
(`namespace__component`) because ESP-IDF derives the build component name from the
component directory basename.

## Install state

The installer writes:

```text
root_components.lock
```

next to the root-managed component storage. This file is an installed inventory,
not a solved dependency graph. Each record stores:

- canonical component name;
- installed version;
- relative path to the installed component directory;
- optional `targets` from the component version metadata.

The lock also stores the hash of `idf_extra_components.yml`. Configure-time code
uses this hash to detect missing or stale installations.

## Install-time behavior

`compote cooking stock`:

1. locates `$IDF_PATH/tools/idf_extra_components.yml`;
2. cleans root-managed storage if the file is missing or has no dependencies;
3. validates the root manifest restrictions;
4. walks the dependency graph breadth-first from the root manifest;
5. downloads registry component artifacts into the versioned root-managed layout;
6. prunes installed component directories that are no longer tracked;
7. writes `root_components.lock`.

For each dependency requirement, the installer considers the base version spec and
version specs from conditional entries in transitive manifests. For each spec it
selects a target-covering version set from registry metadata, then deduplicates by
canonical component name and concrete version.

## Configure-time behavior

During project configure, `ComponentManager.prepare_dep_dirs()` checks whether
`$IDF_PATH/tools/idf_extra_components.yml` exists.

If it exists:

1. the root manifest is loaded and validated;
2. `root_components.lock` is loaded;
3. the lock hash must match the current root manifest hash;
4. the active root-managed graph is resolved against installed records only;
5. selected records are emitted to ESP-IDF as `idf_managed_components`.

No network access or component download should happen in this phase.

Selection uses the active build target and the installed inventory:

- records whose `targets` do not include the active target are ignored;
- version specs from direct and transitive requirements are accumulated;
- a backtracking resolver chooses one installed version per component name;
- component manifests are loaded from the installed component directories to
  expand transitive requirements.

If no installed record satisfies the active graph, configure reports that root
managed components must be reinstalled.

## ESP-IDF integration notes

ESP-IDF developers changing this integration should keep these boundaries:

- install-time code may download and prune root managed storage;
- configure-time code must only read the installed inventory;
- the root manifest hash is the freshness check between the two phases;
- root managed storage is per full ESP-IDF version;
- local project components still have normal ESP-IDF precedence over managed
  components in the build system.
