import json
import logging
import time

import httpx

from .config import FHIR_BASE_URL
from .metrics import FHIR_REQUESTS, FHIR_RETRIES

log = logging.getLogger("sop.fhir")
IDENTIFIER_SYSTEM = "urn:sop-automator:intake"
MAX_ATTEMPTS = 3


class StepError(Exception):
    pass


def _patient_id(resp: httpx.Response) -> str | None:
    try:
        pid = resp.json().get("id")
        if pid:
            return pid
    except ValueError:
        pass
    location = resp.headers.get("Location") or resp.headers.get("Content-Location") or ""
    parts = location.split("/")
    if "Patient" in parts and parts.index("Patient") + 1 < len(parts):
        return parts[parts.index("Patient") + 1]
    return None


def _fail(message: str):
    FHIR_REQUESTS.labels("failed").inc()
    raise StepError(message)


def create_patient(public_id: str, client_name: str, simulate_failures: int = 0) -> dict:
    body = {
        "resourceType": "Patient",
        "identifier": [{"system": IDENTIFIER_SYSTEM, "value": public_id}],
        "name": [{"text": client_name}],
        "meta": {"tag": [{"system": "urn:sop-automator", "code": "demo"}]},
    }
    headers = {
        "Accept": "application/fhir+json",
        "Prefer": "return=representation",
        "If-None-Exist": f"identifier={IDENTIFIER_SYSTEM}|{public_id}",
    }
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            if attempt <= simulate_failures:
                raise httpx.ConnectError("Simulated outage")
            resp = httpx.post(f"{FHIR_BASE_URL}/Patient", json=body, headers=headers, timeout=20)
            resp.raise_for_status()
            pid = _patient_id(resp)
            if not pid:
                _fail("FHIR server didn't return a patient id")
            FHIR_REQUESTS.labels("ok").inc()
            return {"patient_id": pid, "created": resp.status_code == 201, "attempts": attempt}
        except httpx.HTTPStatusError as e:
            if e.response.status_code < 500:
                _fail(f"FHIR rejected the request ({e.response.status_code})")
            last_error = e
        except httpx.TransportError as e:
            last_error = e
        FHIR_RETRIES.inc()
        log.warning(json.dumps({"event": "fhir_retry", "attempt": attempt, "error": str(last_error)}))
        if attempt < MAX_ATTEMPTS:
            time.sleep(2 ** (attempt - 1))
    _fail(f"FHIR failed after {MAX_ATTEMPTS} tries: {last_error}")
