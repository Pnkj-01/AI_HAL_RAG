# sub01: Grounded Retrieval-Augmented Generation (RAG)

Part of the **AI_hal_rag** framework by Pankaj ([@Pnkj-01](https://github.com/Pnkj-01)).

This module implements a local Retrieval-Augmented Generation (RAG) pipeline designed to eliminate LLM hallucinations by forcing models to answer strictly based on ingested knowledge documents.

---

## How It Works

```text
[Input Documents: PDF, TXT, MD]
           │
           ▼
   [DocumentIngestor]
     ├── MD5 Hash Checking (Skips unchanged files)
     ├── Text Chunking (size=500, overlap=50)
     └── OpenAI Embedding Generator (text-embedding-3-small)
           │
           ▼
    [ChromaDB Vector Store]
           │
           ▼  (Top-3 Similarity Search)
    [RAGQueryEngine]
     ├── Strict Grounding Prompt Template
     └── Greedy Deterministic LLM (temperature=0)
           │
           ▼
[Verified Answer with Exact Source Page Citations]
```

---

## Key Features

- **Multi-Format Ingestion**: Supports `.pdf` (via `pypdf`), `.txt`, and `.md` files.
- **Smart Hash Caching**: Generates an MD5 fingerprint for every document stored in `chroma_db/ingested_files.json`. Skips already-ingested files to avoid redundant embedding costs.
- **Dynamic Chunk Purging**: If a source document changes on disk, its previous chunks are automatically purged from ChromaDB before re-indexing.
- **Anti-Hallucination Prompt Template**: Explicitly instructs the model to reply *"I don't know"* if the provided context lacks the factual answer.

---

## Directory Layout

- `data/` — Contains source knowledge files (`DataMind_FAQ_EN.pdf`, `additional_info.txt`).
- `src/ingest.py` — File loading, recursive splitting, embedding creation, and ChromaDB persistence.
- `src/query.py` — Vector similarity search and context-grounded prompt execution.
- `src/rag.py` — Unified facade API (`RAGSystem`) combining ingestion and querying.
- `test_rag.py` — Executable end-to-end demonstration script.

---

## Setup & Execution

### 1. Environment Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy the template and add your OpenAI API key:
```powershell
Copy-Item .env.example .env
```
Inside `.env`:
```dotenv
OPENAI_API_KEY=your-api-key-here
```

### 3. Run Ingestion & Queries
To run the full end-to-end pipeline:
```powershell
python test_rag.py
```

To ingest documents independently:
```powershell
python src/ingest.py
```

To run interactive queries:
```powershell
python src/query.py
```
