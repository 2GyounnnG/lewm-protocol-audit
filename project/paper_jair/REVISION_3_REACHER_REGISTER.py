"""Seal the Reacher correction registration after a passing runtime gate.

The command is intentionally fail-closed: a static/local ``NOT_RUN`` gate or
any failed gate cannot create a registration receipt.  It only writes a small
JSON receipt; it does not launch a job and does not edit the preregistration.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tech-gate", type=Path, required=True)
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--patched-worker", type=Path, nargs="+", required=True)
    ap.add_argument("--patch", type=Path, required=True)
    ap.add_argument("--environment-lock", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refuse overwrite existing registration: {args.output}")
    gate = json.loads(args.tech_gate.read_text())
    if gate.get("status") != "PASS":
        raise SystemExit("TECH runtime gate is not PASS; registration is not written")
    paths = [args.baseline, args.patch, args.environment_lock, *args.patched_worker]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(missing)
    receipt = {
        "status": "SEALED_BEFORE_REVISION3_REACHER_FORMAL_RESULTS",
        "registration_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": "Correct dm_control qpos_match post-success reset semantics before Reacher rerun",
        "baseline_and_patch": {str(p): sha(p) for p in paths},
        "tech_gate": {"path": str(args.tech_gate), "sha256": sha(args.tech_gate), "status": gate["status"]},
        "scope": {
            "task": "Reacher",
            "cohort": "D1 V2 HELDOUT",
            "cases": 100,
            "streams": "ABC",
            "methods": ["LeWM h1", "LeWM h3", "Fast-LeWM", "AP", "AD-WM three training seeds"],
            "budget_raw_steps": 50,
        },
        "definitions_unchanged": [
            "qpos threshold and original predicate",
            "case, checkpoint, stream and retrieval-bank identities",
            "V2 success labels and paired bootstrap estimands",
        ],
        "old_results": "Retained as an identified implementation-error measurement; excluded from Reacher conclusions after corrected results exist.",
        "formal_results_seen_at_registration": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

