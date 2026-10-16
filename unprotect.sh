#!/usr/bin/env bash
# Decrypt data.tar.gz.gpg into the working tree (overwrites build.py, gtfs/, etc.).
set -euo pipefail
cd "$(dirname "$0")"
PF="${GTFS_PASSFILE:-$HOME/.gtfs-rt-passphrase}"
[ -f "$PF" ] || { echo "missing passphrase file: $PF" >&2; exit 1; }
gpg --batch --pinentry-mode loopback --passphrase-file "$PF" --decrypt data.tar.gz.gpg | tar -xzf -
echo "decrypted into $(pwd)"
