import os

from prometheus_client import Counter, Histogram

from .config import CLAUDE_MODEL

HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
HTTP_LATENCY = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "path"])
RUNS_FINISHED = Counter("runs_finished_total", "Runs that reached a final state", ["status"])
STEPS_TOTAL = Counter("run_steps_total", "Workflow steps executed", ["handler", "outcome"])
LLM_REQUESTS = Counter("llm_requests_total", "Claude calls", ["model", "prompt_version", "outcome"])
LLM_TOKENS = Counter("llm_tokens_total", "Claude tokens", ["model", "kind"])
LLM_LATENCY = Histogram("llm_latency_seconds", "Claude call duration", ["model"], buckets=(0.5, 1, 2, 4, 8, 15, 30, 60))
LLM_COST = Counter("llm_cost_usd_total", "Estimated Claude spend in USD", ["model"])
FHIR_REQUESTS = Counter("fhir_requests_total", "FHIR patient writes", ["outcome"])
FHIR_RETRIES = Counter("fhir_retries_total", "FHIR retry attempts")

INPUT_PRICE = float(os.getenv("LLM_INPUT_USD_PER_MTOK", "0"))
OUTPUT_PRICE = float(os.getenv("LLM_OUTPUT_USD_PER_MTOK", "0"))

# Start known series at zero so the first real event shows up on charts
for s in ("completed", "failed", "cancelled"):
    RUNS_FINISHED.labels(s)
for kind in ("input", "output"):
    LLM_TOKENS.labels(CLAUDE_MODEL, kind)
LLM_COST.labels(CLAUDE_MODEL)
for outcome in ("ok", "failed"):
    FHIR_REQUESTS.labels(outcome)


def record_llm_usage(model: str, input_tokens: int, output_tokens: int, latency_s: float) -> float:
    LLM_TOKENS.labels(model, "input").inc(input_tokens)
    LLM_TOKENS.labels(model, "output").inc(output_tokens)
    LLM_LATENCY.labels(model).observe(latency_s)
    cost = (input_tokens * INPUT_PRICE + output_tokens * OUTPUT_PRICE) / 1_000_000
    LLM_COST.labels(model).inc(cost)
    return round(cost, 6)
