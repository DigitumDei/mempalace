#!/usr/bin/env bash
# Fires on UserPromptSubmit. On the first message of each session, injects
# an additionalContext reminder to read MemPalace before responding.
input=$(cat)
sid=$(echo "$input" | jq -r '.session_id // "unknown"')
marker="/tmp/claude-mp-$sid"
if [ ! -f "$marker" ]; then
  touch "$marker"
  printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"[Session orientation pending] Before responding to this message, call mempalace_status then mempalace_diary_read with agent_name=claude to orient yourself. Do this first."}}'
fi
