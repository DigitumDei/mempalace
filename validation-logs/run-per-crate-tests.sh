#!/usr/bin/env bash
set -u
source "$HOME/.cargo/env"
cd /mnt/d/SourceCode/mempalace/mempalace-rs

LOG=/mnt/d/SourceCode/mempalace/validation-logs
mkdir -p "$LOG"

SUMMARY="$LOG/test-summary.txt"
: > "$SUMMARY"

for crate in mempalace-embeddings mempalace-storage mempalace-ingest mempalace-graph mempalace-mcp mempalace-cli; do
  echo "=========================================="
  echo "==== TESTING $crate ===="
  echo "=========================================="
  cargo test -p "$crate" --locked --message-format=short -- --nocapture > "$LOG/test-$crate.log" 2>&1
  rc=$?
  tail -15 "$LOG/test-$crate.log"
  echo "---- $crate EXIT=$rc ----"
  echo "$crate EXIT=$rc" >> "$SUMMARY"
done

echo
echo "=========================================="
echo "SUMMARY:"
cat "$SUMMARY"
