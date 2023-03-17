#!/bin/bash

# This script checks that the version in pyproject.toml and idf_component_tools/__version__.py match.
pyproject_version=$(awk -F "= " '/^version/ {gsub(/"/, "", $2); print $2}' pyproject.toml)
versionpy_version=$(awk -F "'" '/^__version__/ {print $2}' idf_component_tools/__version__.py)


if [[ "${pyproject_version}" == "${versionpy_version}" ]]; then
    echo "Versions match"
    exit 0
else
    echo "ERROR: Versions in pyproject.toml ($pyproject_version) and idf_component_tools/__version__.py ($versionpy_version) do not match"
    exit 1
fi
