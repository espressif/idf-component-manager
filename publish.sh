#! /bin/bash
set -eo pipefail

python -m build
CURRENT_VERSION=$(ls dist | grep -oP '(?<=idf_component_manager-).*(?=-py3-none-any.whl)' | tail -1)

while IFS='' read -r PUBLISHED_VERSION; do
  if  [ "${PUBLISHED_VERSION}" == "${CURRENT_VERSION}" ] ; then
    echo "Version ${CURRENT_VERSION} already published, skipping..."
    exit 0
  fi
done < <(curl https://pypi.org/pypi/idf-component-manager/json 2>/dev/null | jq -r '.releases | keys[]')

echo "Publishing new version: ${CURRENT_VERSION}"
twine upload dist/*
