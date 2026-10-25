import json
import sys

r = json.load(sys.stdin)
if not isinstance(r, dict) or "events" not in r:
    print(json.dumps(r, indent=2))
    sys.exit()
print(f"Run {r['id']}  status={r['status']}  next_step={r['current_step']}")
print(f"public_id={r['public_id']}")
print(f"client={r['input']['client_name']}  context={r['context']}")
for e in r["events"]:
    step = f"step {e['step']}" if e["step"] else ""
    detail = ", ".join(f"{k}={v}" for k, v in e["detail"].items())
    print(f"  {step:7} {e['event']:17} {detail}")
