# AI_hal_rag

**Developer & Maintainer:** Pankaj ([@Pnkj-01](https://github.com/Pnkj-01))  
**Repository:** [https://github.com/Pnkj-01/AI_hal_rag](https://github.com/Pnkj-01/AI_hal_rag)

An end-to-end framework and toolkit for detecting, preventing, and monitoring Large Language Model (LLM) hallucinations across production AI systems.

---

## Overview

Large Language Models frequently generate factually inaccurate claims with high confidence. **AI_hal_rag** provides a complete three-tier defense system to ensure AI outputs remain verifiable, grounded, and observable:

1. **Grounded Retrieval (Prevention)**: Enforces document grounding via vector similarity search, strict system prompting, and page-level source citations.
2. **Guardrails & Fallback Routing (Detection & Verification)**: Intercepts risky prompts, screens for sensitive data, flags ungrounded assertions, and automatically routes failed queries to fallback models or safe default handlers.
3. **Synthetic Telemetry & Observability (Monitoring)**: Instruments LLM applications with OpenTelemetry to track hallucination scores, response times, and failure rates in real-time using Prometheus and Grafana.

---

## Project Structure

```text
AI_hal_rag/
├── sub01/           # Grounded RAG Pipeline (PDF/TXT Ingestion & ChromaDB Retrieval)
│   ├── data/        # Source documents (PDFs, knowledge files)
│   ├── src/         # Ingestor, Query Engine, and RAG facade
│   └── test_rag.py  # End-to-end retrieval and answering demo
│
├── sub02/           # Safety Guardrails, Output Verification & Fallback Logic
│   ├── data/        # Context grounding documents
│   ├── safety-guardrails.js # Input sanitization, model fallbacks, output verification
│   └── package.json # Node.js project configuration
│
├── sub03/           # Observability & Monitoring Stack
│   ├── main.py      # FastAPI application instrumented with OpenTelemetry
│   ├── demo.py      # Traffic generator simulating queries and detector events
│   ├── docker-compose.yml # Prometheus & Grafana services
│   └── grafana/     # Provisioned real-time hallucination monitoring dashboard
│
└── LICENSE          # MIT License
```

---

## Modules

### [sub01: Retrieval-Augmented Generation (RAG)](./sub01/README.md)
* **Goal**: Ground answers strictly in local source documents so the model cannot invent facts.
* **Tech**: Python 3.11+, LangChain, ChromaDB, OpenAI Embeddings (`text-embedding-3-small`).
* **Features**:
  * Multi-format document loader (`.pdf`, `.txt`, `.md`).
  * MD5 change detection caching (`ingested_files.json`) to prevent redundant embedding recalculation.
  * Deterministic greedy decoding (`temperature=0`) with explicit page citation attribution.

### [sub02: Guardrails & Adaptive Fallbacks](./sub02/README.md)
* **Goal**: Validate both user inputs and model outputs before they reach end users.
* **Tech**: Node.js (ES Modules), OpenAI Responses API (`gpt-5.6-terra`, `gpt-5.6-luna`).
* **Features**:
  * Input sanitization for sensitive patterns (API keys, credentials, PII).
  * Output verification detecting hallucinated citations, missing uncertainty markers, or unauthorized legal/medical advice.
  * Hierarchical fallback routing: Primary Model $\rightarrow$ Secondary Model $\rightarrow$ Human Review Queue & Safe Default.

### [sub03: Observability & Telemetry](./sub03/README.md)
* **Goal**: Continuously monitor hallucination scores, detector latencies, and request anomalies in production.
* **Tech**: FastAPI, OpenTelemetry Metrics SDK, Prometheus, Grafana, Docker.
* **Features**:
  * Real-time metrics exported at `/metrics` (Prometheus exposition format).
  * Tracks hallucination rates, response duration histograms, detector latency, and active sessions.
  * Pre-configured Grafana dashboard ready out-of-the-box.

---

## Quick Start

### 1. Run the RAG Pipeline (`sub01`)
```powershell
cd sub01
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # Add your OPENAI_API_KEY
python test_rag.py
```

### 2. Run Safety Guardrails (`sub02`)
```powershell
cd sub02
npm install
npm test                      # Runs offline simulated test (zero API cost)
npm run start:live            # Runs with live OpenAI model
```

### 3. Run the Monitoring Stack (`sub03`)
```powershell
cd sub03
docker compose up -d          # Starts FastAPI app, Prometheus, and Grafana
pip install -r requirements.txt
python demo.py                # Generates synthetic traffic
```
* **Grafana Dashboard**: [http://localhost:3000](http://localhost:3000) (User: `admin` / Password: `admin`)
* **Prometheus Targets**: [http://localhost:9090](http://localhost:9090)
* **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## License

This project is licensed under the [MIT License](./LICENSE).  
Copyright (c) 2026 Pankaj.
