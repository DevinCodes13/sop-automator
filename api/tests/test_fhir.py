import httpx
import pytest

from app import fhir


def make(status, body=None):
    return httpx.Response(status, json=body or {}, request=httpx.Request("POST", "http://fhir.test/Patient"))


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(fhir.time, "sleep", lambda s: None)


def test_creates_a_patient(monkeypatch):
    monkeypatch.setattr(fhir.httpx, "post", lambda *a, **k: make(201, {"id": "p1"}))
    assert fhir.create_patient("run-1", "Test Client") == {"patient_id": "p1", "created": True, "attempts": 1}


def test_existing_patient_is_not_duplicated(monkeypatch):
    seen = []

    def fake_post(url, json, headers, timeout):
        seen.append(headers["If-None-Exist"])
        return make(200, {"id": "p1"})

    monkeypatch.setattr(fhir.httpx, "post", fake_post)
    result = fhir.create_patient("run-1", "Test Client")
    assert result["created"] is False
    assert seen == ["identifier=urn:sop-automator:intake|run-1"]


def test_retries_then_succeeds(monkeypatch):
    replies = iter([make(503), make(503), make(201, {"id": "p2"})])
    monkeypatch.setattr(fhir.httpx, "post", lambda *a, **k: next(replies))
    assert fhir.create_patient("run-2", "Test Client")["attempts"] == 3


def test_gives_up_after_three_tries(monkeypatch):
    monkeypatch.setattr(fhir.httpx, "post", lambda *a, **k: make(503))
    with pytest.raises(fhir.StepError):
        fhir.create_patient("run-3", "Test Client")


def test_bad_request_is_not_retried(monkeypatch):
    calls = []

    def fake_post(*a, **k):
        calls.append(1)
        return make(400)

    monkeypatch.setattr(fhir.httpx, "post", fake_post)
    with pytest.raises(fhir.StepError):
        fhir.create_patient("run-4", "Test Client")
    assert len(calls) == 1


def test_pretend_failures_then_success(monkeypatch):
    monkeypatch.setattr(fhir.httpx, "post", lambda *a, **k: make(201, {"id": "p5"}))
    assert fhir.create_patient("run-5", "Test Client", simulate_failures=2)["attempts"] == 3
