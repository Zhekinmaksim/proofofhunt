#!/usr/bin/env bash
# Start the installed Studio stack without resetting accounts or contracts.
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cli_dir="${GENLAYER_CLI_DIR:-$(npm root -g)/genlayer}"

if [[ ! -f "$cli_dir/docker-compose.yml" ]]; then
  echo "GenLayer CLI Compose file not found: $cli_dir/docker-compose.yml" >&2
  exit 1
fi

# Explicit -f files omit the incomplete web-module override written by CLI
# 0.39.1. Public HTTPS clue sources use the image's complete web configuration.
docker compose --project-directory "$cli_dir" -p genlayer \
  -f "$cli_dir/docker-compose.yml" \
  -f "$project_dir/verification/studio.override.yml" \
  --profile frontend --profile ollama up -d
