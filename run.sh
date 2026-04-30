#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$REPO_DIR/.venv" ]; then
    python3 -m venv "$REPO_DIR/.venv"
    "$REPO_DIR/.venv/bin/pip" install -r "$REPO_DIR/requirements.txt"
fi

source "$REPO_DIR/.venv/bin/activate"

cd "$REPO_DIR/src"

python worker.py &
worker_pid=$!

python app.py &
app_pid=$!

sleep 2
open "http://127.0.0.1:5000"

cleanup() {
    pkill -P "$app_pid" 2>/dev/null || true
    kill "$worker_pid" "$app_pid" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

wait -n "$worker_pid" "$app_pid"
