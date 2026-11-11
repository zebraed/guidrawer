#!/bin/bash
# how to use: bash .github/scripts/check_version.sh v3.3.0
set -eu

tag="$1"
cd "$(dirname "$0")/../.."

tag_version="${tag#v}"
init_version=$(tr -d '\r' < python/guidrawer/__init__.py | sed -n 's/^__version__ = "\(.*\)"$/\1/p')
echo "tag=$tag_version __init__.py=$init_version"

if [ "$tag_version" != "$init_version" ]; then
  echo "::error::The versions of the tag and python/guidrawer/__init__.py must match"
  exit 1
fi
