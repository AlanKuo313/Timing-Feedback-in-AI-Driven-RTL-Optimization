#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p config/lib
url='https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/master/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
file='config/lib/NangateOpenCellLibrary_typical.lib'
if command -v curl >/dev/null; then
    curl -fL --retry 3 "$url" -o "$file"
elif command -v wget >/dev/null; then
    wget "$url" -O "$file"
else
    echo 'Install curl or wget.' >&2
    exit 1
fi
test "$(wc -c < "$file")" -gt 1000000 || { echo 'Incomplete library download' >&2; exit 1; }
echo "Downloaded $file"
