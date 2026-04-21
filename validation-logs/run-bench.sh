#!/usr/bin/env bash
set -u
source "$HOME/.cargo/env" 2>/dev/null || true

ROOT=/mnt/d/SourceCode/mempalace
WS=$ROOT/mempalace-rs
LOG=$ROOT/validation-logs
SMOKE=$HOME/.mempalace-smoke
CACHE=$SMOKE/cache/mempalace/embeddings
mkdir -p "$CACHE"

cd "$WS"

export MEMPALACE_EMBED_CACHE="$CACHE"
export MEMPALACE_EMBED_ALLOW_DOWNLOADS=1
export MEMPALACE_EMBED_ITERATIONS=15

echo "==== embedding_bench: balanced (will download model if absent) ===="
MEMPALACE_EMBED_PROFILE=balanced cargo run -p mempalace-embeddings --example embedding_bench --release --locked --message-format=short 2>&1 | tee "$LOG/bench-balanced.log"
BAL_RC=${PIPESTATUS[0]}
echo "==== balanced EXIT=$BAL_RC ===="

echo
echo "==== embedding_bench: low_cpu ===="
MEMPALACE_EMBED_PROFILE=low_cpu cargo run -p mempalace-embeddings --example embedding_bench --release --locked --message-format=short 2>&1 | tee "$LOG/bench-low-cpu.log"
LOW_RC=${PIPESTATUS[0]}
echo "==== low_cpu EXIT=$LOW_RC ===="

echo
echo "SUMMARY: balanced=$BAL_RC low_cpu=$LOW_RC"
echo "Cache contents:"
find "$CACHE" -maxdepth 4 -type f | head -30
du -sh "$CACHE" 2>/dev/null
