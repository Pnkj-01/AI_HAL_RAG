# Synthetic LLM Monitoring Application
# FastAPI server with OpenTelemetry metrics for Prometheus and Grafana

import logging
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import uvicorn
from fastapi import FastAPI, Response
from pydantic import BaseModel, Field

# OpenTelemetry & Prometheus imports
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SIMULATION_NOTICE = "Educational synthetic data only. No external model was queried, and the values are not model benchmarks."

# -------------------------------------------------------------
# 1. Setup OpenTelemetry & Prometheus Reader
# -------------------------------------------------------------
resource = Resource.create({SERVICE_NAME: "sub03-synthetic-monitoring"})
prometheus_reader = PrometheusMetricReader()
meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[prometheus_reader],
)
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter("sub03.synthetic-monitoring", "1.0.0")

# -------------------------------------------------------------
# 2. Define the Metrics We Track
# -------------------------------------------------------------
hallucination_counter = meter.create_counter(
    "hallucinations_detected",
    description="Simulated application-side detector flags",
)
llm_requests_total = meter.create_counter(
    "llm_requests",
    description="Synthetic requests handled by the local demonstration",
)
model_usage = meter.create_counter(
    "model_usage",
    description="Synthetic traffic grouped by illustrative model label",
)
false_positive_counter = meter.create_counter(
    "false_positives",
    description="Manually simulated false-positive events",
)
false_negative_counter = meter.create_counter(
    "false_negatives",
    description="Manually simulated false-negative events",
)
active_sessions_gauge = meter.create_up_down_counter(
    "active_sessions",
    description="Simulated active sessions",
)
llm_response_time = meter.create_histogram(
    "llm_response_duration_seconds",
    unit="s",
    description="Elapsed time for a locally simulated response",
)
hallucination_score = meter.create_histogram(
    "hallucination_score",
    description="Synthetic score produced by the application-side detector",
)
detection_latency = meter.create_histogram(
    "detection_latency_seconds",
    unit="s",
    description="Elapsed time for the simulated detector function",
)

# -------------------------------------------------------------
# 3. FastAPI App Initialization & Request/Response Models
# -------------------------------------------------------------
app = FastAPI(
    title="sub03 Synthetic LLM Monitoring Demo",
    version="1.0.0",
    description=SIMULATION_NOTICE,
)


class LLMRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    model: str = Field(
        default="gpt-4o",
        description="Illustrative series label only; no provider is contacted",
    )
    user_id: Optional[str] = None
    context: Optional[str] = None


class LLMResponse(BaseModel):
    response: str
    model: str
    response_time: float
    hallucination_detected: bool
    hallucination_score: float
    timestamp: str
    simulation_notice: str


# -------------------------------------------------------------
# 4. Simulated Hallucination Detector
# -------------------------------------------------------------
class HallucinationDetector:
    detection_methods = (
        "simulated_semantic_similarity",
        "simulated_factual_consistency",
        "simulated_confidence_score",
    )
    trigger_phrases = (
        "hallucinate",
        "make up",
        "fictional",
        "false information",
    )

    def detect_hallucination(self, prompt, response, model):
        start_time = time.perf_counter()

        method = random.choice(self.detection_methods)
        is_trigger_prompt = any(phrase in prompt.lower() for phrase in self.trigger_phrases)

        # Higher hallucination score if prompt asked to hallucinate
        if is_trigger_prompt:
            score = random.uniform(0.65, 0.95)
        else:
            score = random.uniform(0.05, 0.45)

        detector_runtime = time.perf_counter() - start_time
        detected = score > 0.5

        return detected, score, method, detector_runtime


detector = HallucinationDetector()


# Generate a fake response locally
def simulate_llm_response(prompt, model):
    if any(phrase in prompt.lower() for phrase in detector.trigger_phrases):
        samples = [
            "[Synthetic example] The Eiffel Tower was built on the Moon.",
            "[Synthetic example] Python was invented as a spreadsheet formula.",
            "[Synthetic example] Ocean tides are controlled by traffic lights.",
        ]
    else:
        samples = [
            "[Synthetic example] This local response represents a routine answer.",
            "[Synthetic example] The application generated this text without an AI API.",
            "[Synthetic example] This response exists only to create monitoring traffic.",
        ]

    chosen = random.choice(samples)
    return f"{chosen} Model label: {model}."


# -------------------------------------------------------------
# 5. API Endpoints
# -------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "message": "sub03 synthetic LLM monitoring application",
        "status": "running",
        "simulation_notice": SIMULATION_NOTICE,
    }


# Prometheus scrapes this endpoint
@app.get("/metrics")
async def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Main chat endpoint
@app.post("/chat", response_model=LLMResponse)
async def chat_completion(request: LLMRequest):
    start_time = time.perf_counter()
    session_id = request.user_id or str(uuid.uuid4())
    attributes = {"model": request.model, "traffic": "synthetic"}

    # Count request
    llm_requests_total.add(1, attributes)
    model_usage.add(1, attributes)

    # Small delay to simulate processing
    time.sleep(random.uniform(0.05, 0.20))

    # Generate response & run detector
    response_text = simulate_llm_response(request.prompt, request.model)
    detected, score, method, detector_runtime = detector.detect_hallucination(
        request.prompt,
        response_text,
        request.model,
    )
    total_time = time.perf_counter() - start_time

    # Record metrics
    llm_response_time.record(total_time, attributes)
    hallucination_score.record(score, {**attributes, "method": method})
    detection_latency.record(detector_runtime, {"method": method, "traffic": "synthetic"})

    if detected:
        severity = "high" if score > 0.8 else "medium"
        hallucination_counter.add(1, {**attributes, "severity": severity, "method": method})

    logger.info(
        f"Synthetic request - label={request.model} session={session_id} flag={detected} score={score:.2f}"
    )

    return LLMResponse(
        response=response_text,
        model=request.model,
        response_time=total_time,
        hallucination_detected=detected,
        hallucination_score=score,
        timestamp=datetime.now(timezone.utc).isoformat(),
        simulation_notice=SIMULATION_NOTICE,
    )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/stats")
async def get_stats():
    return {
        "metrics": "Available from /metrics and Prometheus",
        "detection_methods": detector.detection_methods,
        "simulation_notice": SIMULATION_NOTICE,
    }


# Simulation endpoints for manual events
@app.post("/simulate/false-positive")
async def simulate_false_positive():
    false_positive_counter.add(1, {"traffic": "synthetic"})
    return {"message": "Synthetic false-positive event recorded"}


@app.post("/simulate/false-negative")
async def simulate_false_negative():
    false_negative_counter.add(1, {"traffic": "synthetic"})
    return {"message": "Synthetic false-negative event recorded"}


@app.post("/simulate/session/start")
async def start_session():
    active_sessions_gauge.add(1, {"traffic": "synthetic"})
    return {"message": "Synthetic session started"}


@app.post("/simulate/session/end")
async def end_session():
    active_sessions_gauge.add(-1, {"traffic": "synthetic"})
    return {"message": "Synthetic session ended"}


# Run app directly with python main.py
if __name__ == "__main__":
    logger.info("Starting synthetic monitoring app on http://localhost:8000")
    logger.info("Metrics available at http://localhost:8000/metrics")
    uvicorn.run(app, host="0.0.0.0", port=8000)
