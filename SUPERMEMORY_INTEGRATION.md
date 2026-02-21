# Supermemory Integration

This document describes the **current implementation** of Supermemory integration in this repository.

## Scope

Code paths verified during this scan:

- `nanobot/agent/super_memory.py`
- `nanobot/agent/loop.py`
- `nanobot/agent/context.py`
- `nanobot/agent/memory.py`
- `nanobot/session/manager.py`
- `nanobot/config/schema.py`
- `nanobot/config/loader.py`
- `nanobot/agent/prompt_library.py`
- `tests/SuperMemoryTests.py`

## Architecture Overview

There are two memory backends:

1. `MemoryStore` (local filesystem)
- `workspace/memory/MEMORY.md` for long-term memory
- `workspace/memory/HISTORY.md` for append-only history

2. `SupermemoryStore` (remote + local fallback)
- Uses Supermemory SDK and direct HTTP call to `https://api.supermemory.ai/v4/conversations`
- Uses local `MemoryStore` as fallback for some operations
- Persists failed uploads to `~/.nanobot/failed_sessions/*.jsonl`

Backend selection is config-driven in both `ContextBuilder` and `AgentLoop`:

- `supermemory.api_key` is set -> `SupermemoryStore`
- `supermemory.api_key` is empty -> `MemoryStore`

## Configuration

Defined in `nanobot/config/schema.py`:

```json
{
  "supermemory": {
    "api_key": "",
    "container_tag": ""
  }
}
```

Runtime defaults:

- `container_tag` falls back to `nanobot_memory` in `SupermemoryStore.__init__`
- config file path is `~/.nanobot/config.json`

## Runtime Flows

### 1) Prompt-time memory retrieval (`ContextBuilder`)

`ContextBuilder.build_system_prompt(...)` calls `self.memory.get_context(query=...)`.

- Local backend: returns content derived from local `MEMORY.md`
- Supermemory backend: calls `supermemory_client.profile(container_tag=..., q=..., threshold=0.6)` and builds context from:
  - `profile.static`
  - `profile.dynamic`
  - `search_results.results`

If retrieval fails, code falls back to `get_memory_context()`.

### 2) Normal message handling (`AgentLoop._process_message`)

For non-`/new` messages:

- session messages are appended and saved via `SessionManager`
- automatic consolidation trigger runs only for `MemoryStore` when history exceeds `memory_window`

### 3) `/new` flow and `clear_session`

`/new` now routes through `run_command(..., clear_session: bool)`.

Behavior:

- If backend is `SupermemoryStore`, agent first calls `update_conversation(messages, session)`
- On upload success:
  - schedules `clear_failed_sessions()` replay task
  - calls `run_command(..., clear_session=True)` (session is cleared)
- On upload failure/exception:
  - calls `run_command(..., clear_session=False)` (session is preserved)
- If backend is local `MemoryStore`:
  - calls `run_command(..., clear_session=True)`

`run_command` always schedules consolidation of archived messages, but only clears persisted session state when `clear_session=True`.

### 4) Consolidation flow (`AgentLoop._consolidate_memory`)

Consolidation uses provider output JSON with keys:

- `history_entry`
- `memory_update`

Write behavior:

- `MemoryStore`:
  - append `history_entry` to `HISTORY.md`
  - write `memory_update` to `MEMORY.md` if changed
- `SupermemoryStore`:
  - sends both `history_entry` and `memory_update` via `add_memory(...)`

Prompt templates come from `PromptLibrary`.

## SupermemoryStore API + Fallback Details

### `update_conversation(messages, session)`

- Sends HTTP POST to `/conversations`
- payload:
  - `conversationId = "session_{container_tag}"`
  - `messages = [...]`
- success condition: HTTP 200

On failure:

- logs exception
- if `session` is provided: saves session JSONL to `~/.nanobot/failed_sessions/{session_key}.jsonl`
- returns `False`

### `clear_failed_sessions()` replay

- iterates `~/.nanobot/failed_sessions/*.jsonl`
- parses file lines as messages
- calls `update_conversation(messages, None)`
- unlinks file after call in current control flow

### `add_memory(content)`

- primary: `supermemory_client.add(...)`
- fallback on exception: append to local `HISTORY.md`

### `get_user_long_term_memory()`

- primary: `supermemory_client.profile(container_tag=...)`
- fallback: local `MEMORY.md`

## Session Persistence Model

Session storage is managed by `SessionManager`:

- primary session files: `~/.nanobot/sessions/*.jsonl`
- failed Supermemory upload artifacts: `~/.nanobot/failed_sessions/*.jsonl`

`Session` tracks:

- `messages`
- `metadata`
- `last_consolidated`

## Tests

`tests/SuperMemoryTests.py` covers:

- successful upload/session clear behavior
- failed upload persistence to `failed_sessions`
- replay success/partial success/failure behavior
- long payload integrity
- disabled Supermemory fallback to local memory
- `run_command(clear_session=True/False)` semantics

The test module is written to run on plain `pytest` (no async plugin required) by using `asyncio.run(...)` wrappers.

## Current Implementation Notes

- Some debug `print(...)` statements remain in Supermemory/context paths.
- `SupermemoryStore` imports `os` but does not use it.
- `PromptLibrary.build_identity_prompt(...)` currently ignores its `workspace` argument and uses `self.workspace_path` internally; docs above reflect the behavior as implemented.

