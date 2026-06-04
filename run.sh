#!/usr/bin/env bash
#
# run.sh — one-command setup + run for build_llms_full.py
#
# Creates a local virtual environment (.venv) the first time it runs,
# installs the dependencies into it, then runs the build script.
# Safe to run repeatedly — it reuses the venv on later runs.
#
# Usage:
#   ./run.sh                       # build with defaults
#   ./run.sh --out llms-full.txt   # any build_llms_full.py args pass through
#
set -euo pipefail

# Always work from the directory this script lives in.
cd "$(dirname "$0")"

VENV_DIR=".venv"

# Pick a Python 3 interpreter.
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "Error: Python 3 not found. Install it from https://www.python.org/downloads/ and retry." >&2
  exit 1
fi

# Create the venv on first run.
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in $VENV_DIR ..."
  "$PY" -m venv "$VENV_DIR"
fi

# Use the venv's own python/pip — no need to 'activate'.
VENV_PY="$VENV_DIR/bin/python"

echo "Installing dependencies ..."
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet -r requirements.txt

echo "Running build_llms_full.py ..."
"$VENV_PY" build_llms_full.py "$@"
