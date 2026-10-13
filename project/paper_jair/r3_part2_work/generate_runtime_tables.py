"""Build two compact Reacher audit tables from returned machine-readable evidence.

Writes only table_reacher_runtime_checks.tex and
table_reacher_correction_timeline.tex. A formal-start row is included only if a
returned FORMAL_STAGE_1_STARTED.json is available (or passed with --started-json).
No inferred start/completion/stop timestamps or hashes are emitted.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_EXPERIMENT = HERE / "returns/PREFORMAL_VERIFIED/experiment"
DEFAULT_TABLES = HERE.parent / "revision3_part2/tables"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value):
    return f"{int(value):,}"


def percent(numerator, denominator):
    return f"{100 * numerator / denominator:.2f}".rstrip("0").rstrip(".") + r"\%"


def tex_status(value):
    if value not in ("PASS", "FAIL", "BLOCKED"):
        raise ValueError("Unexpected evidence status: " + str(value))
    return value


def utc_cell(value):
    stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    return r"\shortstack[l]{" + stamp.strftime("%Y-%m-%d") + r"\\" + stamp.strftime("%H:%M:%S.%f") + "}"


def runtime_table(experiment):
    gate = read(experiment / "TECH_GATE_FINAL_T1_T4.json")
    runtime = read(experiment / "runtime_checks_final.json")
    if gate.get("status") != "PASS" or runtime.get("status") != "PASS":
        raise ValueError("These final evidence tables require actually passed numerical and runtime checks")
    trajectories = gate["case_stream_results"]
    n = len(trajectories)
    prior = sum(r["T1"]["actions_before_success_compared"] for r in trajectories)
    inclusive = sum(r["T1"]["actions_including_first_success_compared"] for r in trajectories)
    resets = sum(r["T2"]["wrapper_reset_count"] for r in trajectories)
    dmresets = sum(r["T2"]["dm_control_reset_count"] for r in trajectories)
    internal = sum(r["T2"]["internal_reset_event_count"] for r in trajectories)
    microsteps = sum(r["T3"]["microsteps"] for r in trajectories)
    steps = sum(r["T3"]["environment_steps"] for r in trajectories)
    predicate_count = sum(r["T4"]["predicate_comparisons"] for r in trajectories)
    predicate_errors = sum(r["T4"]["predicate_mismatches"] for r in trajectories)
    label_diff = sum(r["T4"]["steps_where_two_labels_differ"] for r in trajectories)
    maximum = max(v for r in trajectories for v in r["T3"]["cpu_replay"]["max_abs_by_field"].values())
    tolerance = gate["rules"]["replay_state_absolute_tolerance"]
    micro_dt = min(r["T3"]["min_microstep_dt"] for r in trajectories)
    assert prior == gate["gates"]["T1"]["totals"]["actions_before_success_compared"]
    assert inclusive == gate["gates"]["T1"]["totals"]["actions_including_first_success_compared"]
    assert label_diff == gate["gates"]["T4"]["totals"]["steps_where_two_labels_differ"]
    gates = gate["gates"]
    for key in ("T1", "T2", "T3", "T4"):
        assert sum(r[key]["status"] == "PASS" for r in trajectories) == gates[key]["case_stream_counts"]["PASS"]
    tolerance_tex = (r"$10^{" + str(int(f"{tolerance:.0e}".split("e")[1])) + "}$")
    rows = [
        ("T1: action prefix",
         f"{number(prior)} actions before first success and {number(inclusive)} including its action are bitwise identical to the sealed original references ({n}/{n} trajectories).",
         tex_status(gates["T1"]["status"])),
        ("T2: reset counts",
         f"{number(resets)} wrapper and {number(dmresets)} dm-control resets: one initial reset per trajectory; {internal} internal resets.",
         tex_status(gates["T2"]["status"])),
        ("T3: physical replay",
         f"{number(steps)} environment steps / {number(microsteps)} microsteps; monotone time, {micro_dt:.2f}~s per microstep, fixed target. Independent CPU replay maximum state error {maximum:g} (absolute tolerance {tolerance_tex}).",
         tex_status(gates["T3"]["status"])),
        ("T4: success labels",
         f"{number(predicate_count)} predicates, {predicate_errors} mismatches. Both step-label sequences and any/block/final outputs agree with their definitions; the two step labels differ at {label_diff} environment steps.",
         tex_status(gates["T4"]["status"])),
    ]
    cont = runtime["four_environment_continuation"]
    cont_pass = all(row["pass"] for row in cont.values())
    rows.append(("Four-environment check",
        "Original Reacher resets after success; corrected Reacher, PushT and TwoRoom continue with the recorded state continuity checks. Cube continues with increasing physical time.",
        "PASS" if cont_pass else "FAIL"))
    old = runtime["reacher_replay"]["records"][0]
    before = old["segments"]["through_first_success"]
    after = old["segments"]["after_first_success"]
    original_matches = before["original_matches"] + after["original_matches"]
    rows.append(("Held-out replay",
        f"Original semantics reproduce {original_matches}/{old['n_actions']} labels ({percent(original_matches, old['n_actions'])}). Corrected semantics agree through first success ({before['patched_matches']}/{before['n_steps']}); thereafter {after['patched_matches']}/{after['n_steps']} agree and {old['post_success_disagreement']} differ.",
        "PASS" if runtime["reacher_replay"]["pass"] else "FAIL"))
    output = [
        "% Generated by r3_part2_work/generate_runtime_tables.py from returned JSON evidence.",
        r"\begin{table}[t]", r"\centering", r"\small",
        r"\caption{Reacher correction checks on the final recording code: " + str(n)
        + r" TECH trajectories, plus four-environment continuation and one original held-out trajectory replay. The two step labels are within-step any-success and step-end success.}",
        r"\label{tab:reacher-runtime}",
        r"\begin{tabular}{@{}p{0.16\linewidth}p{0.67\linewidth}p{0.08\linewidth}@{}}",
        r"\toprule", r"Check & Numerical evidence & Result \\", r"\midrule",
    ]
    output.extend(" & ".join(row) + r" \\" for row in rows)
    output.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(output) + "\n"


def timeline_table(experiment, local_return_path, launch_path, started_path):
    records = [
        ("Final numerical gates", experiment / "TECH_GATE_FINAL_T1_T4.json", "utc"),
        ("Final correction registration", experiment / "REVISION_3_REACHER_CORRECTION_REGISTRATION.json", "registration_utc"),
        ("Verified local return", local_return_path, "utc"),
        ("Formal launch authorization", launch_path, "created_utc"),
    ]
    if started_path is not None:
        start = read(started_path)
        if start.get("stage") != 1:
            raise ValueError("Formal start must be the actual stage-1 STARTED receipt")
        if start.get("launch_receipt_sha256") != sha(launch_path):
            raise ValueError("Formal start does not bind this final launch receipt")
        records.append(("Corrected formal stage 1 started", started_path, "utc"))
    rows = []
    last = None
    for label, path, field in records:
        obj = read(path)
        stamp = dt.datetime.fromisoformat(obj[field].replace("Z", "+00:00"))
        if last is not None and stamp < last:
            raise ValueError("Correction timeline is not chronologically ordered")
        last = stamp
        rows.append((label, utc_cell(obj[field]), r"\texttt{" + sha(path)[:12] + "}"))
    output = [
        "% Generated by r3_part2_work/generate_runtime_tables.py; SHA prefixes identify exact receipt files.",
        r"\begin{table}[t]", r"\centering", r"\small",
        r"\caption{Audit timeline for the Reacher correction. Times are UTC; hashes are the first 12 characters of each record's SHA--256. The launch authorization follows numerical gates, the sealed correction registration and verified local return.}",
        r"\label{tab:reacher-correction-timeline}",
        r"\begin{tabular}{@{}p{0.34\linewidth}p{0.34\linewidth}p{0.25\linewidth}@{}}",
        r"\toprule", r"Event & UTC & SHA--256 \\", r"\midrule",
    ]
    output.extend(" & ".join(row) + r" \\" for row in rows)
    output.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(output) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    p.add_argument("--local-return-json", type=Path, default=HERE / "returns/PREFORMAL_LOCAL_RETURN.json")
    p.add_argument("--launch-json", type=Path, default=HERE / "returns/FORMAL_LAUNCH_RECEIPT.json")
    p.add_argument("--started-json", type=Path)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_TABLES)
    a = p.parse_args()
    launch = read(a.launch_json)
    for role, filename in (("correction_registration", "REVISION_3_REACHER_CORRECTION_REGISTRATION.json"),
                           ("technical_gates", "TECH_GATE_FINAL_T1_T4.json"),
                           ("runtime_checks", "runtime_checks_final.json")):
        if sha(a.experiment / filename) != launch["verified_evidence"][role]["sha256"]:
            raise ValueError("Evidence does not match final launch receipt: " + role)
    if sha(a.local_return_json) != launch["verified_evidence"]["local_return"]["sha256"]:
        raise ValueError("Local verification receipt mismatch")
    if a.started_json is None:
        candidates = sorted((HERE / "returns").glob("*/experiment/FORMAL_STAGE_1_STARTED.json"))
        if candidates:
            unique = {sha(path) for path in candidates}
            if len(unique) != 1:
                raise ValueError("Conflicting returned stage-1 start receipts; pass the intended --started-json")
            a.started_json = candidates[0]
    a.output_dir.mkdir(parents=True, exist_ok=True)
    first = a.output_dir / "table_reacher_runtime_checks.tex"
    second = a.output_dir / "table_reacher_correction_timeline.tex"
    first.write_text(runtime_table(a.experiment))
    second.write_text(timeline_table(a.experiment, a.local_return_json, a.launch_json, a.started_json))
    print(json.dumps({"generated": [str(first), str(second)],
                      "formal_start_included": a.started_json is not None}, indent=2))


if __name__ == "__main__":
    main()
