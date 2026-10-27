#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
# Optional trusted local shell configuration; never commit this file.
if [[ -f "$ROOT_DIR/.env.tunnel" ]]; then source "$ROOT_DIR/.env.tunnel"; fi
TUNNEL_HOST=${TUNNEL_HOST:-34.35.70.11}
TUNNEL_USER=${TUNNEL_USER:-kabisatunnel}
TUNNEL_KEY=${TUNNEL_KEY:-$HOME/.ssh/kabisa/kabisa_main_access_key.pem}
TUNNEL_KEY=${TUNNEL_KEY/#\~/$HOME}
TUNNEL_PORT=${TUNNEL_PORT:-5440}
TUNNEL_REMOTE_HOST=${TUNNEL_REMOTE_HOST:-127.0.0.1}
TUNNEL_REMOTE_PORT=${TUNNEL_REMOTE_PORT:-5433}
TUNNEL_SSH_PORT=${TUNNEL_SSH_PORT:-22}
TUNNEL_BACKOFF=${TUNNEL_BACKOFF:-3}
[[ -r "$TUNNEL_KEY" ]] || { echo "Tunnel key is not readable: $TUNNEL_KEY" >&2; exit 1; }
if timeout 1 bash -c 'exec 3<>/dev/tcp/127.0.0.1/"$1"' _ "$TUNNEL_PORT" 2>/dev/null; then
    echo "Port $TUNNEL_PORT is already in use; keep the existing tunnel or stop it first." >&2
    exit 1
fi
CONTROL_DIR=$(mktemp -d)
child=
cleanup() { [[ -z "$child" ]] || kill "$child" 2>/dev/null || true; rm -rf -- "$CONTROL_DIR"; }
trap cleanup EXIT
trap 'exit 0' INT TERM
while true; do
    ssh -M -S "$CONTROL_DIR/socket" -p "$TUNNEL_SSH_PORT" -i "$TUNNEL_KEY" \
        -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 \
        -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
        -L "127.0.0.1:$TUNNEL_PORT:$TUNNEL_REMOTE_HOST:$TUNNEL_REMOTE_PORT" \
        -N "$TUNNEL_USER@$TUNNEL_HOST" &
    child=$!
    for ((attempt=0; attempt<15; attempt++)); do
        if ssh -S "$CONTROL_DIR/socket" -O check "$TUNNEL_USER@$TUNNEL_HOST" >/dev/null 2>&1; then
            echo "Tunnel connected: localhost:$TUNNEL_PORT → $TUNNEL_HOST:$TUNNEL_REMOTE_PORT"
            break
        fi
        kill -0 "$child" 2>/dev/null || break
        sleep 1
    done
    wait "$child" || true
    child=
    echo "Tunnel disconnected; reconnecting in ${TUNNEL_BACKOFF}s."
    sleep "$TUNNEL_BACKOFF"
done
