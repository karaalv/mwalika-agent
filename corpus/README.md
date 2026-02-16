# Mwalika Agent Corpus

> This document describes version 1.0 of the Mwalika Agent Corpus and retrieval algorithm. If the corpus structure or retrieval logic changes in the future, this document will be updated and versioned accordingly.

This directory contains the logic required to transform raw eCitizen data into a structured, indexed knowledge base used by the Mwalika Agent.

It is responsible for:

- Processing raw government service data
- Generating structured embeddings
- Creating vector store artefacts
- Pushing embeddings to Qdrant
- Persisting structured entities and metadata to MongoDB

Embeddings are stored **only in Qdrant**. MongoDB does not store embedding vectors.

## Corpus Scope and Justification

The goal of the corpus is to enable the agent to resolve user requests related to Kenyan government services.

Broadly, this involves two forms of retrieval:

1. **Contextual Retrieval**  
   Retrieving information about ministries, departments, agencies, and services in order to provide structured detail.

2. **Intent Resolution**  
   Mapping user queries (e.g. “How do I apply for a business permit?”) to the correct service entity and associated metadata.

The corpus therefore acts as a structured, semantically indexed knowledge base that enables the agent to retrieve relevant entities and reason over them.

## Corpus Size and Storage Estimate

The corpus currently contains approximately:

- ~6000 entities (ministries, departments, agencies, services)

The raw structured dataset (without embeddings) is approximately:

- ~2 MB

Embeddings are generated using `text-embedding-3-large` (3072 dimensions).

Each embedding:

- 3072 dimensions
- Stored as float32 (4 bytes per value)
- 3072 × 4 = **12,288 bytes (~12 KB per vector)**

Total embedding storage:

- 6000 × 12 KB ≈ **72 MB**

With HNSW indexing overhead in Qdrant, total vector storage is expected to be approximately:

- **90–120 MB**

This comfortably fits within the 1GB Qdrant Cloud free tier.

Embeddings are not stored in MongoDB.

## A Note on FAQs

The eCitizen FAQ section contains:

- ~15 entries
- Answers averaging ~15 words

Given the small size and high-level nature of this content:

- FAQs are not included in the vector store.
- FAQs are passed to the agent deterministically via a tool during reasoning.
- This avoids unnecessary indexing complexity.

If FAQs expand significantly in the future, they may be indexed in a separate collection.

For v1.0, this simpler approach is sufficient and architecturally cleaner.

## Structured Embedding Model

The eCitizen ecosystem follows a hierarchical structure:

Ministry → Department → Agency → Service

To leverage this hierarchy, embeddings are created using a structured concatenation approach.

Each entity is converted into structured text before embedding.

Example for a service:

``` txt
Ministry: [Ministry Name]
Ministry Description: [Summarised Description]
Department: [Department Name]
Agency: [Agency Name]
Agency Description: [Summarised Description]
Service: [Service Name]
```

Notes:

- Descriptions are summarised to a maximum of 150 tokens before embedding.
- Summaries are generated once during corpus processing and stored in MongoDB.
- Summaries are not stored in the vector store separately.
- The same embedding model is used for both corpus items and query embeddings.

Embedding model:

- `text-embedding-3-large`
- 3072 dimensions
- Outputs normalised vectors

Cosine similarity is used for retrieval. Since embeddings are normalised, cosine similarity reduces to dot product in practice, but Cosine is explicitly configured for clarity and correctness.

## Vector Store Schema

Each corpus item is stored in Qdrant as:

```typescript
interface CorpusItem {
    id: string;
    vector: number[];
    payload: {
        type: 'ministry' | 'department' | 'agency' | 'service';
        schemaVersion: string;
        entityId: string;
    };
}
```

The vector store contains only retrieval-relevant fields.

Full structured entity data is stored in MongoDB.

This separation prevents:

- Payload bloat
- Duplication across entities
- Tight coupling between retrieval and application logic

## Retrieval Algorithm (v1.0)

### 1. Request Synthesis

The agent synthesises the user query into a concise retrieval query.

Example:

User:  
“How do I apply for a business permit?”

Synthesised query:  
“Apply for business permit”

The synthesised query is embedded using the same embedding model as the corpus.

If the user query is not in English:

- It is translated to English before embedding.
- Final response is translated back if necessary.

### 2. Type Filtering

Based on intent, the agent selects relevant entity types:

- Service queries → `type = service`
- Agency queries → `type = agency`
- Department queries → `type = department`
- Ministry queries → `type = ministry`

Filtering reduces retrieval noise and improves precision.

### 3. Vector Similarity Search

The agent performs cosine similarity search in Qdrant.

Initial retrieval:

- Top 3 results

Similarity expansion threshold:

- If all top 3 scores < φ → expand to top 5

Acceptance threshold:

- If best result < γ → ask user for clarification

Threshold values (φ and γ) are determined through evaluation and tuning.

### 4. Metadata Enhancement

After retrieval:

- The entity ID is used to fetch full structured data from MongoDB.
- Related entities (e.g. parent ministry) are joined at the application layer.

This design ensures:

- Vector store remains lean and retrieval-focused.
- Application logic handles entity relationships.
- No duplication of hierarchical data in Qdrant.

### 5. Response Generation

The agent generates responses using:

- Retrieved entity embeddings
- Full structured entity data from MongoDB
- Joined metadata from related entities

This provides:

- Deterministic service links
- Responsible ministry/agency information
- Structured contextual responses

## Conclusion

Version 1.0 implements a structured RAG system optimised for:

- Government service discovery
- Deterministic entity resolution
- Efficient vector search
- Clean separation of retrieval and application logic

The system is intentionally simple, scalable within current constraints, and designed for iterative refinement based on real retrieval performance.
