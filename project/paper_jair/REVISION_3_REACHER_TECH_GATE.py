"""Static and synthetic technical gate for the Revision-3 Reacher rerun.

This script is safe to run on the laptop: it does not import torch, dm_control,
MuJoCo, or stable-worldmodel.  The ``--mode static`` check records source
hashes and exercises the patch against a tiny fake wrapper.  A future GPU
stage may run ``--mode runtime`` after the patched worker and pinned
environment are installed; that mode is intentionally a fail-closed checklist
and does not launch a formal job.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np


ROOT = Path(__file__).resolve().parent
FROZEN_SOURCE = ROOT.parent / "d1_execution/step4/resume_01/code/official_formal_v2.py"
METHOD_SOURCE = ROOT.parent / "d1_execution/step4/resume_01/code/method_formal_v1.py"
REACHER_SOURCE = ROOT.parent / (
    "d1_execution/step4/remote_return/workspace/d1/repos/SWM_NATIVE/"
    "stable_worldmodel/envs/dmcontrol/reacher.py"
)
TASK_SOURCE = ROOT.parent / (
    "d1_execution/step4/remote_return/workspace/d1/repos/SWM_NATIVE/"
    "stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py"
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_patch():
    spec = importlib.util.spec_from_file_location("revision3_patch", ROOT / "REVISION_3_REACHER_PATCH.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def synthetic_test(patch) -> dict:
    class FakePhysics:
        def __init__(self):
            self.data = SimpleNamespace(qpos=np.array([0.0, 0.0], dtype=np.float64))

    class FakeTask:
        qpos_threshold = 0.05
        target_qpos = np.array([0.0, 0.0], dtype=np.float64)

        def get_termination(self, physics):
            return 0.0 if np.all(np.abs(physics.data.qpos - self.target_qpos) < self.qpos_threshold) else None

    physics = FakePhysics()
    env = SimpleNamespace(task=FakeTask(), physics=physics)
    wrapper = SimpleNamespace(env=env, _task_name="qpos_match", action_repeat=2)
    tracker = patch.install_nonterminating_reacher(wrapper)
    threshold_before = env.task.qpos_threshold
    first = wrapper._is_terminated(None)
    physics.data.qpos[:] = [0.2, 0.0]
    second = wrapper._is_terminated(None)
    physics.data.qpos[:] = [0.0, 0.0]
    third = wrapper._is_terminated(None)
    high_level = tracker.consume_step()
    return {
        "task_get_termination_after_patch": env.task.get_termination(physics),
        "wrapper_termination_returns": [bool(first), bool(second), bool(third)],
        "consumed_high_level_success": bool(high_level),
        "threshold_unchanged": threshold_before == env.task.qpos_threshold == 0.05,
        "original_predicate_preserved": bool(getattr(wrapper, "_revision3_original_get_termination", None)(physics) == 0.0),
        "pass": env.task.get_termination(physics) is None and not first and not second and not third and high_level and threshold_before == 0.05,
    }


def static_gate() -> dict:
    patch = load_patch()
    source_text = TASK_SOURCE.read_text()
    reacher_text = REACHER_SOURCE.read_text()
    formal_text = FROZEN_SOURCE.read_text()
    method_text = METHOD_SOURCE.read_text()
    required = {
        "task_predicate_lines": "if np.all(diff < self.qpos_threshold):" in source_text,
        "wrapper_termination_lines": "self.env.task.get_termination(self.env.physics)" in reacher_text,
        "full_budget_flag_only": "allowed['terminated'][...]=False" in formal_text,
        "method_worker_has_boundworld_step": "env,initial,goal=bind(case,assets['dataset'],assets['dataset_sha256'])" in method_text,
        "patch_has_none_termination": "return None" in (ROOT / "REVISION_3_REACHER_PATCH.py").read_text(),
    }
    synth = synthetic_test(patch)
    return {
        "status": "PASS" if all(required.values()) and synth["pass"] else "FAIL",
        "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "files": {str(p): sha(p) for p in (FROZEN_SOURCE, METHOD_SOURCE, REACHER_SOURCE, TASK_SOURCE, ROOT / "REVISION_3_REACHER_PATCH.py", ROOT / "REVISION_3_REACHER_WORKER_PATCH.py", ROOT / "REVISION_3_REACHER_METHOD_PATCH.py")},
        "source_checks": required,
        "synthetic_patch_test": synth,
        "runtime_required_before_formal": [
            "instantiate pinned Reacher qpos_match wrapper",
            "verify exactly one reset per case",
            "verify first-success action prefix equals original trace",
            "verify monotone physics time and no post-success qpos jump",
            "verify independent predicate labels at every raw step",
            "exercise the same patch through AP/M01/M03/M07 BoundWorld worker",
        ],
    }


def runtime_gate() -> dict:
    # Deliberately no runtime imports on the author laptop.  A GPU runner may
    # call this mode after installing the pinned environment and fill the
    # runtime receipt with environment-specific facts.
    return {
        "status": "NOT_RUN",
        "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "reason": "Awaiting author-provided SSH instance; no environment or model was started.",
        "required": [
            "dm_control qpos_match wrapper instantiated from pinned commit",
            "task.get_termination disabled only for formal full-budget path",
            "qpos predicate recorded independently at every action-repeat call",
            "reset counter equals one per case",
            "physical time monotone; post-success state has no reset jump",
            "first-success prefix matches original protocol before any success",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("static", "runtime"), default="static")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    result = static_gate() if args.mode == "static" else runtime_gate()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in ("PASS", "NOT_RUN") else 1


if __name__ == "__main__":
    raise SystemExit(main())

