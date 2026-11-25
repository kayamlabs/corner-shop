#!/bin/sh
# Copy the engine and the 100 firms into the package (corner_shop/going_concern, corner_shop/firms).
#
# Inside a checkout of the corner-shop repo it copies from ../../. Anywhere else (for example the
# Docker build on OpenReward, whose build context is only this directory) it downloads the engine
# from GitHub at CORNER_SHOP_REF (default: main). Pin CORNER_SHOP_REF to a commit for reproducible builds.
set -e
here=$(cd "$(dirname "$0")" && pwd)
pkg="$here/corner_shop"
rm -rf "$pkg/going_concern" "$pkg/firms"
if [ -d "$here/../../going_concern" ] && [ -d "$here/../../firms" ]; then
    cp -R "$here/../../going_concern" "$pkg/going_concern"
    cp -R "$here/../../firms" "$pkg/firms"
else
    ref="${CORNER_SHOP_REF:-main}"
    python3 - "$pkg" "$ref" <<'PY'
import io, sys, tarfile, urllib.request
pkg, ref = sys.argv[1], sys.argv[2]
url = f"https://codeload.github.com/kayamlabs/corner-shop/tar.gz/{ref}"
data = urllib.request.urlopen(url, timeout=120).read()
with tarfile.open(fileobj=io.BytesIO(data)) as tar:
    for m in tar.getmembers():
        parts = m.name.split("/", 1)
        if len(parts) < 2 or not parts[1].startswith(("going_concern/", "firms/")):
            continue
        if not (m.isfile() or m.isdir()):
            continue
        m.name = parts[1]
        tar.extract(m, pkg)
print(f"engine fetched from {url}")
PY
fi
find "$pkg" -name __pycache__ -prune -exec rm -rf {} +
n=$(ls "$pkg/firms" | grep -c '^corner_shop_.*\.json$' || true)
echo "vendored engine and $n firms into $pkg"
