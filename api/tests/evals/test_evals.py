import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.eval
CASES_DIR = Path(__file__).parent
RUN = os.getenv("RUN_EVALS") == "1"


def load_cases():
    cases = []
    for path in sorted(CASES_DIR.glob("*.json")):
        for case in json.loads(path.read_text()):
            cases.append(pytest.param(case, id=case["name"]))
    return cases


@pytest.mark.skipif(not RUN, reason="set RUN_EVALS=1 to call the real Claude API")
@pytest.mark.parametrize("case", load_cases())
def test_eval(case):
    from app.ai import parse_sop

    result, _ = parse_sop(case["sop_text"])

    if "is_procedure" in case:
        assert result.is_procedure == case["is_procedure"]

    for word in case.get("forbid_words", []):
        bad = [s.action for s in result.steps if word.lower() in s.action.lower()]
        assert not bad, f"steps mention {word!r}: {bad}"

    for check in case.get("step_checks", []):
        matches = [s for s in result.steps if check["locate"].lower() in s.source_quote.lower()]
        assert matches, f"no step quotes {check['locate']!r}"
        found = matches[0]
        if "handler" in check:
            assert found.handler == check["handler"], f"step {found.number}: handler {found.handler}"
        if "needs_approval" in check:
            assert found.needs_approval == check["needs_approval"], f"step {found.number}: needs_approval {found.needs_approval}"
