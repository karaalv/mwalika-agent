# Mwalika: Agentic AI System for eCitizen Platform

This repository contains the core agent engine for **Mwalika**, an AI-powered interface designed to enhance Kenya’s eCitizen platform.

Mwalika enables citizens to interact with government services through a conversational, intent-driven system rather than manually navigating complex service flows.

## Context

This project forms part of a national government hackathon organised by the **National Intelligence and Research University (NIRU)**.

The wider Mwalika system spans multiple repositories:

- `mwalika-agent`: Agent logic, retrieval, orchestration, streaming
- `mwalika-ui`: Frontend interface (React)
- `mwalika-backend`: API layer and service integrations
- `mwalika-documentation`: Centralised design, specifications, and technical documentation

The documentation repository acts as the single source of truth for architecture decisions, methodology, and system design.

## Purpose of This Repository

This repository specifically focuses on:

- Retrieval-Augmented Generation (RAG) pipeline
- Government service discovery logic
- Agent orchestration and reasoning
- Event-based streaming architecture
- Integration with vector database (Qdrant)
- Structured response formatting for frontend rendering

It does **not** contain UI implementation or full backend service integrations. Those are handled in their respective repositories.

## Overview

Mwalika operates as a general support agent for the eCitizen ecosystem. It assists users by:

- Identifying relevant government services based on user intent
- Explaining which agency and ministry are responsible for a service
- Providing official links to live eCitizen service pages
- Structuring responses in a way that supports rich UI rendering (markdown, images, links, etc.)

## Key Features (v1.0.0)

### 1. Semantic Service Discovery

- Performs semantic search over the structured government services corpus.
- Redirects users to the most relevant official eCitizen service pages.
- Provides contextual detail about responsible agencies and ministries.

<!-- TODO: Add more features as they are developed -->

## Project Structure

- **`agent/`**  
  Contains the high-level agent logic, including intent handling, retrieval coordination, response structuring, and orchestration.

- **`api/`**  
  Exposes endpoints and WebSocket interfaces used by the frontend to communicate with the agent.

- **`databases/`**  
  Houses all database integration logic, including:
  - Vector search operations (Qdrant)
  - General-purpose storage and persistence (MongoDB)

- **`corpus/`**  
  Contains all processing logic required to transform the raw dataset into the structured context corpus used by the agent. This includes embedding generation and pushing indexed vectors to the vector database.

- **`data/`**  
  Stores the raw collected dataset of ministries, agencies, and services. This acts as the immutable input layer for corpus processing.

Each major directory contains its own `README.md` explaining its role and internal structure.

## Licence

This project is licensed under the **Apache License 2.0**.

Copyright © Alvin Karanja

You may use, modify, and distribute this work in accordance with the terms of the Apache 2.0 licence. See the `LICENSE` file for full details.
