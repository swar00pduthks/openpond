# OpenPond

The **Intelligent Data Operating System**.

OpenPond orchestrates, executes, and tracks your data pipelines from ingestion to insight with zero infrastructure overhead. By combining Agentic Orchestration with high-performance vector-based execution and native lineage tracking, OpenPond provides a unified, single-pane-of-glass experience for modern data teams.

---

## 🌟 Core Pillars

1. **Agentic Orchestration (AAF):** Stop writing brittle DAG scripts. Simply describe your pipeline in natural language. The OpenPond Agent synthesizes, visualizes, and executes complex data workflows instantly.
2. **Unified Data Catalog:** Native discovery and lineage tracking are built into every action. OpenPond ensures absolute transparency regarding where your data comes from and how it was transformed.
3. **High-Performance Compute:** Blazing-fast analytical execution powered by vector-based query engines, seamlessly scaling from local development to distributed cloud clusters.
4. **Interactive Workspaces:** A premium SQL authoring environment and auto-generating dashboards, providing instant visual feedback on your data.

---

## 🏛️ Architecture

OpenPond relies on a decoupled, cloud-native architecture:
*   **Control Plane (`backend/`):** A stateless Python API gateway that handles agent synthesis, catalog tracking, and compute delegation.
*   **Single Pane of Glass (`frontend/`):** A modern React application featuring interactive DAG visualizations, intelligent chat, and a robust data explorer.
*   **Compute Plane:** Scalable execution engine supporting distributed cloud deployments (e.g., via KubeRay).
*   **Storage Abstraction:** Native support for Azure ADLS, AWS S3, and GCS object stores.

---

## 🚀 Quick Start (Local Docker Development)

```bash
# Build the unified container
docker build -t openpond-control-plane .

# Run the platform locally
docker run -p 8000:8000 openpond-control-plane

# Access the Single Pane of Glass
# http://localhost:8000
```

## 📚 Documentation
Please refer to the `/docs` directory for advanced topics, including Kubernetes deployments and Cloud Storage configuration.
