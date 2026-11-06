# sub03: Observability & Synthetic Monitoring Stack

Part of the **AI_hal_rag** framework by Pankaj ([@Pnkj-01](https://github.com/Pnkj-01)).

This module provides a production-style observability and monitoring stack using **FastAPI**, **OpenTelemetry**, **Prometheus**, and **Grafana** to track hallucination metrics, detector latencies, and traffic distribution.

---

## Architecture

```text
                  ┌──────────────┐
                  │   demo.py    │ (Synthetic Traffic & Event Generator)
                  └──────┬───────┘
                         │ HTTP POST /chat
                         ▼
                  ┌──────────────┐
                  │ FastAPI App  │ (main.py)
                  │  - Detector  │
                  │  - Responses │
                  └──────┬───────┘
                         │ OpenTelemetry Metrics (/metrics)
                         ▼
                  ┌──────────────┐
                  │  Prometheus  │ (Scrapes port 8000 every 5s)
                  └──────┬───────┘
                         │ PromQL Queries
                         ▼
                  ┌──────────────┐
                  │   Grafana    │ (Dashboard port 3000)
                  └──────────────┘
```

---

## Metrics Tracked

| Metric Name | Type | Description |
| :--- | :--- | :--- |
| `llm_requests_total` | Counter | Total requests handled, segmented by model label |
| `hallucinations_detected_total` | Counter | Detected hallucination events tagged by severity and method |
| `model_usage_total` | Counter | Distribution of queries across model identifiers |
| `false_positives_total` | Counter | Manually audited false alarm flags |
| `false_negatives_total` | Counter | Manually audited missed detection flags |
| `active_sessions` | UpDownCounter / Gauge | Number of active concurrent user sessions |
| `hallucination_score` | Histogram | Continuous distribution of simulated detector scores (0.0 to 1.0) |
| `llm_response_duration_seconds` | Histogram | Total end-to-end request duration |
| `detection_latency_seconds` | Histogram | Processing time spent executing hallucination detectors |

---

## Included Components

- `main.py` — FastAPI service exposing chat endpoints and OpenTelemetry metrics.
- `demo.py` — Traffic generator simulating user queries, trigger prompts, and false positive/negative feedback.
- `docker-compose.yml` — Multi-container stack (FastAPI app, Prometheus, Grafana).
- `prometheus.yml` — Target configuration scraping `/metrics` on a 5-second interval.
- `grafana/` — Pre-provisioned Prometheus datasource and ready-to-use Grafana monitoring dashboard.

---

## Running the Stack

### 1. Start Docker Containers
```powershell
docker compose up -d
```

### 2. Verify Services

| Service | Address | Credentials / Info |
| :--- | :--- | :--- |
| **LLM Application** | [http://localhost:8000](http://localhost:8000) | FastAPI server |
| **API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive endpoint testing |
| **Prometheus Metrics** | [http://localhost:8000/metrics](http://localhost:8000/metrics) | Raw Prometheus text format |
| **Prometheus UI** | [http://localhost:9090](http://localhost:9090) | Query engine & targets |
| **Grafana Dashboard** | [http://localhost:3000](http://localhost:3000) | `admin` / `admin` |

### 3. Generate Simulated Traffic
In a separate terminal:
```powershell
pip install -r requirements.txt
python demo.py
```

### 4. Stop the Stack
```powershell
docker compose down
```
*(To clear saved Prometheus time-series volumes, add `--volumes`).*
