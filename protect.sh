#!/usr/bin/env bash
# Encrypt the private data/code into data.tar.gz.gpg (AES-256, symmetric). Only this archive is committed.
# Passphrase file: $GTFS_PASSFILE or ~/.gtfs-rt-passphrase (never stored in the repo).
set -euo pipefail
cd "$(dirname "$0")"
PF="${GTFS_PASSFILE:-$HOME/.gtfs-rt-passphrase}"
[ -f "$PF" ] || { echo "missing passphrase file: $PF" >&2; exit 1; }
FILES=(build_tubus.py gtfs_tubus tubus_gtfs_draft.zip build.py shapes_lib.py gtfs transmetro_gtfs_draft.zip stops.txt stops_by_line.csv)
KMLS=$(ls reference/*/*.kml reference/*/*.json reference/*/SOURCES.txt 2>/dev/null || true)
tar -czf - "${FILES[@]}" $KMLS | gpg --batch --yes --pinentry-mode loopback --passphrase-file "$PF" \
  --symmetric --cipher-algo AES256 -o data.tar.gz.gpg
echo "wrote data.tar.gz.gpg"
