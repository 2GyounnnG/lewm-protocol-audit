"""Finite, explicitly selected stage of the corrected Reacher FORMAL queue.

This script never advances to another stage, transfers data, or stops the
instance. It requires final T1--T4/runtime evidence, the sealed correction
registration, and a receipt of local SHA verification before starting. For
stages 2 and 3 it additionally requires local SHA verification of all artifacts
from the preceding stage. All paths retain lexical resume_01 spelling because
the frozen formal_guard uses that spelling; do not call Path.resolve().

Additional launch-receipt schema (alongside frozen formal_guard fields):
  verified_evidence: {role: {path: W-relative-path, sha256: file-sha}}
  roles = correction_registration, technical_gates, runtime_checks, local_return
Local-return receipt schema:
  status: VERIFIED_LOCAL_RETURN
  mismatch_count: 0
  verified_files: integer > 0
  manifest_sha256: {W-relative-path: sha256, ...}
For a stage-return receipt additionally provide:
  stage: 1 or 2
  stage_status_sha256: SHA of FORMAL_STAGE_<stage>_STATUS.json
The preformal manifest must cover final code plus the three evidence files.
Stage manifests must cover every file in the preceding status artifact_sha256.
These receipts are written only after actual local verification, never here.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import time
import traceback

import numpy as np

W = Path("/workspace/d1/step4/resume_01")
PY = "/workspace/d1/venvs/r3-reacher-v3/bin/python"
RUNNER = W / "code/step4_worker_r3_final.py"
RECEIPT = W / "FORMAL_LAUNCH_RECEIPT.json"
STAGES = {
    1: [("D1V2_001", "LeWM", 1, 30, "official"),
        ("D1V2_002", "LeWM", 3, 30, "official")],
    2: [("D1V2_009", "M01", 1, 30, "released"),
        ("D1V2_010", "M03", 1, 30, "official"),
        ("D1V2_011", "M07", 1, 30, "3072"),
        ("D1V2_012", "M07", 1, 30, "4096"),
        ("D1V2_013", "M07", 1, 30, "6144")],
    3: [("D1V2_029", "LeWM", 1, 10, "official"),
        ("D1V2_030", "LeWM", 3, 10, "official")],
}
STREAMS = ("R3_ORIGINAL", "R4_ALT_CEM_1", "R4_ALT_CEM_2")
COMPLETE_STATUS = "PROCESSES_COMPLETE_RECORDS_PRESENT_PENDING_LOCAL_RETURN"
FIELDS = ("physics.time", "qpos", "qvel", "target_qpos")


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def relative_path(name):
    p = Path(name)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("Manifest path must be lexical W-relative: " + str(name))
    return W / p


def verify_mapping(mapping):
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("Nonempty SHA file mapping required")
    for name, wanted in mapping.items():
        if sha(relative_path(name)) != wanted:
            raise ValueError("SHA mismatch: " + name)


def verify_local_return(path, required):
    receipt = read(path)
    if (receipt.get("status") != "VERIFIED_LOCAL_RETURN"
            or receipt.get("mismatch_count") != 0
            or not isinstance(receipt.get("verified_files"), int)
            or receipt["verified_files"] <= 0):
        raise ValueError("Local return not verified: " + str(path))
    manifest = receipt.get("manifest_sha256")
    if not isinstance(manifest, dict):
        raise ValueError("manifest_sha256 must be a relative-file-to-SHA mapping")
    for name, wanted in required.items():
        if manifest.get(name) != wanted:
            raise ValueError("Local-return manifest does not cover current file: " + name)
    verify_mapping(required)
    return receipt


def preflight(stage):
    # Import the frozen guard, preserving its lexical path and actual checks.
    sys.path.insert(0, str(W / "code"))
    from formal_guard import authorize
    launch = read(RECEIPT)
    evidence = launch["verified_evidence"]
    required_evidence = {}
    loaded = {}
    for role in ("correction_registration", "technical_gates", "runtime_checks", "local_return"):
        entry = evidence[role]
        p = relative_path(entry["path"])
        if sha(p) != entry["sha256"]:
            raise ValueError("Evidence SHA mismatch: " + role)
        loaded[role] = read(p)
        if role != "local_return":
            required_evidence[entry["path"]] = entry["sha256"]
    gate = loaded["technical_gates"]
    if (gate.get("status") != "PASS" or gate.get("full_registered_group_coverage") is not True
            or any(gate.get("gates", {}).get(k, {}).get("status") != "PASS" for k in ("T1", "T2", "T3", "T4"))
            or len(gate.get("case_stream_results", [])) != 108):
        raise ValueError("Full final-code T1--T4 evidence not PASS")
    if loaded["runtime_checks"].get("status") != "PASS":
        raise ValueError("Addendum runtime checks not PASS")
    reg = loaded["correction_registration"]
    if not str(reg.get("status", "")).startswith("SEALED"):
        raise ValueError("Correction registration is not sealed")
    registered_code = reg.get("final_code_sha256")
    if not isinstance(registered_code, dict) or not registered_code:
        raise ValueError("Correction registration lacks final code SHA mapping")
    if reg.get("code_sha256") != registered_code:
        raise ValueError("Correction registration code mappings disagree")
    for name, wanted in registered_code.items():
        if launch["code_sha256"].get(name) != wanted:
            raise ValueError("Launch code differs from sealed correction registration: " + name)
    for name in ("code/step4_worker_r3_final.py", "code/official_formal_v4_reacher.py",
                 "code/method_formal_v3_reacher.py", "code/adapters/swm_runtime_recorded.py"):
        if name not in registered_code:
            raise ValueError("Final worker/bind code missing from correction registration: " + name)
    if launch.get("correction_registration_sha256") != evidence["correction_registration"]["sha256"]:
        raise ValueError("Launch receipt does not bind final correction registration")
    if launch.get("tech_gate_sha256") != evidence["technical_gates"]["sha256"]:
        raise ValueError("Launch receipt does not bind final T1--T4 result")
    if launch.get("runtime_checks_sha256") != evidence["runtime_checks"]["sha256"]:
        raise ValueError("Launch receipt does not bind final runtime checks")
    required_local = dict(launch["code_sha256"], **required_evidence)
    self_name = str(Path(__file__).relative_to(W))
    if self_name not in launch["code_sha256"]:
        raise ValueError("Queue script must be included in final code SHA mapping")
    verify_local_return(relative_path(evidence["local_return"]["path"]), required_local)
    heldout = read(W / "cases/HELDOUT_CASES_V2.json")["tasks"]["reacher"]
    if len(heldout) != 100 or len({x["case_id"] for x in heldout}) != 100:
        raise ValueError("Exactly 100 distinct sealed HELDOUT cases required")
    for cid, model, history, iterations, seed in STAGES[stage]:
        authorized = authorize(cid, RUNNER, RECEIPT)
        spec = authorized["condition_specs"][cid]
        expected = {"task": "reacher", "model": model, "history": history,
                    "iterations": iterations, "train_seed": seed, "stream_letters": "ABC",
                    "cases": 100, "expected_trajectories": 300, "budget_raw": 50,
                    "success_mode": "full50", "stage_order": stage}
        for key, value in expected.items():
            if str(spec.get(key)) != str(value):
                raise ValueError(f"Condition receipt mismatch {cid}: {key}")
        worker_name = ("official_formal_v4_reacher.py" if model == "LeWM"
                       else "method_formal_v3_reacher.py")
        authorize(cid, W / "code" / worker_name, RECEIPT)
        if (W / "formal_verified" / cid).exists():
            raise FileExistsError("Refuse to overwrite an existing formal condition: " + cid)
    previous_receipt = None
    if stage > 1:
        previous_status_path = W / f"FORMAL_STAGE_{stage - 1}_STATUS.json"
        previous = read(previous_status_path)
        if previous.get("stage") != stage - 1 or previous.get("status") != COMPLETE_STATUS:
            raise ValueError("Previous stage processes or record completeness unresolved")
        previous_receipt_path = W / f"FORMAL_STAGE_{stage - 1}_LOCAL_RETURN.json"
        previous_receipt = verify_local_return(previous_receipt_path, previous["artifact_sha256"])
        if (previous_receipt.get("stage") != stage - 1
                or previous_receipt.get("stage_status_sha256") != sha(previous_status_path)):
            raise ValueError("Previous-stage local receipt does not bind exact stage status")
    return launch, heldout, previous_receipt


def inspect_records(out, spec, cases):
    cid, model, _, _, _ = spec
    expected = {(x["case_id"], s) for x in cases for s in STREAMS}
    paths = (sorted(out.glob("*/*/result.json")) if model == "LeWM"
             else sorted(out.glob("*/*.json")))
    seen = set()
    complete = 0
    errors = []
    wall_sum = 0.0
    for p in paths:
        try:
            r = read(p)
            identity = (r["case_id"], r["stream"])
            if identity not in expected or identity in seen:
                raise ValueError("Unexpected or duplicate case-stream")
            seen.add(identity)
            if (r.get("status") != "COMPLETE" or r.get("phase") != "FORMAL"
                    or r.get("condition_id") != cid or r.get("executed_raw_steps") != 50
                    or r.get("raw_budget") != 50 or r.get("success_mode") != "full50"
                    or r.get("error") is not None):
                raise ValueError("Formal full50 completion metadata differs")
            record = r["reacher_runtime"]
            if (record.get("schema_version") != "reacher_correction_record_v2"
                    or len(record["events"]) != 100 or len(record["micro_steps"]) != 100
                    or len(record["env_steps"]) != 50 or len(record["physics_steps"]) != 50
                    or len(record["step_any_labels"]) != 50 or len(record["step_end_labels"]) != 50
                    or "reset_count" not in record or "internal_reset_events" not in record):
                raise ValueError("Required observational record incomplete")
            for state in ([record["initial_state"]] + record["physics_steps"]
                          + [x[side] for x in record["micro_steps"] for side in ("before", "after")]):
                if not all(k in state and np.isfinite(np.asarray(state[k], float)).all() for k in FIELDS):
                    raise ValueError("Missing or nonfinite recorded physical state")
            if model == "LeWM":
                with np.load(p.parent / "trajectory.npz", allow_pickle=False) as z:
                    actions = z["raw_actions"]
                    if any(z[k].shape != (50,) for k in ("successes", "success_any_in_step", "success_at_step_end")):
                        raise ValueError("Trajectory step labels missing")
                complete_receipt = read(p.parent / "COMPLETE.json")["sha256"]
                for name, wanted in complete_receipt.items():
                    if sha(p.parent / name) != wanted:
                        raise ValueError("Worker COMPLETE receipt SHA mismatch")
            else:
                actions = np.load(p.with_suffix(".actions.npy"), allow_pickle=False)
                first = np.load(p.with_suffix(".first_plan.npy"), allow_pickle=False)
                if not np.isfinite(first).all() or len(r["steps"]) != 50:
                    raise ValueError("Method plan or step records incomplete")
                for row in r["steps"]:
                    if "success_any_in_step" not in row or "success_at_step_end" not in row:
                        raise ValueError("Method step labels missing")
            if actions.shape != (50, 2) or not np.isfinite(actions).all():
                raise ValueError("Saved raw actions incomplete or nonfinite")
            if not all(r.get(k) in (0, 1) for k in ("success_any", "success_block", "success_final")):
                raise ValueError("Result labels incomplete")
            wall_sum += float(r.get("whole_case_wall_seconds", 0.0))
            complete += 1
        except Exception as exc:
            errors.append({"path": str(p.relative_to(W)), "error": repr(exc)})
    missing = sorted(expected - seen)
    return {"status": "COMPLETE_RECORDS" if complete == len(expected) and not errors and not missing else "INCOMPLETE_RECORDS",
            "expected_records": 300, "observed_record_files": len(paths),
            "complete_records": complete, "missing_case_streams": missing,
            "errors": errors, "sum_case_wall_seconds": wall_sum,
            "scientific_gate_or_result_claim": False}


def run_condition(spec, gpu, stage, cases):
    cid, model, history, iterations, seed = spec
    out = W / "formal_verified" / cid
    if out.exists():
        raise FileExistsError(out)
    env = dict(os.environ, MUJOCO_GL="egl", CUDA_VISIBLE_DEVICES=str(gpu),
               PYTHONPATH=str(W) + ":" + str(W / "code"))
    command = [PY, str(RUNNER), "--model", model, "--task", "reacher", "--history", str(history),
               "--iterations", str(iterations), "--train-seed", seed, "--streams", "ABC",
               "--success-mode", "full50", "--phase", "FORMAL", "--budget", "50",
               "--condition-id", cid, "--case-start", "0", "--case-end", "100", "--output", str(out)]
    log = W / "logs_verified" / f"FORMAL_{cid}.log"
    log.parent.mkdir(exist_ok=True)
    started_utc, started = utc(), time.monotonic()
    print(json.dumps({"event": "START", "utc": started_utc, "stage": stage, "condition": cid, "gpu": gpu}), flush=True)
    with log.open("xb") as f:
        process = subprocess.run(command, env=env, stdout=f, stderr=subprocess.STDOUT)
    duration = time.monotonic() - started
    complete = inspect_records(out, spec, cases)
    record = {"condition_id": cid, "stage": stage, "gpu": gpu,
              "started_utc": started_utc, "completed_utc": utc(), "exit_code": process.returncode,
              "process_wall_seconds": duration, "allocated_gpu_hours": duration / 3600,
              "command": command, "log_sha256": sha(log), "record_completeness": complete,
              "process_status": "EXITED_ZERO" if process.returncode == 0 else "EXITED_NONZERO",
              "not_a_scientific_gate_receipt": True}
    write_new(W / "logs_verified" / f"FORMAL_{cid}_PROCESS.json", record)
    print(json.dumps({"event": "CONDITION_EXIT", "utc": utc(), "condition": cid,
                      "exit_code": process.returncode, "complete_records": complete["complete_records"]}), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for stage in (1, 2, 3):
        group.add_argument(f"--stage{stage}", action="store_const", dest="stage", const=stage)
    a = parser.parse_args()
    stage = a.stage
    started = time.monotonic()
    launch, cases, previous = preflight(stage)
    start_path = W / f"FORMAL_STAGE_{stage}_STARTED.json"
    write_new(start_path, {"stage": stage, "utc": utc(), "conditions": [x[0] for x in STAGES[stage]],
              "launch_receipt_sha256": sha(RECEIPT), "queue_sha256": sha(__file__),
              "previous_stage_local_return_sha256": None if previous is None else sha(W / f"FORMAL_STAGE_{stage - 1}_LOCAL_RETURN.json"),
              "execution": "up to four GPUs concurrently within this stage only; no automatic next stage"})
    todo = queue.Queue()
    for spec in STAGES[stage]:
        todo.put(spec)

    def worker(gpu):
        rows = []
        while True:
            try:
                spec = todo.get_nowait()
            except queue.Empty:
                return rows
            try:
                rows.append(run_condition(spec, gpu, stage, cases))
            except Exception as exc:
                rows.append({"condition_id": spec[0], "stage": stage, "gpu": gpu,
                             "exit_code": None, "process_status": "LAUNCH_OR_CHECK_FAILURE",
                             "error": repr(exc), "traceback": traceback.format_exc(), "utc": utc(),
                             "not_a_scientific_gate_receipt": True})
            # Continue other, unaffected conditions; never auto-retry a failed one.

    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        rows = sum(list(pool.map(worker, range(4))), [])
    order = {s[0]: i for i, s in enumerate(STAGES[stage])}
    rows.sort(key=lambda r: order[r["condition_id"]])
    all_complete = (len(rows) == len(STAGES[stage])
                    and all(r.get("exit_code") == 0 and r.get("record_completeness", {}).get("status") == "COMPLETE_RECORDS" for r in rows))
    artifact_paths = [start_path]
    for spec in STAGES[stage]:
        cid = spec[0]
        artifact_paths.extend(p for p in (W / "formal_verified" / cid).rglob("*") if p.is_file())
        artifact_paths.extend(p for p in (W / "logs_verified").glob(f"FORMAL_{cid}*") if p.is_file())
    artifacts = {str(p.relative_to(W)): sha(p) for p in sorted(set(artifact_paths))}
    report = {"stage": stage, "utc": utc(),
              "status": COMPLETE_STATUS if all_complete else "PROCESS_OR_RECORD_COMPLETENESS_FAILURE",
              "conditions_expected": len(STAGES[stage]), "conditions_exited_zero": sum(r.get("exit_code") == 0 for r in rows),
              "records_expected": len(STAGES[stage]) * 300,
              "records_complete": sum(r.get("record_completeness", {}).get("complete_records", 0) for r in rows),
              "stage_wall_seconds": time.monotonic() - started,
              "allocated_gpu_hours": sum(r.get("allocated_gpu_hours", 0.0) for r in rows),
              "rows": rows, "artifact_sha256": artifacts,
              "not_a_scientific_gate_receipt": True,
              "next_action": "Return artifacts to local computer and verify SHA before explicit next-stage invocation; this queue exits now.",
              "automatic_next_stage": False, "automatic_instance_stop": False}
    write_new(W / f"FORMAL_STAGE_{stage}_STATUS.json", report)
    print(json.dumps({"event": "STAGE_EXIT", "stage": stage, "status": report["status"],
                      "records_complete": report["records_complete"], "automatic_next_stage": False}), flush=True)
    return 0 if all_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
