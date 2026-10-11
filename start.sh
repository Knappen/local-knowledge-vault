#!/usr/bin/env sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ -x "$PROJECT_DIR/.venv/bin/python" ] || { echo 'Run ./setup.sh first.' >&2; exit 1; }
export AIWS_KNOWLEDGE_ROOT="${AIWS_KNOWLEDGE_ROOT:-$PROJECT_DIR/data}"
export HF_HOME="${HF_HOME:-$PROJECT_DIR/.cache/huggingface}"
export AIWS_FASTEMBED_CACHE="${AIWS_FASTEMBED_CACHE:-$PROJECT_DIR/.cache/fastembed}"
export AIWS_ACTIVE_BACKEND="${AIWS_ACTIVE_BACKEND:-http://127.0.0.1:11434}"
export AIWS_PROFILE_ROUTER="${AIWS_PROFILE_ROUTER:-$AIWS_ACTIVE_BACKEND}"
export AIWS_RAG_PYTHON="$PROJECT_DIR/.venv/bin/python"
exec "$AIWS_RAG_PYTHON" "$PROJECT_DIR/portable_server.py"
