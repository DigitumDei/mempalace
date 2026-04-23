#!/usr/bin/env bash
set -u
source "$HOME/.cargo/env" 2>/dev/null || true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WS="$ROOT/mempalace-rs"
LOG="$SCRIPT_DIR"
mkdir -p "$LOG"

cd "$WS"

SUMMARY="$LOG/test-summary.txt"
: > "$SUMMARY"

overall=0
for crate in mempalace-embeddings mempalace-storage mempalace-ingest mempalace-graph mempalace-mcp mempalace-cli; do
  echo "=========================================="
  echo "==== TESTING $crate ===="
  echo "=========================================="
  cargo test -p "$crate" --locked --message-format=short -- --nocapture > "$LOG/test-$crate.log" 2>&1
  rc=$?
  tail -15 "$LOG/test-$crate.log"
  echo "---- $crate EXIT=$rc ----"
  echo "$crate EXIT=$rc" >> "$SUMMARY"
  if [ $rc -ne 0 ]; then overall=$rc; fi
done

echo
echo "=========================================="
echo "SUMMARY:"
cat "$SUMMARY"
exit $overall
