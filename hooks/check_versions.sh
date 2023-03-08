#!/bin/bash

pyproject_version=$(awk -F "\"" '/^version\s*=\s*"/ {print $2}' pyproject.toml)
versionpy_version=$(awk -F "'" '/^__version__\s*=\s*/ {print $2}' idf_component_tools/__version__.py)

if [[ "$pyproject_version" == "$versionpy_version" ]]; then
    echo "Versions match"
    exit 0
else
    echo "Versions in pyproject.toml and idf_component_tools/__version__.py do not match"
    exit 1
fi
