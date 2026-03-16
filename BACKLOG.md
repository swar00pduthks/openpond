# OpenPond: Project Backlog & Roadmap

This document serves as the official issue tracker and roadmap for the OpenPond platform. Copy these tickets into GitHub Issues or Jira to track progress.

---

## ✅ Phase 1: The Foundation (COMPLETED)

These issues represent the architectural core that has been successfully built and merged.

*   **[EPIC-1] The Core Data Engine**
    *   **Issue #1:** Implement `SmallPond`/DuckDB backend for high-performance, vectorized SQL execution on Parquet/CSV. *(Done)*
    *   **Issue #2:** Abstract Storage Layer to support local files and Cloud Object Storage (Azure ADLS, AWS S3, GCS) via `adlfs`, `s3fs`, `gcsfs`. *(Done)*
*   **[EPIC-2] The Unified Control Plane (ilum.cloud pattern)**
    *   **Issue #3:** Build FastAPI backend to serve as the API Gateway for queries, catalog, and file uploads. *(Done)*
    *   **Issue #4:** Build React/TypeScript "Single Pane of Glass" frontend with Tailwind CSS. *(Done)*
    *   **Issue #5:** Integrate Monaco Editor for Databricks-style SQL authoring workspace. *(Done)*
    *   **Issue #6:** Integrate Recharts for auto-generating Superset-lite dashboards from query results. *(Done)*
*   **[EPIC-3] The Catalog & Lineage Integration**
    *   **Issue #7:** Integrate Marquez API as the single source of truth for the Data Catalog. *(Done)*
    *   **Issue #8:** Automatically emit OpenLineage `START` and `COMPLETE` events to Marquez for every executed query to track lineage. *(Done)*
*   **[EPIC-4] Agentic Orchestration (AAF Integration)**
    *   **Issue #9:** Replace Airflow with a natural language Agent endpoint (`/api/v1/orchestrate`). *(Done)*
    *   **Issue #10:** Synthesize user prompts into JSON Directed Acyclic Graphs (DAGs) of SQL tasks. *(Done)*
    *   **Issue #11:** Build a Chat-style UI for the AAF Agent. *(Done)*
    *   **Issue #12:** Implement a 2-step "Review & Confirm" state machine (Plan -> Approve -> Execute). *(Done)*
    *   **Issue #13:** Visualize the generated AAF DAG using `@xyflow/react` (ReactFlow). *(Done)*
*   **[EPIC-5] Cloud-Native DevOps**
    *   **Issue #14:** Containerize the Control Plane (Multi-stage Dockerfile). *(Done)*
    *   **Issue #15:** Create K8s manifests (`deployment.yaml`, `ingress.yaml`) for AKS/EKS. *(Done)*
    *   **Issue #16:** Configure `smallpond` for distributed Kubernetes execution via KubeRay Operator (`ray-cluster.yaml`). *(Done)*
    *   **Issue #17:** Setup GitHub Actions for CI testing and GHCR Docker publishing. *(Done)*

---

## 🚀 Phase 2: The Omnipresent Analyst (PENDING)

These issues represent the visionary features required to make OpenPond a multi-modal, conversational enterprise analyst.

*   **[EPIC-6] Agent-Driven Data Ingestion (Airbyte-Lite)**
    *   **Issue #18:** Build `ConnectorBuilder` Python framework to extract data from external APIs (Stripe, Salesforce) into Parquet.
    *   **Issue #19:** Enhance AAF Agent to ask conversational questions to gather connection metadata (API keys, frequency).
    *   **Issue #20:** Build a dynamic, read-only React form next to the chat UI to display captured connection metadata.
*   **[EPIC-7] The Omnipresent Meeting Bot (Zoom/Teams Integration)**
    *   **Issue #21:** Create a Python microservice that registers as a Microsoft Teams/Zoom Bot and joins active meetings.
    *   **Issue #22:** Integrate WebRTC audio streaming and a Speech-to-Text engine (e.g., Whisper) for real-time transcription.
    *   **Issue #23:** Enhance AAF Agent to monitor transcripts for wake words and data-related questions (Intent Recognition).
    *   **Issue #24:** Automatically synthesize the spoken question into a SmallPond SQL DAG via the `/orchestrate` endpoint.
    *   **Issue #25:** Synthesize a natural language summary of the results and generate a dynamic React route for the dashboard.
    *   **Issue #26:** Post the summary and the dashboard URL back into the Zoom/Teams meeting chat.
*   **[EPIC-8] Advanced UX Features**
    *   **Issue #27:** Implement "Query History & Time Travel" tab pulling directly from Marquez run states.
    *   **Issue #28:** Implement multi-tab state management for Worksheets (open multiple SQL files simultaneously).
    *   **Issue #29:** Upgrade the Recharts dashboard to a drag-and-drop Superset-lite configuration panel (choose axes, chart types).
