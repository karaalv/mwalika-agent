# Streaming Architecture

## Overview

Mwalika uses a WebSocket-based streaming architecture to deliver agent responses to the frontend in real time.

The system is designed to:

- Stream token-level responses from the LLM
- Support structured chunks (images, links, markdown text)
- Maintain clean separation of concerns
- Apply back-pressure safely
- Support multi-tab connections per user
- Be easily extended to a distributed architecture (Redis / PubSub / Streams)

This document describes the full streaming stack from payload format to infrastructure components.

## 1. Payload Strategy

### 1.1 Markdown for Text

All natural language content from the agent is streamed as Markdown chunks.

This allows the frontend to:

- Render progressively
- Support formatting (bold, lists, code blocks)
- Avoid re-parsing large documents

Example chunk:

```json
{
    "type": "text",
    "payload": "The capital of France is **Paris**.",
    "memory_id": "12345678",
    "sequence_number": 1
}
```

### 1.2 NDJSON for Structured Blocks

Structured content is sent as NDJSON-style blocks.

This is used for:

- Images
- External links
- Action cards
- Embedded metadata

Each block is self-contained and independently renderable.

Why NDJSON:

- Allows streaming heterogeneous content
- Keeps parsing simple on the client
- Enables incremental rendering
- Avoids deeply nested streaming schemas

## 2. Stream Semantics

Each agent run is treated as an independent stream.

Every streamed message includes:

- stream.id – unique per agent execution
- stream.seq – monotonically increasing sequence number

This enables:

- Deterministic ordering
- Duplicate protection
- Future reconnection support
- Debug traceability

Sequence numbers are per stream, not global.

## 3. WebSocket Infrastructure

The WebSocket layer is responsible strictly for transport.

It does not contain agent logic.

It does not generate content.

It only delivers structured messages.

### 3.1 WebSocketManager

Each WebSocket connection is assigned a WebSocketManager.

Responsibilities:

- Maintain a bounded per-connection message queue
- Serialize all outgoing sends
- Enforce backpressure
- Send heartbeat messages
- Handle send failures safely
- Close cleanly on error

Single Writer Pattern:

Each manager runs:

- _message_sender() – consumes queue
- _heartbeat_loop() – periodic liveness signal

All outbound messages go through the queue.

There are no concurrent writes to the WebSocket.

### 3.2 Backpressure Model

Backpressure is enforced at the connection level.

Each connection has a bounded queue:

- If the client is slow, queue fills
- Producers block on await queue.put()
- Prevents unbounded memory growth

The system does not drop token chunks.

If a connection becomes too slow, it may be closed.

Backpressure is not handled globally. It is scoped per connection.

### 3.3 Heartbeat

Heartbeat:

- Sent periodically
- Ensures connection remains alive
- Helps detect dead sockets

Heartbeat messages are queued like normal messages to maintain single-writer guarantees.

## 4. Socket Registry

The SocketRegistry maintains active connections per user.

Structure:

user_id -> connection_id -> WebSocketManager

Supports:

- Multi-tab
- Multi-device
- Broadcast to user
- Send to specific connection
- Graceful shutdown

The registry:

- Is concurrency-safe (asyncio.Lock)
- Never holds locks during network I/O
- Cleans up connections on disconnect

Lifecycle is owned by the FastAPI lifespan context.

## 5. Event Bus Architecture

### 5.1 Purpose

The Event Bus decouples:

- Agent execution
- Transport delivery

Agent code does not call WebSocketManager directly.

Instead it publishes events.

### 5.2 InMemoryBus (Current Implementation)

The current bus is an in-memory async queue.

Responsibilities:

- Accept events via publish()
- Expose events via get_event()

It acts as a lightweight routing layer between:

- Producers (agent, background tasks)
- Consumers (EventForwarder)

This keeps agent code transport-agnostic.

### 5.3 EventForwarder

The EventForwarder:

- Runs as a background task
- Consumes events from the bus
- Routes them to the SocketRegistry

Routing logic:

- If connection_id provided -> send to that connection
- Else -> broadcast to all user connections

The forwarder is the only component aware of both:

- EventBus
- SocketRegistry

## 6. Lifecycle Management

All streaming infrastructure is instantiated in FastAPI lifespan:

- SocketRegistry singleton
- EventBus singleton
- EventForwarder singleton
- Background forwarder task

Startup:

- Instantiate components
- Start forwarder task

Shutdown:

- Stop forwarder
- Cancel background tasks
- Close all active sockets

This ensures:

- No zombie tasks
- Clean teardown
- Deterministic resource management

## 7. Distributed Scaling Strategy

The current EventBus is intentionally implemented as a placeholder abstraction.

It enables future migration to:

- Redis PubSub
- Redis Streams
- Kafka
- NATS

Without changing:

- Agent logic
- WebSocketManager
- Registry logic

In a distributed setup:

- Events would be published to Redis
- Each backend instance subscribes
- Instance forwards only if user is locally connected

This design avoids rewriting core streaming logic during scaling.

## 8. Design Principles

- Single-writer per WebSocket
- Backpressure at the edge
- Stateless agent logic
- Explicit stream identifiers
- Clean separation of concerns
- Infrastructure prepared for horizontal scaling

## 9. Summary

The streaming system:

- Streams Markdown + NDJSON blocks incrementally
- Uses per-stream sequencing for ordering
- Applies backpressure per connection
- Maintains multi-tab support
- Decouples agent logic from transport via EventBus
- Is designed to scale with minimal architectural change

This architecture prioritizes clarity, correctness, and forward compatibility.
