#!/bin/bash
# Build a ZIP that can be extracted into the Maya modules folder.
# how to use: bash .github/scripts/build_zip.sh v3.3.0 [output folder]
set -eu

tag="$1"
cd "$(dirname "$0")/../.."
output="$(cd "${2:-.}" && pwd)"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

git archive --prefix=guidrawer/ "$tag" | tar -x -C "$stage"

# The .mod at the ZIP root points at the guidrawer folder next to it.
# The copy inside the folder has the same name and would clash, so it is not packed.
if ! grep -q '^+ guidrawer [^ ]* guidrawer' "$stage/guidrawer/guidrawer.mod"; then
  echo "::error::guidrawer.mod does not point at the guidrawer folder"
  exit 1
fi
mv "$stage/guidrawer/guidrawer.mod" "$stage/guidrawer.mod"
rm -rf "$stage/guidrawer/.github" "$stage/guidrawer/.gitignore"

(cd "$stage" && zip -qr "$output/guidrawer-$tag.zip" guidrawer.mod guidrawer)
echo "$output/guidrawer-$tag.zip"
