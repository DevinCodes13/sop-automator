import pytest
from pydantic import ValidationError

from app.ai import ParseResult


def step(n, **overrides):
    base = {
        "number": n, "action": "Do the thing", "actor": "instructor", "inputs": [],
        "needs_approval": False, "handler": "manual", "source_quote": "Do the thing.",
    }
    base.update(overrides)
    return base


def test_valid_procedure_passes():
    result = ParseResult.model_validate({"is_procedure": True, "reason": "ok", "steps": [step(1), step(2)]})
    assert len(result.steps) == 2


def test_out_of_order_steps_are_rejected():
    with pytest.raises(ValidationError):
        ParseResult.model_validate({"is_procedure": True, "reason": "", "steps": [step(1), step(3)]})


def test_procedure_with_no_steps_is_rejected():
    with pytest.raises(ValidationError):
        ParseResult.model_validate({"is_procedure": True, "reason": "", "steps": []})


def test_made_up_handler_is_rejected():
    with pytest.raises(ValidationError):
        ParseResult.model_validate({"is_procedure": True, "reason": "", "steps": [step(1, handler="delete_records")]})


def test_not_a_procedure_with_no_steps_is_fine():
    result = ParseResult.model_validate({"is_procedure": False, "reason": "Just an ad", "steps": []})
    assert result.steps == []
