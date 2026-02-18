# Supermemory Integration (Current Branch)

This document reflects the memory integration as implemented in the current working tree.

## At a glance

| Backend | Class | Storage | Selected when |
|---|---|---|---|
| Local memory | `MemoryStore` | `workspace/memory/MEMORY.md` + `workspace/memory/HISTORY.md` | `supermemory.api_key` is empty |
| Supermemory | `SupermemoryStore` | Supermemory API + local fallback (`MemoryStore`) | `supermemory.api_key` is set |

## What changed recently

- Introduced explicit local memory backend in `nanobot/agent/memory.py`.
- Updated backend selection in:
  - `nanobot/agent/context.py`
  - `nanobot/agent/loop.py`
- Added Supermemory fallback paths in `nanobot/agent/super_memory.py`:
  - `add_memory(...)` falls back to local `HISTORY.md` append on errors.
  - `get_user_long_term_memory(...)` falls back to local `MEMORY.md`.
  - `get_memory_context(...)` falls back to local memory context.
- Consolidation flow in `nanobot/agent/loop.py` now branches by backend:
  - Local backend writes `history_entry` to `HISTORY.md` and updates `MEMORY.md`.
  - Supermemory backend sends both `history_entry` and `memory_update` to Supermemory.

## File map

| File | Responsibility |
|---|---|
| `nanobot/agent/memory.py` | Local memory store (`MEMORY.md`, `HISTORY.md`) |
| `nanobot/agent/super_memory.py` | Supermemory-backed store with local fallback |
| `nanobot/agent/context.py` | Injects memory context into system prompt |
| `nanobot/agent/loop.py` | Runtime memory writes + consolidation |
| `nanobot/config/schema.py` | `SupermemoryConfig` (`api_key`, `container_tag`) |

## Runtime behavior

### 1) Backend selection

Both `ContextBuilder` and `AgentLoop` read config and choose memory backend using the same rule:

- `supermemory.api_key` present -> `SupermemoryStore(workspace)`
- otherwise -> `MemoryStore(workspace)`

### 2) Prompt-time memory retrieval (`ContextBuilder`)

- Calls `self.memory.get_memory_context(query=current_message)`.
- If memory text exists, injects it under `# Memory` in system prompt.
- Wrapped in `try/except` with fallback attempt to basic memory retrieval.

### 3) Message-time persistence (`AgentLoop`)

- Session history is always saved to `SessionManager`.
- Additional memory write after each response:
  - only when active backend is `SupermemoryStore` (`self.memory.add_memory(final_content)`).

### 4) Consolidation (`_consolidate_memory`)

- Builds conversation summary prompt for LLM and expects JSON:
  - `history_entry`
  - `memory_update`
- Backend-specific write path:
  - `MemoryStore`: append `history_entry`, update long-term file if changed.
  - `SupermemoryStore`: send both fields via `add_memory(...)`.

## Configuration

`~/.nanobot/config.json`:

```json
{
  "supermemory": {
    "api_key": "YOUR_SUPERMEMORY_API_KEY",
    "container_tag": "nanobot_memory"
  }
}
```

- Leave `api_key` empty to stay fully local.
- `container_tag` defaults to `nanobot_memory` in `SupermemoryStore`.

## Quick verification checklist

1. Local-only mode (`api_key=""`)
   - Confirm writes happen in `workspace/memory/MEMORY.md` and `workspace/memory/HISTORY.md`.
2. Supermemory mode (`api_key` set)
   - Confirm context comes from Supermemory profile.
   - Confirm responses and consolidation outputs are sent via `add_memory(...)`.
3. Failure fallback
   - Force Supermemory API failure and confirm fallback reads/writes use local `MemoryStore`.
