"""Apply the Reacher non-terminating patch to a frozen D1 worker copy.

Usage on the future GPU instance (after copying this directory):

    python REVISION_3_REACHER_WORKER_PATCH.py \
      --source /workspace/d1/step4/resume_01/code/official_formal_v2.py \
      --output /workspace/d1/step4/revision3/code/official_formal_v3_reacher.py

The source is never modified.  The patch is deliberately textual and checks
the expected anchors and base SHA before writing a new worker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def patch(source: Path, output: Path) -> dict:
    text = source.read_text()
    base_sha = sha256(source)
    anchors = [
        "task=case['task'];sc=scaler(task);transform=image_transform();current=None",
        "world.set_policy(Observed())",
        "result=native_step(value,*args,**kw);actions.append(ar(value[0]));successes.append(bool(result[2][0]))",
    ]
    missing = [a for a in anchors if a not in text]
    if missing:
        raise RuntimeError(f"official_formal_v2 anchors missing: {missing}")
    policy_anchor = "world.set_policy(Observed())\n  if variant=='angle':"
    if policy_anchor not in text:
        raise RuntimeError("world.set_policy insertion anchor missing")
    text = text.replace(
        "task=case['task'];sc=scaler(task);transform=image_transform();current=None",
        "task=case['task'];sc=scaler(task);transform=image_transform();current=None\n r3_tracker=None",
        1,
    )
    text = text.replace(
        policy_anchor,
        "world.set_policy(Observed())\n  if task=='reacher':\n   from REVISION_3_REACHER_PATCH import install_nonterminating_reacher\n   r3_tracker=install_nonterminating_reacher(world.envs.envs[0].unwrapped)\n  if variant=='angle':",
        1,
    )
    text = text.replace(
        "result=native_step(value,*args,**kw);actions.append(ar(value[0]));successes.append(bool(result[2][0]))",
        "result=native_step(value,*args,**kw);actions.append(ar(value[0]))\n   successes.append(r3_tracker.consume_step() if r3_tracker is not None else bool(result[2][0]))",
        1,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text)
    return {
        "base_source": str(source),
        "base_sha256": base_sha,
        "patched_worker": str(output),
        "patched_sha256": sha256(output),
        "patch_module": "REVISION_3_REACHER_PATCH.py",
        "anchors_checked": len(anchors),
        "anchor_replacements": 3,
        "source_unchanged": sha256(source) == base_sha,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--receipt", type=Path)
    args = ap.parse_args()
    receipt = patch(args.source, args.output)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

