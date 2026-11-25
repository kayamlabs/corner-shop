#!/bin/sh
# Copy the engine and the 100 firms into server/ before building, serving or pushing to a Space.
set -e
here=$(cd "$(dirname "$0")" && pwd)
rm -rf "$here/server/going_concern" "$here/server/firms"
cp -R "$here/../../going_concern" "$here/server/going_concern"
cp -R "$here/../../firms" "$here/server/firms"
find "$here/server" -name __pycache__ -prune -exec rm -rf {} +
