"""Patch the frozen M01/M03/M07 method worker for the Reacher correction.

The LeWM worker has its own evaluation loop; M01, M03 and M07 use
``method_formal_v1.py`` plus ``adapters.harness``.  This patcher creates a
copy, installs the same non-terminating Reacher adapter after the target has
been bound, and reconstitutes ``_d1_success`` from the tracker while leaving
the returned ``terminated`` flag false.
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
    anchor = "env,initial,goal=bind(case,assets['dataset'],assets['dataset_sha256'])\n  try:"
    if anchor not in text:
        raise RuntimeError("method_formal_v1 bind anchor missing")
    replacement = (
        "env,initial,goal=bind(case,assets['dataset'],assets['dataset_sha256'])\n"
        "  r3_tracker=None\n"
        "  if a.task=='reacher':\n"
        "   from REVISION_3_REACHER_PATCH import install_nonterminating_reacher\n"
        "   r3_tracker=install_nonterminating_reacher(env.world.envs.envs[0].unwrapped)\n"
        "   _native_env_step=env.step\n"
        "   def _corrected_env_step(action):\n"
        "    obs,reward,terminated,truncated,info=_native_env_step(action)\n"
        "    info['_d1_success']=r3_tracker.consume_step()\n"
        "    return obs,reward,False,truncated,info\n"
        "   env.step=_corrected_env_step\n"
        "  try:"
    )
    text = text.replace(anchor, replacement, 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text)
    return {
        "base_source": str(source),
        "base_sha256": base_sha,
        "patched_worker": str(output),
        "patched_sha256": sha256(output),
        "patch_module": "REVISION_3_REACHER_PATCH.py",
        "anchor_replacements": 1,
        "source_unchanged": sha256(source) == base_sha,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--receipt", type=Path)
    args = ap.parse_args()
    result = patch(args.source, args.output)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

