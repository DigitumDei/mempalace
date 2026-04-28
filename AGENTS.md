# User Instructions

## Memory — MemPalace

MemPalace is the persistent memory store. Use it to remember and recall anything that matters across sessions.

**On session start:** Call `mempalace_status` to orient yourself, then `mempalace_diary_read(agent_name: "claude")` to recall recent context.

**During a session:**
- Before answering questions about people, projects, or past events: search first with `mempalace_kg_query` or `mempalace_search`. Never guess — verify.
- File important decisions, facts, or context with `mempalace_add_drawer`.
- Record structured facts (relationships, states, timelines) with `mempalace_kg_add`.
- When facts change, invalidate the old one with `mempalace_kg_invalidate` before adding the new one.

**On session end:** Write a diary entry with `mempalace_diary_write(agent_name: "claude", ...)` summarising what happened and what matters.

**ALWAYS use MemPalace for memory. Do NOT write new memories to the auto-memory system (`~/.claude/projects/.../memory/`).** The auto-memory files are a read-only legacy fallback — MemPalace is the only memory store. If in doubt, use MemPalace.

## Git Rules
- NEVER commit or push unless the user explicitly asks you to.
- Do not proactively stage, commit, or push changes.
- NEVER push directly to `main` or `master`. Always use a branch and pull request.