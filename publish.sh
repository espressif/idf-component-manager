#! /bin/bash
set -eo pipefail

CURRENT_VERSION=$(poetry version -s)

while IFS='' read -r PUBLISHED_VERSION; do
  if  [ "${PUBLISHED_VERSION}" == "${CURRENT_VERSION}" ] ; then
    echo "Version ${CURRENT_VERSION} already published, skipping..."
    exit 0
  fi
done < <(curl https://pypi.org/pypi/idf-component-manager/json 2>/dev/null | jq -r '.releases | keys[]')

echo "Packaging and publishing new version: ${CURRENT_VERSION}"
rm -rf dist
poetry publish --build
