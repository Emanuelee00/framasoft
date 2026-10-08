#!/usr/bin/env bash
# Migrates the project from pdm to uv, keeping the exact versions from pdm.lock.
# Run it from anywhere: it always works from the folder where this file lives.
set -euo pipefail
cd "$(dirname "$0")"

# numpy 1.24.4 (from pdm.lock) has no prebuilt package for Python 3.12+, so 3.11 is the default.
# Override it when running the script, e.g.: PYTHON_VERSION=3.8 bash migrate.sh
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"

echo "1/5 Exporting exact versions from pdm.lock to pinned.txt"
uvx pdm export -f requirements --without-hashes -G :all -o pinned.txt

echo "2/5 Creating a fresh .venv with Python ${PYTHON_VERSION}"
uv python install "${PYTHON_VERSION}"
rm -rf .venv
uv venv --python "${PYTHON_VERSION}" .venv

echo "3/5 Writing version constraints and dev groups into pyproject.toml (backup: pyproject.toml.bak)"
[ -f pyproject.toml.bak ] || cp pyproject.toml pyproject.toml.bak
uvx --from tomlkit python - <<'PYEOF'
import tomlkit

with open("pyproject.toml") as f:
    doc = tomlkit.parse(f.read())

# pdm stores dev dependencies in [tool.pdm.dev-dependencies]; uv reads [dependency-groups]
groups = doc.get("dependency-groups", tomlkit.table())
for name, deps in doc["tool"]["pdm"]["dev-dependencies"].items():
    groups[name] = list(deps)
doc["dependency-groups"] = groups

# Pin every package (direct and indirect) to the version pdm locked
with open("pinned.txt") as f:
    pins = [line.strip() for line in f if "==" in line and not line.startswith("#")]
uv_table = doc["tool"].get("uv", tomlkit.table())
uv_table["constraint-dependencies"] = pins
doc["tool"]["uv"] = uv_table

with open("pyproject.toml", "w") as f:
    f.write(tomlkit.dumps(doc))
PYEOF

echo "4/5 Locking and installing with uv"
uv lock
# uwsgi 2.0.26 fails to compile with recent GCC and is only needed in production,
# so we lock it as usual but skip installing it for development
uv sync --all-groups --no-install-package uwsgi

echo "5/5 Comparing installed versions with the pdm lock"
uv pip freeze | sed 's/ *;.*//' | tr 'A-Z_' 'a-z-' | sort > installed.txt
sed 's/ *;.*//' pinned.txt | grep -vi '^uwsgi==' | tr 'A-Z_' 'a-z-' | sort > expected.txt
if diff expected.txt installed.txt; then
    echo "OK: installed versions match pdm.lock"
else
    echo "WARNING: some versions differ, see the diff above"
fi

echo "Done. Run the server with: uv run --no-sync python pytition/manage.py runserver"
