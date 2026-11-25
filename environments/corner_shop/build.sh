#!/bin/sh
# Copy the engine and the 10 firms into the package before publishing to the Environments Hub.
set -e
here=$(cd "$(dirname "$0")" && pwd)
rm -rf "$here/corner_shop/going_concern" "$here/corner_shop/firms"
cp -R "$here/../../going_concern" "$here/corner_shop/going_concern"
cp -R "$here/../../firms" "$here/corner_shop/firms"
find "$here/corner_shop" -name __pycache__ -prune -exec rm -rf {} +
