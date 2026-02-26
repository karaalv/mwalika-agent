# Mwalika Agent Data Architecture and Storage Contracts

**Version**: 1.0.0

## Conventions

- All data fields across all collections use **snake_case**.
- All API payloads also use **snake_case** for consistency across the project.
- Timestamps are stored as **ISO 8601 strings (UTC)**.
- ISO timestamps are converted to native `datetime` objects within the application layer where required.

These conventions apply across MongoDB documents, Qdrant payloads, and API contracts.

## 1. Overview

This document defines the storage architecture and data contracts for the Mwalika Agent.

The system uses:

- **MongoDB** for structured entity data and application state.
- **Qdrant** for vector embeddings and semantic retrieval.

This document specifies:

- Vector collection configuration.
- MongoDB database and collection structure.
- Expected document schemas.
- Responsibilities of each storage system.

Although the agent is implemented in Python, TypeScript-style interfaces are used here to describe storage contracts clearly and language-agnostically. The corresponding Pydantic schemas in the codebase are the source of truth for implementation.

## 2. Qdrant Vector Storage

Qdrant is used exclusively for semantic search and retrieval.

### 2.1 Configuration

- Embedding model: `text-embedding-3-large`
- Dimensions: `3072`
- Distance metric: `Cosine`
- Vectors are normalised (cosine reduces to dot product in practice).
- A single collection is used for all corpus entities.

```txt
qdrant-cloud
└── Collection: mwalika_corpus
```

### 2.2 Collection Structure

Each corpus item is stored as:

```typescript
interface CorpusItem {
    id: string;
    vector: number[];
    payload: {
        type: 'ministry' | 'department' | 'agency' | 'service';
        schema_version: string;
        entity_id: string;
    };
}
```

### 2.3 Design Principles

- The payload contains only retrieval-relevant metadata.
- Full structured entity data is not duplicated in Qdrant.
- Entity relationships are resolved in the application layer using MongoDB.
- This prevents payload bloat and avoids tight coupling between retrieval and domain logic.

## 3. MongoDB Storage

MongoDB is the primary structured data store for the agent.

It stores:

- Full entity documents.
- Session state.
- Chat history.
- Application-level metadata.

```txt
mongodb
├── Database: mwalika_corpus
│   ├── Collection: ministries
│   ├── Collection: departments
│   ├── Collection: agencies
│   ├── Collection: services
│   └── Collection: faqs
│
├── Database: chats
│   ├── Collection: sessions
│   └── Collection: memories
│
├── Database: mwalika_identity
│   └── Collection: users
│
└── Database: mwalika_security
    ├── Collection: user_usage_stats
    ├── Collection: ip_usage_stats
    └── Collection: blocked_entities
```

Indexes may be added as performance requirements evolve.

### 3.1 Database: mwalika_corpus

Each entity type has its own collection.

Example:

```typescript
interface MinistryEntry {
    ministry_id: string;
    ministry_name: string;
    ministry_description: string;
    ...
}
```

The exact schema for each entity type is defined in the corresponding Pydantic models in the codebase located in `schemas/corpus/`.

### 3.2 Database: chats

The `chats` database stores conversation state and session management data.

#### Collection: sessions

Stores metadata about active and historical chat sessions.

```typescript
interface AgentSession {
    session_id: string;
    user_id: string;
    chat_name: string;
    created_at: string;      // ISO 8601 (UTC)
    last_active_at: string;  // ISO 8601 (UTC)
}
```

#### Collection: memories

Stores conversation history for each session.

Each message is stored as a separate document to allow:

- Efficient pagination.
- Incremental retrieval.
- Streamed updates.

```typescript
interface AgentMemory {
    session_id: string;
    user_id: string;
    message_id: string;
    sender: 'user' | 'agent';
    content: MemoryContent[];
    timestamp: string; // ISO 8601 (UTC)
}

interface MemoryContent {
    type: 'text' | 'image' | 'link';
    payload: string;
}
```

#### Content Model

Messages are stored as an array of content blocks.

This aligns with the agent's structured streaming format (NDJSON-style blocks), enabling:

- Mixed content rendering.
- Image support.
- Future extensibility (buttons, structured outputs, etc.).

### 3.3 Database: mwalika_identity

The `mwalika_identity` database stores user-related data for the anonymous user system.

#### Collection: users

Stores information about anonymous users.

```typescript
interface AnonymousUser {
    user_id: string;
    language_preference: 'english' | 'swahili';
    created_at: string;      // ISO 8601 (UTC)
    last_active_at: string;  // ISO 8601 (UTC)
}
```

### 3.4 Database: mwalika_security

The `mwalika_security` database stores data related to security monitoring, rate limiting, and user behavior tracking.

#### Collection: user_usage_stats

Stores usage statistics for each user.

<!-- TODO: Update these interfaces to match the latest user observer implementation -->
```typescript
interface UserUsageStats {
    user_id: string;
    day_key: string; // e.g. '2024-06-01'
    blocked_count: number;
    last_blocked_at: number | null; // Seconds since epoch
    requests_today: number;
    agent_input_tokens_today: number;
    active_ws_connections: string[]; // List of active WebSocket connection IDs
    bad_requests_today: number; // Requests that triggered security rules
    last_api_request_at: number | null; // Seconds since epoch
    access_tokens_generated_today: number; // Number of access tokens generated today
    claim_cookies_generated_today: number; // Number of claim cookies generated today
}
```

#### Collection: ip_usage_stats

Stores usage statistics for each IP address.

```typescript
interface IpUsageStats {
    ip_address: string;
    day_key: string; // e.g. '2024-06-01'
    blocked_count: number;
    last_blocked_at: number | null; // Seconds since epoch
    requests_today: number;
    agent_input_tokens_today: number;
    active_ws_connections: string[]; // List of active WebSocket connection IDs
    bad_requests_today: number; // Requests that triggered security rules
    last_api_request_at: number | null; // Seconds since epoch
    refresh_tokens_generated_today: number; // Number of refresh tokens generated today
    claim_cookies_generated_today: number; // Number of claim cookies generated today
}
```

#### Collection: blocked_entities

Stores records of blocked entities (users, IP addresses or tokens) for security enforcement.

```typescript
interface BlockedEntity {
    entity_id: string; // user_id, ip_address or token identifier
    entity_type: 'user' | 'ip' | 'refresh_token' | 'access_token';
    reason: string;
    blocked_at: string; // ISO 8601 (UTC)
    blocked_until: int; // Seconds since epoch when the block expires
}
```

## 4. Separation of Responsibilities

| System   | Responsibility                                     |
|----------|----------------------------------------------------|
| Qdrant   | Vector similarity search only                      |
| MongoDB  | Structured data and application state              |
| Agent    | Joins relationships and assembles response context |

Embeddings are stored only in Qdrant. MongoDB does not store embedding vectors.

This separation ensures:

- Lean vector payloads.
- Clear ownership boundaries.
- Scalable retrieval logic.
- Reduced duplication across systems.
