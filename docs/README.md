# Agent Documentation Contracts

This directory contains technical documentation and system contracts
for the `mwalika-agent` repository.

It defines the application-level architecture assumptions required for
the agent to function correctly, including:

- Storage architecture (MongoDB and Qdrant)
- Vector collection configuration and schema
- API contracts
- WebSocket event schemas
- Internal data structures and invariants

## Purpose

The purpose of this documentation is to serve as a **technical
reference and contract** for developers working on the agent.

It ensures:

- Consistency in data modelling and storage interactions
- Stability of API and WebSocket interfaces
- Clear definition of retrieval and indexing assumptions
- Alignment between implementation and architecture

Any changes that affect storage structure, collection schemas, payload
contracts, or event formats must be reflected in this documentation.

## Scope

This documentation is strictly technical.

It may include:

- Implementation details
- Design decisions
- Architectural trade-offs
- Schema definitions
- Versioning rules

It does **not** include user-facing explanations, product justifications,
or high-level proposal material. Those are maintained in the
`mwalika-documentation` repository.

This directory exists to define the system contract between the agent
code, its storage layer, and its external interfaces.
