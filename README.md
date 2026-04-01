# AI Long-Term Memory (ALTM)

** Agentic Memory System for the Next Generation of AI Agents.**

ALTM is a high-performance, asynchronous memory layer designed to give AI agents a persistent, hierarchical, and self-consolidating long-term memory. Unlike simple vector stores, ALTM implements **Agentic Routing (PageIndex)**, **Dynamic Importance Decay**, and **Automated Memory Merging** to ensure your agents remember what matters and forget what doesn't.

---

## 🏛 Exceptional Architecture

The system is built for extreme reliability and low-latency performance:

- **Fully Asynchronous Event Loop**: Powered by FastAPI and Motor (Async MongoDB), the architecture ensures zero blocking of the event loop. Every database operation and API call is non-blocking, allowing the system to scale to thousands of concurrent requests.
- **Resource Efficiency (OOM-Safe)**: All batch updates (importance decay, pruning) utilize **asynchronous cursor iteration**. This prevents memory exhaustion (OOM) even when managing millions of memory nodes for a single user.
- **Singleton Pattern Resource Management**: Implements thread-safe singleton patterns for HTTPX clients and MongoDB connections, preventing socket exhaustion and ensuring high-performance TCP/TLS reuse.
- **Lifespan-Managed Lifecycle**: Utilizing FastAPI lifespan handlers for graceful startup/shutdown, ensuring all database connections are cleanly initialized and closed.

## 🛡 Security & Resilience

ALTM is "battle-hardened" against common production failures:

- **Thread-Safe Embedding Cache**: A lock-guarded LRU cache prevents race conditions during embedding generation.
- **Input Sanitization & Validation**: Strict Pydantic models with character limits (OOM protection) and automated MongoDB key sanitization to prevent injection attacks during hierarchical indexing.
- **Deterministic Context Retrieval**: Advanced sorting with `_id` tie-breakers ensures conversation history is never jumbled, even during millisecond-parallel message ingestion.
- **Atlas-Ready Connectivity**: Pre-configured for MongoDB Atlas with `dnspython` support and optimized Vector Search index definitions.

## 🚀 Special Features

### 1. PageIndex (Agentic Routing)
Instead of a flat search, ALTM uses an LLM-driven "Archivist" to categorize memories into a hierarchical map (Categories/Topics). The **Agentic Router** then narrows down search spaces, significantly improving retrieval accuracy and reducing noise.

### 2. Automated Memory Consolidation
The system detects "near-duplicate" memories and utilizes an LLM to merge them into a single, cohesive node. This prevents "context stuffing" and keeps the agent's memory lean and high-signal.

### 3. Dynamic Importance & Decay
Memories aren't static. ALTM implements a **Reinforcement/Decay** system:
- **Reinforce**: Similarity to new content boosts a memory's importance.
- **Decay**: Irrelevant memories fade over time.
- **Pruning**: Low-importance memories are automatically pruned when a user hits the `MAX_DEPTH` threshold.

---

## 🛠 Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/ai-long-term-memory.git
cd ai-long-term-memory

# Install production dependencies
pip install -r requirements.txt

# Configure your environment
cp sample.env .env
# Add your MONGODB_URI and OPENROUTER_API_KEY
```

## 🤝 Call for Open-Source Contributors

We are building the standard for agentic memory, and we want your help. ALTM is currently seeking contributors to help expand in the following areas:

- **Multi-Modal Support**: Extending memory nodes to store and retrieve image/audio embeddings.
- **Graph-Based Retrieval**: Integrating Knowledge Graph links between memory nodes.
- **Local LLM Providers**: Adding first-class support for Ollama and vLLM for fully local deployments.
- **Client SDKs**: Building TypeScript/Python SDKs for easy integration.

**Ready to contribute?**
1. Check the **Issues** tab for `good-first-issue` tags.
2. Fork the repo and create a feature branch.
3. Submit a PR. We value clean code, async-first patterns, and comprehensive tests.

---

**License**: MIT  
**Author**: [Your Name/Org]  
**Status**: Production-Ready / Bug-Hunted 🛡️
