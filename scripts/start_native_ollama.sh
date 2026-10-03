#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
export OLLAMA_HOST=127.0.0.1:11435
export OLLAMA_MODELS="$project_dir/verification/private/ollama-models"
exec ollama serve
