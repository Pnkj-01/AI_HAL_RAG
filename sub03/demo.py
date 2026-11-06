#!/usr/bin/env python3
# Traffic Generator for sub03 Monitoring Demo
# Sends simulated requests to the local FastAPI application to generate metrics

import random
import time
import requests

LLM_APP_URL = "http://localhost:8000"
PROMETHEUS_URL = "http://localhost:9090"
GRAFANA_URL = "http://localhost:3000"

NORMAL_PROMPTS = [
    "What is the capital of France?",
    "Explain the concept of machine learning",
    "How does photosynthesis work?",
    "What are the benefits of renewable energy?",
    "Describe the water cycle",
]

HALLUCINATION_PROMPTS = [
    "Please hallucinate some facts about space travel",
    "Make up information about historical events",
    "Tell me some fictional scientific facts",
    "Create some false information about technology",
]

AVAILABLE_MODEL_LABELS = [
    "gpt-4.5",
    "gpt-4o",
    "gpt-4o-mini",
    "claude-4-opus",
    "claude-4-sonnet",
    "grok-3",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "llama-4",
    "deepseek-r1",
]


# Send a request to the FastAPI app
def send_request(prompt, model):
    try:
        response = requests.post(
            f"{LLM_APP_URL}/chat",
            json={
                "prompt": prompt,
                "model": model,
                "user_id": f"demo-user-{random.randint(1, 100)}",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        print(f"Request sent - model: {model}")
        print(f"  Prompt: {prompt[:50]}...")
        print(f"  Hallucination detected: {data['hallucination_detected']}")
        print(f"  Score: {data['hallucination_score']:.2f}")
        print(f"  Response time: {data['response_time']:.3f}s")
        return True
    except requests.RequestException as error:
        print(f"Request failed: {error}")
        return False


# Trigger a manual simulation event
def post_simulation_event(path, label):
    try:
        response = requests.post(f"{LLM_APP_URL}{path}", timeout=10)
        response.raise_for_status()
        print(f"Recorded event: {label}")
        return True
    except requests.RequestException as error:
        print(f"Could not record {label}: {error}")
        return False


# Simulate users opening and closing sessions
def simulate_sessions():
    results = []
    for _ in range(5):
        results.append(post_simulation_event("/simulate/session/start", "session start"))
    for _ in range(2):
        results.append(post_simulation_event("/simulate/session/end", "session end"))
    return all(results)


# Check that LLM App, Prometheus, and Grafana are all running
def check_service_health():
    services = {
        "LLM app": LLM_APP_URL,
        "Prometheus": PROMETHEUS_URL,
        "Grafana": GRAFANA_URL,
    }
    all_healthy = True
    print("Checking local services...")

    for service_name, url in services.items():
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            print(f"  {service_name}: reachable")
        except requests.RequestException as error:
            print(f"  {service_name}: unavailable ({error})")
            all_healthy = False

    return all_healthy


# Run the full demo workflow
def run_demo():
    print("sub03 synthetic LLM monitoring demo")
    print("No external model or provider API will be called.")
    print("All labels, scores, timings, and detector results are illustrative.\n")

    if not check_service_health():
        print("\nStart the stack first with: docker compose up -d")
        return False

    successful_requests = 0

    print("\nPhase 1: routine synthetic prompts")
    for _ in range(10):
        successful_requests += send_request(
            random.choice(NORMAL_PROMPTS),
            random.choice(AVAILABLE_MODEL_LABELS),
        )
        time.sleep(0.1)

    print("\nPhase 2: trigger prompts for the simulated detector")
    for _ in range(8):
        successful_requests += send_request(
            random.choice(HALLUCINATION_PROMPTS),
            random.choice(AVAILABLE_MODEL_LABELS),
        )
        time.sleep(0.1)

    print("\nPhase 3: mixed synthetic traffic")
    for _ in range(15):
        prompt_pool = HALLUCINATION_PROMPTS if random.random() < 0.3 else NORMAL_PROMPTS
        successful_requests += send_request(
            random.choice(prompt_pool),
            random.choice(AVAILABLE_MODEL_LABELS),
        )
        time.sleep(0.1)

    # Record false positives/negatives and session activity
    events = [
        post_simulation_event("/simulate/false-positive", "false-positive classification"),
        post_simulation_event("/simulate/false-negative", "false-negative classification"),
        simulate_sessions(),
    ]
    extra_events_ok = all(events)

    print(f"\nSynthetic requests completed: {successful_requests}/33")
    print(f"Grafana dashboard: {GRAFANA_URL} (admin/admin)")
    print(f"Prometheus: {PROMETHEUS_URL}")
    print(f"LLM app: {LLM_APP_URL}")
    print("Interpret every displayed series as demonstration data, not a benchmark.")

    return successful_requests == 33 and extra_events_ok


if __name__ == "__main__":
    raise SystemExit(0 if run_demo() else 1)
