#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"
if [[ -f .env.tunnel ]]; then source .env.tunnel; fi
TUNNEL_PORT=${TUNNEL_PORT:-5440}
if ! timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/"$1"' _ "$TUNNEL_PORT" 2>/dev/null; then
    echo "No database tunnel on localhost:$TUNNEL_PORT. Run pnpm dev:tunnel in another terminal." >&2
    exit 1
fi
for port in "${API_PORT:-8000}" 5173; do
    if timeout 1 bash -c 'exec 3<>/dev/tcp/127.0.0.1/"$1"' _ "$port" 2>/dev/null; then
        echo "Port $port is already in use. Stop the existing dev server before pnpm dev:all." >&2
        exit 1
    fi
done
api_pid= web_pid=
cleanup() {
    [[ -z "$api_pid" ]] || kill -- "-$api_pid" 2>/dev/null || true
    [[ -z "$web_pid" ]] || kill -- "-$web_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' INT TERM
setsid bash scripts/dev-api.sh & api_pid=$!
setsid pnpm dev:web & web_pid=$!
echo "Starting admin: http://localhost:5173 | API: http://localhost:${API_PORT:-8000}/docs"
wait -n "$api_pid" "$web_pid"
