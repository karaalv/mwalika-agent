# schemas/

This directory contains **Pydantic schemas** for all Mwalika Agent resources.

Schemas are grouped by domain to keep contracts explicit and stable across
the system (agent logic, API boundary, storage, and corpus processing).

## Structure

- `corpus/`  
  Entity schemas for the context corpus (e.g. ministries, agencies,
  services) used for retrieval and indexing.

- `api/`  
  API-facing schemas, including WebSocket event payloads, streamed
  response block types, and request/response contracts.

- `memory/`  
  Schemas for agent memory objects persisted to MongoDB (sessions,
  conversation state, user preferences, traces, etc.).

Additional subfolders may be added as new schema domains emerge.

## Conventions

- Schemas should be versioned or backward-compatible when used across
  boundaries (API, stored memory, corpus artefacts).
- Prefer explicit field names and typed enums for `type` fields.
- Keep schemas independent from application services where possible
  to avoid import cycles.
