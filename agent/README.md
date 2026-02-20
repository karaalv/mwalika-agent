# Mwalika Agent Core

**Version:** 1.0.0

This package contains the core logic for the Mwalika Agent. It is responsible for orchestrating user interactions, retrieving structured knowledge, and generating responses grounded in the eCitizen corpus.

The agent core integrates:

- Agent orchestration and control flow
- Prompt construction and LLM interaction
- Retrieval and entity resolution
- Response generation
- Tool routing and execution

It acts as the central coordination layer between the API layer, the structured corpus, and the LLM interface.

## Agent Context

The Mwalika Agent operates exclusively over a structured knowledge base derived from publicly available eCitizen data.

The corpus includes:

- Ministries
- Departments
- Agencies
- Services
- FAQs

Each entity is stored with structured metadata and stable identifiers, enabling deterministic retrieval and traceable response grounding.

No external data sources are currently used. The agent’s responses are constrained to the curated eCitizen corpus to preserve accuracy, traceability, and alignment with government-provided information.

## Agent Behaviour

The agent follows a retrieval-augmented generation (RAG) pattern:

1. Interpret user intent.
2. Retrieve relevant entities from the structured corpus.
3. Generate a response grounded in retrieved context.

Key behavioural characteristics:

- Context-aware and retrieval-grounded responses.
- Clear and concise explanations.
- Clarifying questions when user intent is ambiguous.
- Explicit grounding in ministries, agencies, and services where relevant.

The agent prioritises accuracy and structured reasoning over speculative or inferential responses.

## Agent Tools

The agent currently exposes two primary tools:

### 1. Corpus Search

Retrieves relevant entities and metadata from the structured knowledge base. This tool is used to resolve ministries, departments, agencies, and services related to a user query.

### 2. FAQ Search

Searches the curated FAQ dataset to provide direct answers to common user queries. This enables fast resolution of frequently asked questions without requiring full entity traversal.

These tools are invoked as part of the agent’s orchestration logic and form the basis of its retrieval layer.

## Architectural Boundaries

- The agent does not directly manage database connections.
- The agent does not scrape or mutate corpus data.
- The agent does not access external web resources.

It operates strictly over pre-validated, structured data and delegated tool interfaces.

## Future Enhancements

Planned extensions to this package include:

- Speech-to-text (STT) integration.
- Text-to-speech (TTS) integration.
- Guardrail enforcement and policy-aware response filtering.
