"""Numerical T1--T4 gates for final-code Reacher TECH outputs, never FORMAL.

Run on the pinned CPU environment. No model, planner, dataset, or CUDA work is
started. The independent replay uses the uninstrumented SWM Reacher wrapper,
disables only task termination, and performs both native dm_control calls for
every saved raw action. Missing evidence is BLOCKED, never an inferred PASS.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import traceback
from pathlib import Path

import numpy as np

GROUPS = (
    "LeWM_h1_i30", "LeWM_h3_i30", "M01_h1", "M03_h1",
    "M07_3072_h1", "M07_4096_h1", "M07_6144_h1",
    "LeWM_h1_i10", "LeWM_h3_i10",
)
STREAMS = ("R3_ORIGINAL", "R4_ALT_CEM_1", "R4_ALT_CEM_2")
FIELDS = ("physics.time", "qpos", "qvel", "target_qpos")
# Numerical evidence tolerances, never a tolerance on T1 or the success test.
STATE_ATOL = 1e-12
TIME_ATOL = 1e-12
MICRO_DT = 0.02
THRESHOLD = 0.05


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def status(checks):
    return "PASS" if all(checks.values()) else "FAIL"


def equal_bytes(a, b):
    return (a.dtype == b.dtype and a.shape == b.shape
            and a.tobytes(order="C") == b.tobytes(order="C"))


def state_delta(a, b):
    result = {}
    for field in FIELDS:
        x, y = np.asarray(a[field], float), np.asarray(b[field], float)
        if x.shape != y.shape or not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError("Invalid state field " + field)
        result[field] = float(np.max(np.abs(x - y))) if x.size else 0.0
    return result


def is_same_state(a, b):
    return all(x <= STATE_ATOL for x in state_delta(a, b).values())


def predicate(state):
    return bool(np.all(np.abs(np.asarray(state["qpos"], float)
                              - np.asarray(state["target_qpos"], float))
                       < float(state["qpos_threshold"])))


def load_result(root, group, case_id, stream):
    base = root / "tech_verified" / group
    if group.startswith("LeWM"):
        p = base / case_id / stream / "result.json"
        action_path = p.parent / "trajectory.npz"
        with np.load(action_path, allow_pickle=False) as z:
            actions = z["raw_actions"].copy()
            labels = {k: z[k].copy().tolist() for k in
                      ("successes", "success_any_in_step", "success_at_step_end")}
    else:
        p = base / stream / (case_id + ".json")
        action_path = p.with_suffix(".actions.npy")
        actions = np.load(action_path, allow_pickle=False)
        labels = None
    result = read(p)
    if result.get("phase") != "TECH":
        raise ValueError("Refuse non-TECH output: " + str(p))
    return result, actions, labels, {str(p): sha(p), str(action_path): sha(action_path)}


def t1(root, group, case_id, stream, actions, reference):
    base = root / "t1_reference" / group / case_id / stream
    required = [base / n for n in ("actions.npy", "successes.npy", "metadata.json")]
    missing = [str(p) for p in required if not p.is_file()]
    if reference is None or missing:
        return {"status": "BLOCKED", "reason": "Original sealed STEP4 reference missing",
                "missing": missing, "index_entry_present": reference is not None}
    meta = read(required[2])
    ref = np.load(required[0], allow_pickle=False)
    successes = np.load(required[1], allow_pickle=False).astype(bool)
    hit = np.flatnonzero(successes)
    first = int(hit[0]) if hit.size else None
    stop = first + 1 if first is not None else 50
    sources = meta.get("source_files", [])
    identity = {
        "actions_sha_matches_manifest": sha(required[0]) == reference["extracted_actions_sha256"],
        "successes_sha_matches_manifest": sha(required[1]) == reference["extracted_successes_sha256"],
        "all_sources_seal_verified": bool(sources) and all(x.get("step4_seal_verified") is True for x in sources),
        "metadata_prefix_matches_labels": meta["prefix_stop_exclusive"] == stop,
        "index_prefix_matches_labels": reference["prefix_stop_exclusive"] == stop,
        "metadata_identity": all(meta[k] == v for k, v in
                                 (("group", group), ("case_id", case_id), ("stream", stream))),
        "reference_shape": ref.shape == (50, 2) and successes.shape == (50,),
    }
    pre_stop = first if first is not None else 50
    first_diff = None
    if actions.shape == ref.shape:
        for i in range(stop):
            if not equal_bytes(actions[i:i + 1], ref[i:i + 1]):
                first_diff = i
                break
    pre_equal = equal_bytes(actions[:pre_stop], ref[:pre_stop])
    include_equal = equal_bytes(actions[:stop], ref[:stop])
    checks = dict(identity, before_first_success_bitwise=pre_equal,
                  including_first_success_action_bitwise=include_equal)
    max_abs = (float(np.max(np.abs(actions[:stop].astype(float) - ref[:stop].astype(float))))
               if actions[:stop].shape == ref[:stop].shape else None)
    return {"status": status(checks), "checks": checks,
            "first_original_success_index_zero_based": first,
            "actions_before_success_compared": pre_stop,
            "actions_including_first_success_compared": stop,
            "first_divergence_action_zero_based": first_diff,
            "first_divergence_action_one_based": None if first_diff is None else first_diff + 1,
            "max_abs_action_difference_through_first_success": max_abs,
            "reference_dtype": ref.dtype.str, "final_dtype": actions.dtype.str,
            "reference_file_sha256": {str(p): sha(p) for p in required},
            "required_on_failure": None if status(checks) == "PASS" else
                "Run unpatched v2 on this machine for the identical case-stream; compare to STEP4 and corrected worker before deciding cause."}


def t2(record):
    micros = record["micro_steps"]
    reset_events = record["reset_events"]
    dm_events = record["dm_reset_events"]
    init_events = record["initialize_episode_events"]
    checks = {
        "one_real_wrapper_reset": record["reset_count"] == record["reset_calls"] == len(reset_events) == 1,
        "wrapper_reset_before_actions": all(x["event_count"] == 0 for x in reset_events),
        "one_real_dm_control_reset": record["dm_reset_calls"] == len(dm_events) == 1,
        "one_real_initialize_episode": record["initialize_episode_calls"] == len(init_events) == 1,
        "dm_resets_only_explicit_initial_reset": all(x["phase"] == "explicit_wrapper_reset" and x["event_count"] == 0 for x in dm_events),
        "initialization_only_explicit_initial_reset": all(x["phase"] == "explicit_wrapper_reset" and x["event_count"] == 0 for x in init_events),
        "no_internal_reset_events": record["internal_reset_events"] == [],
        "no_pending_reset": all(not x["pending_reset_before"] and not x["pending_reset_after"] for x in micros),
        "no_dm_terminal_steps": all(x["dm_step_last"] is False for x in micros),
        "reset_count_unchanged_at_each_step": all(x["reset_calls"] == 1 and x["dm_reset_calls"] == 1 and x["internal_reset_event_count"] == 0 for x in record["env_steps"]),
    }
    return {"status": status(checks), "checks": checks,
            "wrapper_reset_count": record["reset_count"], "dm_control_reset_count": record["dm_reset_calls"],
            "initialize_episode_count": record["initialize_episode_calls"],
            "internal_reset_event_count": len(record["internal_reset_events"]),
            "pending_reset_microsteps": sum(x["pending_reset_before"] or x["pending_reset_after"] for x in micros),
            "dm_terminal_microsteps": sum(x["dm_step_last"] for x in micros)}


def cpu_replay(record, actions, case):
    # This imports no experiment patch or neural model. env.step is the native
    # action-scale wrapper around control.Environment, exactly as SWM calls it.
    from stable_worldmodel.envs.dmcontrol.reacher import ReacherDMControlWrapper
    env = ReacherDMControlWrapper(task="qpos_match")
    max_error = {k: 0.0 for k in FIELDS}
    first_mismatch = None
    count = 0
    pending = 0
    final_steps = 0
    try:
        env.reset(seed=int(case["reset_seed"]))
        initial = record["initial_state"]
        env.set_state(np.asarray(initial["qpos"], float), np.asarray(initial["qvel"], float))
        env.set_target_qpos(np.asarray(initial["target_qpos"], float))
        env.env.physics.data.time = float(initial["physics.time"])
        env.env.physics.forward()
        env.env.task.get_termination = lambda _physics: None
        control = env.env
        while hasattr(control, "_env"):
            control = control._env
        # reset() already sets this to false; assert rather than hide a reset.
        if bool(getattr(control, "_reset_next_step", False)):
            raise RuntimeError("Independent replay reset left a pending reset")

        def snap():
            return {"physics.time": float(env.env.physics.time()),
                    "qpos": env.env.physics.data.qpos.copy().tolist(),
                    "qvel": env.env.physics.data.qvel.copy().tolist(),
                    "target_qpos": np.asarray(env.env.task.target_qpos).copy().tolist()}

        for i, action in enumerate(actions):
            for j in range(2):
                k = 2 * i + j
                row = record["micro_steps"][k]
                before = snap()
                pending += int(bool(getattr(control, "_reset_next_step", False)))
                step = env.env.step(np.asarray(action).astype(env.action_spec_dtype))
                final_steps += int(step.last())
                after = snap()
                for side, actual in (("before", before), ("after", after)):
                    errors = state_delta(actual, row[side])
                    for field, err in errors.items():
                        max_error[field] = max(max_error[field], err)
                    if first_mismatch is None and any(x > STATE_ATOL for x in errors.values()):
                        first_mismatch = {"microstep_one_based": k + 1,
                                          "environment_step_one_based": i + 1,
                                          "side": side, "max_abs_by_field": errors}
                count += 1
        return {"status": "PASS" if first_mismatch is None and pending == final_steps == 0 else "FAIL",
                "microsteps_replayed": count, "state_comparisons": count * 2,
                "max_abs_by_field": max_error, "first_mismatch": first_mismatch,
                "pending_resets": pending, "terminal_microsteps": final_steps,
                "absolute_tolerance": STATE_ATOL, "relative_tolerance": 0,
                "source": str(Path(__import__(ReacherDMControlWrapper.__module__, fromlist=["__file__"]).__file__)),
                "method": "native uninstrumented SWM Reacher; native action scaling/dtype; get_termination=None; exactly two dm_control steps per raw action"}
    finally:
        env.close()


def t3(record, actions, case):
    micro = record["micro_steps"]
    initial = record["initial_state"]
    states = [initial] + [x["after"] for x in micro]
    all_states = states + [x["before"] for x in micro] + record["physics_steps"]
    finite = all(all(np.isfinite(np.asarray(s[k], float)).all() for k in FIELDS) for s in all_states)
    times = np.asarray([s["physics.time"] for s in states], float)
    dt_values = np.diff(times)
    qpos = np.asarray([s["qpos"] for s in states], float)
    target = np.asarray(initial["target_qpos"])
    transitions = [is_same_state(x["before"], states[i]) for i, x in enumerate(micro)]
    env_match = [is_same_state(x["state"], micro[2 * i + 1]["after"])
                 and is_same_state(record["physics_steps"][i], x["state"])
                 for i, x in enumerate(record["env_steps"])]
    checks = {
        "finite_actions_and_states": finite and bool(np.isfinite(actions).all()),
        "physical_time_strictly_increases": bool(np.all(dt_values > 0)),
        "each_microstep_dt_0_02": bool(np.all(np.abs(dt_values - MICRO_DT) <= TIME_ATOL)),
        "state_chain_continuous": all(transitions),
        "environment_step_state_equals_second_microstep": all(env_match),
        "target_unchanged": all(np.array_equal(np.asarray(s["target_qpos"]), target) for s in all_states),
        "action_repeat_exactly_two": record["action_repeat"] == 2 and all(x["microstep_count"] == 2 for x in record["env_steps"]),
    }
    try:
        replay = cpu_replay(record, actions, case)
    except (ImportError, ModuleNotFoundError) as exc:
        replay = {"status": "BLOCKED", "reason": repr(exc)}
    except Exception as exc:
        replay = {"status": "FAIL", "reason": repr(exc), "traceback": traceback.format_exc()}
    checks["independent_cpu_replay_matches_every_microstep"] = replay["status"] == "PASS"
    out_status = status(checks)
    if replay["status"] == "BLOCKED" and all(v for k, v in checks.items() if not k.startswith("independent_")):
        out_status = "BLOCKED"
    return {"status": out_status, "checks": checks,
            "microsteps": len(micro), "environment_steps": len(record["env_steps"]),
            "initial_physics_time": float(times[0]), "final_physics_time": float(times[-1]),
            "min_microstep_dt": float(np.min(dt_values)), "max_microstep_dt": float(np.max(dt_values)),
            "max_microstep_dt_error": float(np.max(np.abs(dt_values - MICRO_DT))),
            "max_abs_qpos_step_change": float(np.max(np.abs(np.diff(qpos, axis=0)))),
            "state_chain_mismatches": len(transitions) - sum(transitions),
            "environment_state_mismatches": len(env_match) - sum(env_match),
            "continuity_rule": "No arbitrary qpos-jump cutoff; recorded changes must match independent non-reset physics replay at every microstep.",
            "cpu_replay": replay}


def t4(record, result, saved_labels):
    events = np.asarray(record["events"], bool)
    micro = record["micro_steps"]
    expected = np.asarray([predicate(x["state_at_predicate"]) for x in micro], bool)
    any_labels = expected.reshape(50, 2).any(axis=1)
    end_labels = expected.reshape(50, 2)[:, -1]
    checks = {
        "threshold_exactly_0_05": all(x["state_at_predicate"]["qpos_threshold"] == THRESHOLD for x in micro),
        "events_match_independent_qpos_predicate": bool(np.array_equal(events, expected)),
        "tracker_events_alias_matches": record["tracker_events"] == record["events"],
        "stored_predicates_match": all(x["predicate"] == x["independent_predicate"] == bool(expected[i]) for i, x in enumerate(micro)),
        "original_termination_values_match": all(x["original_termination_result"] == 0.0 if expected[i] else x["original_termination_result"] is None for i, x in enumerate(micro)),
        "predicate_observed_at_microstep_end": all(is_same_state(x["state_at_predicate"], x["after"]) for x in micro),
        "wrapper_termination_always_false": all(x["wrapper_terminated_return"] is False for x in micro),
        "step_any_labels_match": np.array_equal(record["step_any_labels"], any_labels),
        "step_end_labels_match": np.array_equal(record["step_end_labels"], end_labels),
        "step_label_aliases_match": np.array_equal(record["success_any_in_step"], any_labels) and np.array_equal(record["success_at_step_end"], end_labels),
        "event_offsets_match": record["event_offsets"] == list(range(0, 101, 2)),
        "env_step_event_mapping": all(x["env_step"] == i + 1 and x["event_start"] == 2 * i and x["event_end"] == 2 * i + 2 and x["success_any_in_step"] == bool(any_labels[i]) and x["success_at_step_end"] == bool(end_labels[i]) for i, x in enumerate(record["env_steps"])),
        "microstep_indices_match": all(x["micro_step"] == i + 1 and x["event_index"] == i for i, x in enumerate(micro)),
        "no_unconsumed_events_or_diagnostics": record["unconsumed_events"] == 0 and record["diagnostics"] == [],
        "task_termination_returns_none": len(record["task_termination_calls"]) == 100 and all(x["returned"] is None for x in record["task_termination_calls"]),
    }
    expected_result = {"success_any": int(any_labels.any()),
                       "success_block": int(end_labels[4::5].any()),
                       "success_final": int(end_labels[-1])}
    for key, value in expected_result.items():
        checks[key + "_uses_registered_semantics"] = result[key] == value
    if saved_labels is not None:
        checks["trajectory_npz_labels_match"] = (np.array_equal(saved_labels["successes"], any_labels)
            and np.array_equal(saved_labels["success_any_in_step"], any_labels)
            and np.array_equal(saved_labels["success_at_step_end"], end_labels))
    else:
        checks["method_steps_labels_match"] = len(result["steps"]) == 50 and all(
            x["success"] == x["success_any_in_step"] == bool(any_labels[i])
            and x["success_at_step_end"] == bool(end_labels[i]) for i, x in enumerate(result["steps"]))
    checks = {k: bool(v) for k, v in checks.items()}
    return {"status": status(checks), "checks": checks,
            "predicate_comparisons": len(events), "predicate_mismatches": int(np.sum(events != expected)),
            "positive_microstep_predicates": int(expected.sum()),
            "positive_any_in_step_labels": int(any_labels.sum()),
            "positive_step_end_labels": int(end_labels.sum()),
            "steps_where_two_labels_differ": int(np.sum(any_labels != end_labels)),
            "expected_result": expected_result}


def aggregate(rows, gate):
    results = [x[gate] for x in rows]
    counts = {s: sum(x["status"] == s for x in results) for s in ("PASS", "FAIL", "BLOCKED")}
    s = "FAIL" if counts["FAIL"] else "BLOCKED" if counts["BLOCKED"] or not results else "PASS"
    summary = {"status": s, "case_stream_counts": counts, "case_streams_expected": len(rows)}
    fields = {"T1": ("actions_before_success_compared", "actions_including_first_success_compared"),
              "T2": ("wrapper_reset_count", "dm_control_reset_count", "internal_reset_event_count", "pending_reset_microsteps"),
              "T3": ("microsteps", "environment_steps", "state_chain_mismatches", "environment_state_mismatches"),
              "T4": ("predicate_comparisons", "predicate_mismatches", "steps_where_two_labels_differ")}[gate]
    summary["totals"] = {k: sum(x.get(k, 0) for x in results) for k in fields}
    return summary


def evaluate(root, groups):
    root = root.resolve()
    tech_path = root / "cases/tech_reacher.json"
    cases = read(tech_path)
    if len(cases) != 4 or len({x["case_id"] for x in cases}) != 4:
        raise ValueError("Exactly four distinct registered TECH cases required")
    index_path = root / "t1_reference/REFERENCE_INDEX.json"
    index = read(index_path) if index_path.is_file() else {"technical_references": []}
    refs = {(x["group"], x["case_id"], x["stream"]): x for x in index["technical_references"]}
    rows = []
    for group in groups:
        for case in cases:
            for stream in STREAMS:
                case_id = case["case_id"]
                row = {"group": group, "case_id": case_id, "stream": stream}
                try:
                    result, actions, labels, hashes = load_result(root, group, case_id, stream)
                    record = result["reacher_runtime"]
                    row["files_sha256"] = hashes
                    structure = {"status_complete": result["status"] == "COMPLETE",
                        "full50": result["executed_raw_steps"] == 50 and result["raw_budget"] == 50,
                        "action_shape": actions.shape == (50, 2),
                        "record_schema": record["schema_version"] == "reacher_correction_record_v2",
                        "microstep_count": len(record["micro_steps"]) == len(record["events"]) == 100,
                        "step_count": len(record["env_steps"]) == len(record["physics_steps"]) == 50}
                    row["structure_checks"] = structure
                    row["T1"] = t1(root, group, case_id, stream, actions, refs.get((group, case_id, stream)))
                    if not all(structure.values()):
                        raise ValueError("Required final-code full50 record structure failed: " + repr(structure))
                    for gate, fun, args in (("T2", t2, (record,)), ("T3", t3, (record, actions, case)), ("T4", t4, (record, result, labels))):
                        try:
                            row[gate] = fun(*args)
                        except Exception as exc:
                            row[gate] = {"status": "FAIL", "reason": repr(exc), "traceback": traceback.format_exc()}
                except FileNotFoundError as exc:
                    for gate in ("T1", "T2", "T3", "T4"):
                        row.setdefault(gate, {"status": "BLOCKED", "reason": str(exc)})
                except Exception as exc:
                    for gate in ("T1", "T2", "T3", "T4"):
                        row.setdefault(gate, {"status": "FAIL", "reason": repr(exc), "traceback": traceback.format_exc()})
                rows.append(row)
                print(json.dumps({"group": group, "case_id": case_id, "stream": stream,
                                  **{g: row[g]["status"] for g in ("T1", "T2", "T3", "T4")}}), flush=True)
    gates = {g: aggregate(rows, g) for g in ("T1", "T2", "T3", "T4")}
    overall = "FAIL" if any(g["status"] == "FAIL" for g in gates.values()) else "BLOCKED" if any(g["status"] == "BLOCKED" for g in gates.values()) else "PASS"
    return {"status": overall, "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope": "FINAL_CODE_TECH_ONLY", "groups": list(groups),
        "full_registered_group_coverage": set(groups) == set(GROUPS),
        "formal_launch_authorized_by_this_file": False,
        "additional_required_evidence": "Both addendum section 2 runtime checks and locally returned SHA verification are required separately.",
        "evaluator_sha256": sha(__file__), "tech_case_sha256": sha(tech_path),
        "reference_index_sha256": sha(index_path) if index_path.is_file() else None,
        "rules": {"T1": "Strict dtype/shape/C-order-byte equality, before first original success and separately including its action; no success means all 50 actions.",
            "T2": "Actual initial wrapper reset, dm_control reset and initialization exactly once; no pending or internal resets.",
            "T3": "Monotone time, dt=.02, target fixed, finite states; every saved state agrees with native CPU full-two-microstep replay.",
            "T4": "Original non-wrapped absolute-joint threshold .05; independent predicate, both step labels and any/block/final semantics agree.",
            "replay_state_absolute_tolerance": STATE_ATOL, "replay_state_relative_tolerance": 0,
            "success_predicate_tolerance": "none: strict < 0.05"},
        "gates": gates, "case_stream_results": rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path("/workspace/d1/step4/resume_03_reacher"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--groups", nargs="+", help="Optional groups (space- or comma-separated) for a partial smoke evaluation")
    a = p.parse_args()
    groups = tuple(x for entry in a.groups for x in entry.split(",")) if a.groups else GROUPS
    if not groups or len(set(groups)) != len(groups) or set(groups) - set(GROUPS):
        p.error("Invalid or duplicate group")
    result = evaluate(a.root, groups)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "gates": result["gates"], "output": str(a.output)}, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
