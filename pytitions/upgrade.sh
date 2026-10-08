#!/usr/bin/env bash
# Upgrades every dependency to the latest compatible version (uv lock --upgrade + uv sync)
# and appends to upgraded.md ONLY the packages that changed, with date and time.
# Run it from anywhere: it always works from the folder where this file lives.
#
# If pyproject.toml still has the exact version pins that migrate.sh copies from pdm.lock
# ([tool.uv] constraint-dependencies), they are removed first: they would block the upgrade.
#
# To go back to an earlier state, restore the files from the commit and sync, e.g.:
#   git checkout <commit> -- uv.lock pyproject.toml && uv sync --all-groups --no-install-package uwsgi
set -euo pipefail
cd "$(dirname "$0")"

LOG=upgraded.md
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")
DIRTY=""
git diff --quiet HEAD -- uv.lock pyproject.toml 2>/dev/null || DIRTY="yes"

# Ask for confirmation first (skip with: ./upgrade.sh --yes)
if [ "${1:-}" != "--yes" ] && [ "${1:-}" != "-y" ]; then
    echo "================================================================"
    echo " ARE YOU SURE? This upgrades ALL dependencies to the latest"
    echo " compatible versions and rewrites uv.lock and .venv. If pyproject.toml"
    echo " has exact version pins (copied from pdm.lock by migrate.sh), they are"
    echo " removed first, otherwise nothing could be upgraded."
    echo
    echo " Current state: commit ${COMMIT}"
    if [ -n "$DIRTY" ]; then
        echo " WARNING: uv.lock or pyproject.toml have UNCOMMITTED changes. If you upgrade now,"
        echo " the current versions can NOT be restored from git."
        echo " Run first:  git add uv.lock pyproject.toml && git commit -m 'lock before upgrade'"
    else
        echo " uv.lock and pyproject.toml are committed: you can go back at any time."
    fi
    echo
    echo " HOW TO GO BACK:"
    echo "   git checkout ${COMMIT} -- uv.lock pyproject.toml"
    echo "   uv sync --all-groups --no-install-package uwsgi"
    echo
    echo " WHAT GETS RECORDED: only the packages that change, with date,"
    echo " time and starting commit, appended to ${LOG}."
    echo " Tip: after upgrading, run the tests (python manage.py test)"
    echo " and commit uv.lock and pyproject.toml if everything is fine."
    echo "================================================================"
    read -r -p "Continue? [y/N] " answer
    case "$answer" in
        y|Y|yes|YES) ;;
        *) echo "Cancelled, nothing changed."; exit 1 ;;
    esac
fi

BEFORE=$(mktemp)
trap 'rm -f "$BEFORE"' EXIT
cp uv.lock "$BEFORE"

echo "1/4 Removing exact version pins from pyproject.toml (if any)"
PINS=$(uvx --from tomlkit python - <<'PYEOF'
import tomlkit

with open("pyproject.toml") as f:
    doc = tomlkit.parse(f.read())
uv_table = doc.get("tool", {}).get("uv", {})
removed = len(uv_table.get("constraint-dependencies", []))
if removed:
    del uv_table["constraint-dependencies"]
    if not uv_table:
        del doc["tool"]["uv"]
    with open("pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(doc))
print(removed)
PYEOF
)
echo "    ${PINS} pins removed"

echo "2/4 Upgrading uv.lock"
uv lock --upgrade

echo "3/4 Installing into .venv"
# uwsgi fails to compile with recent GCC and is only needed in production
uv sync --all-groups --no-install-package uwsgi

echo "4/4 Writing ${LOG}"
[ -n "$DIRTY" ] && COMMIT="${COMMIT}+uncommitted"

uv run --no-sync python - "$BEFORE" uv.lock "$LOG" "$COMMIT" "$PINS" <<'PYEOF'
import sys
import tomllib
from datetime import datetime

before_path, after_path, log_path, commit, pins = sys.argv[1:6]

def versions(path):
    # a package can appear more than once (different python versions): keep all of them
    with open(path, "rb") as f:
        packages = tomllib.load(f)["package"]
    result = {}
    for p in packages:
        result.setdefault(p["name"], set()).add(p["version"])
    return result

old, new = versions(before_path), versions(after_path)
lines = []
for name in sorted(old.keys() | new.keys()):
    a, b = old.get(name), new.get(name)
    if a == b:
        continue
    fmt = lambda v: " / ".join(sorted(v)) if v else "-"
    lines.append(f"- {name}: {fmt(a)} -> {fmt(b)}")

if not lines:
    print("Nothing to upgrade: everything is already up to date.")
    sys.exit(0)

stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
try:
    with open(log_path) as f:
        has_content = bool(f.read().strip())
except FileNotFoundError:
    has_content = False

with open(log_path, "a") as f:
    if has_content:
        f.write("\n---\n\n")
    f.write(f"## {stamp} (starting from commit {commit})\n\n")
    f.write("\n".join(lines) + "\n\n")
    if int(pins):
        f.write(f"Removed {pins} exact version pins from pyproject.toml (copied from pdm.lock by migrate.sh).\n\n")
    if commit.endswith("+uncommitted"):
        f.write("Rollback: NOT possible from git, uv.lock or pyproject.toml were not committed before this upgrade.\n")
    elif commit == "no-git":
        f.write("Rollback: not available, this is not a git repository.\n")
    else:
        f.write(f"Rollback: `git checkout {commit} -- uv.lock pyproject.toml && uv sync --all-groups --no-install-package uwsgi`\n")

print(f"{len(lines)} packages upgraded, details appended to {log_path}")
PYEOF
