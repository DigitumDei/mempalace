#!/usr/bin/env bash
set -u
source "$HOME/.cargo/env" 2>/dev/null || true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WS="$ROOT/mempalace-rs"
LOG="$SCRIPT_DIR"
CLI=$WS/target/release/mempalace-cli
MCP=$WS/target/release/mempalace-mcp

mkdir -p "$LOG"
OUT=$LOG/smoke.log
: > "$OUT"

SMOKE=$HOME/.mempalace-smoke
# Preserve cache (populated by run-bench.sh); only reset fixture/palace/config.
rm -rf "$SMOKE/fixture" "$SMOKE/palace" "$SMOKE/config"
mkdir -p "$SMOKE/fixture/notes" "$SMOKE/fixture/planning" "$SMOKE/palace" "$SMOKE/config" "$SMOKE/cache"

cat > "$SMOKE/fixture/notes/welcome.md" <<'EOF'
# Welcome

This is the welcome note for the smoke test fixture. It introduces the project.
EOF

cat > "$SMOKE/fixture/notes/overview.md" <<'EOF'
# Overview

The mempalace smoke test exercises init, mine, search, status, and wake-up on a fresh palace.
It ingests a handful of markdown files to verify end-to-end behavior.
EOF

cat > "$SMOKE/fixture/planning/roadmap.md" <<'EOF'
# Roadmap

Phase 12 release readiness covers final validation, packaging, and operator documentation.
EOF

# Pin state away from the user's real ~/.mempalace
export XDG_CACHE_HOME="$SMOKE/cache"
export MEMPALACE_EMBED_CACHE="$SMOKE/cache/mempalace/embeddings"
export MEMPALACE_EMBED_ALLOW_DOWNLOADS=1

# Isolate config by pointing HOME at the smoke dir so ~/.mempalace lives inside.
HOME="$SMOKE/config"
mkdir -p "$HOME"

PALACE="$SMOKE/palace"

overall=0
run() {
  local label="$1"; shift
  echo "################################################################" | tee -a "$OUT"
  echo "### $label" | tee -a "$OUT"
  echo "### $ $*" | tee -a "$OUT"
  echo "################################################################" | tee -a "$OUT"
  "$@" >>"$OUT" 2>&1
  local rc=$?
  echo "### EXIT=$rc" | tee -a "$OUT"
  echo | tee -a "$OUT"
  if [ $rc -ne 0 ]; then
    echo "### FAILED: $label" | tee -a "$OUT"
    overall=$rc
  fi
  return $rc
}

run "1. mempalace-cli --help" "$CLI" --help
run "2. mempalace-cli init"   "$CLI" --palace "$PALACE" init --yes "$SMOKE/fixture"
run "3. mempalace-cli mine"   "$CLI" --palace "$PALACE" mine "$SMOKE/fixture"
run "4. mempalace-cli search" "$CLI" --palace "$PALACE" search "roadmap"
run "5. mempalace-cli status" "$CLI" --palace "$PALACE" status
run "6. mempalace-cli wake-up" "$CLI" --palace "$PALACE" wake-up

echo "################################################################" | tee -a "$OUT"
echo "### 7. mempalace-mcp initialize + tools/list (stdio)" | tee -a "$OUT"
echo "################################################################" | tee -a "$OUT"
MCP_INPUT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
MCP_OUT=$(printf '%s\n' "$MCP_INPUT" | "$MCP" 2>>"$OUT")
MCP_RC=$?
echo "$MCP_OUT" | tee -a "$OUT"
echo "### MCP EXIT=$MCP_RC" | tee -a "$OUT"

if echo "$MCP_OUT" | grep -q '"protocolVersion":"2024-11-05"' && \
   echo "$MCP_OUT" | grep -q 'mempalace_status'; then
  echo "### MCP smoke OK" | tee -a "$OUT"
else
  echo "### MCP smoke FAILED" | tee -a "$OUT"
  overall=1
fi
if [ $MCP_RC -ne 0 ]; then overall=$MCP_RC; fi

echo "################################################################" | tee -a "$OUT"
echo "DONE. Log: $OUT" | tee -a "$OUT"
exit $overall
