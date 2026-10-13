#!/usr/bin/env python3
"""Build corrected-paper assets in a NEW directory; never edit the manuscript.

Example (only after all formal outputs are returned and analyzed):
  python update_paper_corrected.py --analysis r3_part2_work/analysis_final \
    --output r3_part2_work/paper_assets_final

Reads the correction analyst's documented CSV interface. Reacher is replaced
as a whole; other tasks' main rates/contrasts remain sealed Step-4 values.
Descriptive terminal-window metrics are recomputed per physical trajectory for
all tasks to avoid the old seed-union/seed-majority and empty-post-hit bugs.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

WORK = Path(__file__).resolve().parent
PAPER = WORK.parent
S4 = PAPER.parent / "d1_execution/step4/resume_01"
TASKS = ["reacher", "pusht", "tworoom", "cube"]
TASK = dict(zip(TASKS, ["Reacher", "PushT", "TwoRoom", "Cube"]))
MODELS = ["LeWM_h1", "LeWM_h3", "M01_h1", "M03_h1", "M07_h1"]
MODEL = dict(zip(MODELS, ["LeWM one-frame", "LeWM three-frame", "Fast-LeWM", "AP", "AD-WM"]))
STREAMS = ["R3_ORIGINAL", "R4_ALT_CEM_1", "R4_ALT_CEM_2"]
DEFS = ["any", "block", "final"]
COLORS = {"any": "#286090", "block": "#d18f00", "final": "#2b7a4b"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def esc(value):
    return str(value).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def number(value, signed=False, digits=1):
    if value is None or not np.isfinite(float(value)):
        return "--"
    return format(float(value), ("+" if signed else "") + f".{digits}f")


def ci(row):
    return f"{number(row['delta_pp'], True)} [{number(row['ci95_low_pp'], True)}, {number(row['ci95_high_pp'], True)}]"


def one(frame, **filters):
    z = frame
    for key, value in filters.items():
        z = z[z[key] == value]
    require(len(z) == 1, f"Expected one row for {filters}; found {len(z)}")
    return z.iloc[0]


def terminal_metrics(any_labels, end_labels):
    """Metrics first, seed averaging second; final-step-only hits are ineligible."""
    hit = np.flatnonzero(any_labels)
    first = int(hit[0]) if len(hit) else None
    eligible = first is not None and first < 49
    later = end_labels[first + 1:] if eligible else np.empty(0, bool)
    return {
        'any': float(any_labels.any()),
        'block': float(end_labels[4::5].any()),
        'final': float(end_labels[-1]),
        **{f"last{k}_occupancy": float(end_labels[-k:].mean()) for k in (5, 10)},
        **{f"last{k}_all": float(end_labels[-k:].all()) for k in (5, 10)},
        "hit_eligible_for_later_step": float(eligible),
        "hit_and_later_step_exit": float(eligible and (~later).any()),
        "hit_and_later_outside_fraction": float((~later).mean()) if eligible else 0.0,
    }


def write_table(path, caption, label, columns, header, rows, note=None):
    lines = [r"\begin{table*}[t]\centering", r"\caption{" + caption + "}",
             r"\label{" + label + "}", r"\small", r"\begin{tabular}{" + columns + "}",
             r"\toprule", " & ".join(header) + r" \\", r"\midrule"]
    lines += [" & ".join(str(x) for x in row) + r" \\" for row in rows]
    lines += [r"\bottomrule", r"\end{tabular}"]
    if note:
        lines += [r"\par\smallskip\begin{minipage}{0.98\textwidth}\scriptsize " + note + r"\end{minipage}"]
    lines += [r"\end{table*}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analysis", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--old-formal-root", type=Path, default=S4 / "remote_sync/FINAL_RESULTS/formal")
    args = ap.parse_args()
    require(not args.output.exists(), "Choose a new output directory; overwriting is forbidden")
    require(args.output.resolve().is_relative_to(WORK), "Output must be below r3_part2_work")
    inputs, notes = {}, []
    sealed = {r["path"]: r["sha256"] for r in json.loads((S4 / "SEAL.json").read_text())["files"]}
    analysis_manifest = json.loads((args.analysis / "ANALYSIS_MANIFEST.json").read_text())
    require(analysis_manifest.get("status") == "COMPLETE", "Corrected analysis is incomplete")
    require(analysis_manifest.get("corrected_trajectories") == 2700, "Correction grid is incomplete")

    def track(path, original=False, analyzed=False):
        path = Path(path).resolve()
        require(path.is_file(), f"Missing input {path}")
        digest = sha(path)
        if original:
            rel = path.relative_to(S4).as_posix()
            require(sealed.get(rel) == digest, f"Sealed source hash mismatch: {rel}")
        if analyzed:
            require(analysis_manifest["outputs"].get(path.name) == digest, f"Analyzed source hash mismatch: {path.name}")
        inputs[str(path)] = digest
        return path

    def read_csv(path, **flags):
        return pd.read_csv(track(path, **flags), encoding="utf-8-sig")

    track(args.analysis / "ANALYSIS_MANIFEST.json")
    track(S4 / "SEAL.json")
    track(Path(__file__))
    datasets = {}
    for name, keys in [("ABSOLUTE_RATES", ["task", "model", "iterations", "definition"]),
                       ("CONTRASTS", ["analysis", "task", "contrast", "definition", "cohort", "streams"]),
                       ("KENDALL_TAU", ["task", "definitions"])]:
        old = read_csv(S4 / "results" / (name + ".csv"), original=True)
        new = read_csv(args.analysis / (name + ".csv"), analyzed=True)
        require(set(new.task) == {"reacher"}, f"Unexpected new task in {name}")
        if name == "CONTRASTS" and "iterations" in new.columns:
            keys = keys + ["iterations"]
        require(not new.duplicated(keys).any(), f"Duplicate corrected keys in {name}")
        kept = old[old.task != "reacher"].copy()
        merged = pd.concat([kept, new], ignore_index=True, sort=False)
        # The retained rows come directly from the sealed table, not a fresh
        # analysis of other tasks or a different bootstrap implementation.
        pd.testing.assert_frame_equal(merged[merged.task != "reacher"][old.columns].reset_index(drop=True),
                                      kept.reset_index(drop=True), check_dtype=False)
        datasets[name] = merged
    rates, contrasts, taus = (datasets[x] for x in ["ABSOLUTE_RATES", "CONTRASTS", "KENDALL_TAU"])
    corrected_occ = read_csv(args.analysis / "OCCUPANCY.csv", analyzed=True)
    corrected_occ = corrected_occ[(corrected_occ.version == "corrected") & (corrected_occ.iterations == 30)].copy()
    occupancy_rows = [dict(task="reacher", model=r.model, env_step=int(r.env_step), occupancy_pct=float(r.delta_pp))
                      for r in corrected_occ.itertuples()]
    specs = json.loads(track(S4 / "CONDITION_SPECS.json", original=True).read_text())
    cases = json.loads(track(S4 / "cases/HELDOUT_CASES_V2.json", original=True).read_text())["tasks"]
    terminal_rows, terminal_raw = [], []

    # Reacher descriptive metrics are already computed seed-first by the
    # correction analysis; conditional ratios include their actual denominator.
    for model in MODELS:
        row = dict(task="reacher", model=model)
        for metric in ["last5_occupancy", "last10_occupancy", "last5_all", "last10_all",
                       "exit_after_first_hit", "outside_fraction_after_first_hit"]:
            r = one(rates, task="reacher", model=model, iterations=30, definition=metric)
            row[metric + "_pct"] = float(r.rate_pct) if pd.notna(r.rate_pct) else None
            if metric == "exit_after_first_hit":
                row["eligible_trajectories"] = int(r.eligible_trajectories)
        terminal_rows.append(row)

    # Non-Reacher trajectories remain read-only. Computing nonlinear metrics
    # separately on each checkpoint fixes the old descriptive A1 aggregation.
    for task in TASKS[1:]:
        ids = [c["case_id"] for c in cases[task]]
        require(len(ids) == len(set(ids)) == 100, f"Unexpected case set for {task}")
        for model in MODELS:
            source_model, history = model.rsplit("_h", 1)
            cids = [cid for cid, s in specs.items() if s["task"] == task and s["model"] == source_model
                    and int(s["history"]) == int(history) and int(s["iterations"]) == 30]
            require(len(cids) == (3 if source_model == "M07" else 1), f"Wrong seed count for {task}/{model}")
            metric_values, trajectories = [], []
            for cid in cids:
                s = specs[cid]
                for case in ids:
                    for stream in STREAMS:
                        if source_model == "LeWM":
                            p = args.old_formal_root / cid / case / stream / "result.json"
                        else:
                            p = args.old_formal_root / cid / stream / (case + ".json")
                        result = json.loads(track(p, original=True).read_text())
                        require(result.get("status") == "COMPLETE" and result.get("executed_raw_steps") == 50,
                                f"Incomplete old trajectory {p}")
                        require(result.get("case_id") == case and result.get("stream") == stream,
                                f"Identity mismatch {p}")
                        if source_model == "LeWM":
                            with np.load(track(p.with_name("trajectory.npz"), original=True), allow_pickle=False) as z:
                                labels = np.asarray(z["successes"], bool)
                        else:
                            labels = np.asarray([x["success"] for x in result["steps"]], bool)
                        require(labels.shape == (50,), f"Wrong old label shape {p}")
                        m = terminal_metrics(labels, labels)
                        terminal_raw.append(dict(task=task, model=model, condition_id=cid, train_seed=s["train_seed"],
                                                 case_id=case, stream=stream, **m))
                        metric_values.append(m)
                        trajectories.append(labels.astype(float))
            q = pd.DataFrame(metric_values)
            denom = float(q.hit_eligible_for_later_step.sum())
            row = dict(task=task, model=model, eligible_trajectories=int(denom))
            for metric in ["last5_occupancy", "last10_occupancy", "last5_all", "last10_all"]:
                row[metric + "_pct"] = 100 * float(q[metric].mean())
            row["exit_after_first_hit_pct"] = None if denom == 0 else 100 * float(q.hit_and_later_step_exit.sum() / denom)
            row["outside_fraction_after_first_hit_pct"] = None if denom == 0 else 100 * float(q.hit_and_later_outside_fraction.sum() / denom)
            terminal_rows.append(row)
            for i, val in enumerate(np.mean(trajectories, axis=0), 1):
                occupancy_rows.append(dict(task=task, model=model, env_step=i, occupancy_pct=float(val * 100)))

    oldnew = read_csv(args.analysis / "OLD_VS_CORRECTED.csv", analyzed=True)
    labels = read_csv(args.analysis / "LABEL_SEMANTICS_COMPARISON.csv", analyzed=True)
    paired = read_csv(args.analysis / "AP_LEWM_PAIRED.csv", analyzed=True)
    old_rates = read_csv(args.analysis / "ABSOLUTE_RATES_OLD.csv", analyzed=True)
    old_taus = read_csv(args.analysis / "KENDALL_TAU_OLD.csv", analyzed=True)
    seed_streams = read_csv(args.analysis / "PER_STREAM_AND_CHECKPOINT.csv", analyzed=True)
    old_raw = read_csv(S4 / "evidence/stage2_statistics/RAW_TRAJECTORIES.csv", original=True)
    prereg_text = track(PAPER.parent / "d1_execution/prereg/PREREG_D1_V2_FOLLOWUP.md").read_text()
    require(all(x in prereg_text for x in ["≥ +10 pp", "point estimates within ±2 pp", "lower bound > −5 pp", "point estimate < 0", "lower bounds > 0"]),
            "V2 prediction rules do not match this generator; inspect the preregistration")
    post = read_csv(PAPER.parent / "d1_execution/step3/results/POSTHOC_CONTRASTS.csv")
    noise = json.loads(track(PAPER.parent / "d1_execution/step2/resume_03/results/H4_NOISE.json").read_text())
    # New directory is created only after all required sources were verified.
    args.output.mkdir(parents=True)
    for name in ["tables", "figures", "a3_results", "data"]:
        (args.output / name).mkdir()
    table_dir, fig_dir, macro_dir, data_dir = [args.output / x for x in ["tables", "figures", "a3_results", "data"]]
    for name, data in datasets.items():
        data.to_csv(data_dir / (name + ".csv"), index=False)
    occupancy = pd.DataFrame(occupancy_rows)
    terminal = pd.DataFrame(terminal_rows)
    occupancy.to_csv(data_dir / "OCCUPANCY_ALL_TASKS.csv", index=False)
    terminal.to_csv(data_dir / "TERMINAL_WINDOWS_ALL_TASKS.csv", index=False)
    pd.DataFrame(terminal_raw).to_csv(data_dir / "TERMINAL_RAW_NONREACHER.csv", index=False)
    notes += ["Non-Reacher main rates/contrasts are identical to sealed Step-4 rows.",
              "All-task terminal-window summaries use per-trajectory metrics before seed averaging; hits only at step 50 have no later-step window and are excluded from the conditional exit denominator."]

    def rate(task, model, definition="any", iterations=30):
        return one(rates, task=task, model=model, iterations=iterations, definition=definition)

    extra_contrasts = []
    stats_path = track(PAPER.parent / 'd1_execution/step1/upload/code/tools/statistics_d1.py')
    stats_spec = importlib.util.spec_from_file_location('sealed_paper_statistics', stats_path)
    frozen_stats = importlib.util.module_from_spec(stats_spec)
    stats_spec.loader.exec_module(frozen_stats)
    terminal_frame = pd.DataFrame(terminal_raw)

    def contrast(task, name, definition="any", analysis="main"):
        filters=dict(task=task, contrast=name, definition=definition, analysis=analysis,
                     cohort="HELDOUT100", streams="ABC")
        selected=contrasts
        for key,value in filters.items():selected=selected[selected[key]==value]
        if len(selected)==1:return selected.iloc[0]
        # Sealed Step-4 summary has only any-step main contrasts. Its complete
        # immutable trajectories support the missing plotting intervals.
        require(len(selected)==0 and task!='reacher' and analysis=='main'
                and definition in DEFS and name.endswith(' - LeWM_h1'),
                f'Unexpected missing/duplicate contrast: {filters}')
        for row in extra_contrasts:
            if all(row[k]==v for k,v in filters.items()):return pd.Series(row)
        model=name.removesuffix(' - LeWM_h1');require(model in MODELS,'Unknown contrast model')
        vectors=[]
        for m in (model,'LeWM_h1'):
            q=terminal_frame[(terminal_frame.task==task)&(terminal_frame.model==m)]
            counts=q.groupby('case_id').size()
            require(len(counts)==100 and (counts==(9 if m=='M07_h1' else 3)).all(),
                    f'Incomplete paired descriptive data: {task}/{m}')
            vectors.append(q.groupby('case_id')[definition].mean().sort_index())
        require(vectors[0].index.equals(vectors[1].index),'Unpaired descriptive case identities')
        row=dict(filters,**frozen_stats.paired(vectors[0].to_numpy(),vectors[1].to_numpy()))
        row['source']='Supplementary paired contrast from sealed per-trajectory labels; original summary rows unchanged'
        row['bootstrap_seed']=20261011;row['bootstrap_replicates']=5000
        extra_contrasts.append(row)
        return pd.Series(row)

    # Fresh macros are emitted as full replacement files inside --output;
    # original manuscript sources and their old generated files are untouched.
    text = track(PAPER / "a3_results/numbers.tex").read_text()
    macro_changes = {}

    def put(name, value):
        nonlocal text
        line = rf"\newcommand{{\{name}}}{{{value}}}"
        pattern = rf"\\newcommand\{{\\{name}\}}\{{[^}}]*\}}"
        if re.search(pattern, text):
            text = re.sub(pattern, lambda _m: line, text)
        else:
            text += "\n" + line + "\n"
        macro_changes[name] = str(value)

    for macro, model in [("ReacherLeWMOne", "LeWM_h1"), ("ReacherAP", "M03_h1")]:
        for definition in DEFS:
            put(macro + definition.title(), number(rate("reacher", model, definition).rate_pct))
    h = contrast("reacher", "LeWM_h3 - LeWM_h1")
    for name in ["ReacherHistoryDelta", "ReacherHistoryDeltaRevision"]:
        put(name, number(h.delta_pp, True))
    put("ReacherHistoryCI", ci(h))
    put("ReacherHistoryCIRevision", f"[{number(h.ci95_low_pp, True)}, {number(h.ci95_high_pp, True)}]")
    put("ReacherHistoryLow", number(h.ci95_low_pp, True))
    put("ReacherHistoryHigh", number(h.ci95_high_pp, True))
    put("ReacherHistoryCIOnly", f"[{number(h.ci95_low_pp, True)}, {number(h.ci95_high_pp, True)}]")
    for suffix, model in [("MOne", "M01_h1"), ("MSeven", "M07_h1"), ("MThree", "M03_h1")]:
        put("Reacher" + suffix + "Delta", ci(contrast("reacher", "LeWM_h3 - " + model, analysis="C2")))
    for name, model in [("ReacherThreeVsFast", "M01_h1"), ("ReacherThreeVsAD", "M07_h1"), ("ReacherAPVsThree", "M03_h1")]:
        delta=contrast("reacher", "LeWM_h3 - " + model, analysis="C2").delta_pp
        put(name, number(-delta if name=="ReacherAPVsThree" else delta, True))
    for definition in ["any", "final"]:
        delta = contrast("reacher", "M03_h1 - LeWM_h1", definition).delta_pp
        for name in ["APReacher" + definition.title() + "Delta", "ReacherAPLeWM" + definition.title() + "Delta"]:
            put(name, number(delta, True))
    for r in taus[taus.task == "reacher"].itertuples():
        suffix = "".join(x.title() for x in r.definitions.split("/"))
        put("TauReacher" + suffix, number(r.kendall_tau_b, digits=2))
        put("ReacherTau" + suffix, number(r.kendall_tau_b, digits=2))
    cem = contrasts[contrasts.analysis == "D4_iterations"]
    put("CEMMaxDelta", number(cem.delta_pp.abs().max()))
    q = contrast("reacher", "LeWM_h1 CEM10 - CEM30", analysis="D4_iterations")
    for suffix, field in [("Delta", "delta_pp"), ("Low", "ci95_low_pp"), ("High", "ci95_high_pp")]:
        put("DFourReacherHOneAny" + suffix, number(q[field], True))
    (macro_dir / "numbers.tex").write_text(text)
    pair_text = track(PAPER / "a3_results/revision3_pair_stats.tex").read_text()
    for suffix, definition in [("Any", "any"), ("Final", "final"), ("Change", "final_minus_any_difference_in_differences")]:
        r = one(paired, version="corrected", definition=definition)
        name = "APLeWMReacher" + suffix + "CI"
        line = rf"\newcommand{{\{name}}}{{{ci(r)}}}"
        pattern = rf"\\newcommand\{{\\{name}\}}\{{[^}}]*\}}"
        require(re.search(pattern, pair_text), f"Missing expected macro {name}")
        pair_text = re.sub(pattern, lambda _m: line, pair_text)
        macro_changes[name] = ci(r)
    (macro_dir / "revision3_pair_stats.tex").write_text(pair_text)

    # Core tables: corrected endpoint semantics in every Reacher main row.
    main_rows = [[TASK[t], MODEL[m]] + [number(rate(t, m, d).rate_pct) for d in DEFS] for t in TASKS for m in MODELS]
    for filename, label, caption in [
        ("table_success_rates_revision.tex", "tab:success", "Three success labels on the held-out trajectories. Reacher uses corrected continuous physics; block and final labels use environment-step-end states."),
        ("table_complete_results_revision.tex", "tab:complete", "Complete held-out rates used for the main figures; AD-WM averages trajectory metrics across its three public checkpoints.")]:
        write_table(table_dir / filename, caption, label, "llrrr", ["Task", "Configuration", "Any-step (\\%)", "Block (\\%)", "Final (\\%)"], main_rows)
    rank_rows = [[TASK[t], pair.replace("/", " / "), number(one(taus, task=t, definitions=pair).kendall_tau_b, digits=2)]
                 for t in TASKS for pair in ["any/block", "any/final", "block/final"]]
    write_table(table_dir / "table_rankings_revision.tex", "Kendall rank correlations between success definitions, with corrected Reacher continuation.", "tab:rankings", "llr", ["Task", "Definitions", r"$\tau_b$"], rank_rows)
    prediction_rows, prediction_records = [], []

    def prediction(group, description, rule, q, passed):
        verdict = "supported" if passed else "not supported"
        prediction_rows.append([group, description, rule, ci(q), verdict])
        prediction_records.append(dict(prediction=group, subcondition=description, criterion=rule,
                                       estimate_pp=float(q.delta_pp), ci95_low_pp=float(q.ci95_low_pp),
                                       ci95_high_pp=float(q.ci95_high_pp), passed=bool(passed)))

    for t in TASKS:
        q = contrast(t, "LeWM_h3 - LeWM_h1")
        if t == "reacher":
            rule = r"$\widehat{\Delta}\geq+10$ pp and CI lower bound $>0$"
            passed = q.delta_pp >= 10 and q.ci95_low_pp > 0
        else:
            rule = r"$|\widehat{\Delta}|\leq2$ pp (point-estimate rule)"
            passed = abs(q.delta_pp) <= 2
        prediction("P1", TASK[t] + r" (3-frame $-$ 1-frame)", rule, q, passed)
    for model in MODELS[2:]:
        q = contrast("reacher", "LeWM_h3 - " + model, analysis="C2")
        if model == "M03_h1":
            rule = r"$\widehat{\Delta}<0$ pp (point-estimate rule)"
            passed = q.delta_pp < 0
        else:
            rule = r"$\widehat{\Delta}\geq0$ pp and CI lower bound $>-5$ pp"
            passed = q.delta_pp >= 0 and q.ci95_low_pp > -5
        prediction("P2", "Reacher: LeWM 3-frame $-$ " + MODEL[model], rule, q, passed)
    for t in ["tworoom", "cube"]:
        for model in ["M03_h1", "M07_h1"]:
            q = contrast(t, model + " - LeWM_h1")
            prediction("P3", TASK[t] + ": " + MODEL[model] + r" $-$ LeWM 1-frame",
                       r"CI lower bound $>0$ pp (gain rule)", q, q.ci95_low_pp > 0)
    require(len(prediction_rows) == 11, "Expected 11 preregistered prediction subconditions")
    write_table(table_dir / "table_predictions_revision.tex",
                "Preregistered prediction checks on the held-out set. Each row is an independent subcondition; estimates are paired percentage-point differences [95\\% case-bootstrap interval]. Reacher uses corrected trajectories, and every verdict is evaluated from the registered rule.",
                "tab:predictions", "cp{3.4cm}p{4.2cm}p{2.5cm}p{1.7cm}",
                ["Prediction", "Subcondition", "Preregistered rule", "Estimate [95\\% CI]", "Result"], prediction_rows)
    pd.DataFrame(prediction_records).to_csv(data_dir / "PREDICTIONS.csv", index=False)

    adwm_rows, adwm_records = [], []
    for t in TASKS:
        for seed in ["3072", "4096", "6144"]:
            for stream in STREAMS:
                if t == "reacher":
                    z = seed_streams[(seed_streams.version == "corrected") & (seed_streams.model == "M07") &
                                     (seed_streams.history == 1) & (seed_streams.iterations == 30) &
                                     (seed_streams.train_seed.astype(str) == seed) & (seed_streams.stream == stream)]
                    rs = [one(z, metric=d) for d in DEFS]
                    require(all(int(r.n_cases) == 100 for r in rs), "Incomplete corrected AD-WM checkpoint-stream")
                    n, values = 100, [float(r.delta_pp) for r in rs]
                else:
                    z = old_raw[(old_raw.task == t) & (old_raw.model == "M07") & (old_raw.history == 1) &
                                (old_raw.iterations == 30) & (old_raw.train_seed.astype(str) == seed) & (old_raw.stream == stream)]
                    require(len(z) == z.case_id.nunique() == 100 and (z.status == "COMPLETE").all(),
                            f"Incomplete sealed AD-WM {t}/{seed}/{stream}")
                    n, values = len(z), [float(z["success_" + d].mean() * 100) for d in DEFS]
                adwm_rows.append([TASK[t], seed, esc(stream), str(n)] + [number(v) for v in values])
                adwm_records.append(dict(task=t, train_seed=seed, stream=stream, n_cases=n,
                                         **dict(zip(["any_pct", "block_pct", "final_pct"], values))))
    write_table(table_dir / "table_adwm_stream_revision.tex", "AD-WM checkpoint and planner-stream results on 100 held-out cases per row. Reacher is replaced by the corrected run; all other task rows retain the sealed Step-4 results.",
                "tab:adwm-stream", "lllrrrr", ["Task", "Checkpoint", "Planner stream", "Cases", "Any-step (\\%)", "Block (\\%)", "Final (\\%)"], adwm_rows)
    pd.DataFrame(adwm_records).to_csv(data_dir / "ADWM_CHECKPOINT_STREAMS.csv", index=False)
    correction_rows = []
    for m in MODELS:
        row = [MODEL[m]]
        for d in DEFS:
            q = one(oldnew, model=m, iterations=30, metric=d)
            row += [number(q.old_rate_pct), number(q.corrected_rate_pct)]
        correction_rows.append(row)
    write_table(table_dir / "table_reacher_termination_correction.tex",
                "Reacher before and after the termination correction (percent). Old trajectories retain the implicit success reset; corrected trajectories continue without an internal reset. Block and final checks also change from the legacy success flag to the recorded environment-step-end predicate.",
                "tab:reacher-correction", "lrrrrrr", ["Configuration", "Old any", "New any", "Old block", "New block", "Old final", "New final"], correction_rows)
    corr_contrast_rows = []
    for d in ["any", "final", "final_minus_any_difference_in_differences"]:
        corr_contrast_rows.append(["AP minus LeWM: " + ("final minus any change" if d.startswith("final_minus") else d),
                                   ci(one(paired, version="old", definition=d)), ci(one(paired, version="corrected", definition=d))])
    for pair in ["any/block", "any/final", "block/final"]:
        corr_contrast_rows.append([r"Kendall $\tau_b$: " + pair,
                                   number(one(old_taus, task="reacher", definitions=pair).kendall_tau_b, digits=2),
                                   number(one(taus, task="reacher", definitions=pair).kendall_tau_b, digits=2)])
    write_table(table_dir / "table_reacher_termination_contrasts.tex", "Changes in the AP--LeWM contrast and five-configuration ranking after correction. Contrast entries are percentage points [95\\% paired case-bootstrap interval].", "tab:reacher-correction-contrasts", "lrr", ["Statistic", "Old reset semantics", "Corrected continuous semantics"], corr_contrast_rows)
    label_rows = []
    for m in MODELS:
        for d in DEFS:
            q = one(labels, model=m, iterations=30, metric=d)
            label_rows.append([MODEL[m], d, number(q.or_rate_pct), number(q.end_rate_pct), ci(q)])
    write_table(table_dir / "table_reacher_microstep_end.tex", "Within corrected Reacher trajectories, labels from either microstep (OR) versus labels at the second microstep (END). Any-step success uses OR; block and final success use END. Differences are END minus OR in percentage points.", "tab:reacher-microstep-end", "llrrr", ["Configuration", "Metric", "OR (\\%)", "END (\\%)", "Difference [95\\% CI]"], label_rows)
    timing_drops = np.array([rate(t, m, "any").rate_pct - rate(t, m, "final").rate_pct for t in TASKS for m in MODELS], float)
    endpoint_changes = oldnew[(oldnew.iterations == 30) & oldnew.model.isin(MODELS) & oldnew.metric.isin(["block", "final"])].delta_pp.to_numpy(float)
    label_changes = labels[(labels.iterations == 30) & labels.model.isin(MODELS) & labels.metric.isin(["block", "final"])].delta_pp.to_numpy(float)
    replans = post[(post.cohort == "mixed200") & (post.streams == "ABC") & (post.contrast == "replan1 - P0")].delta_pp.to_numpy(float)
    library = post[(post.cohort == "mixed200") & (post.streams == "ABC") & (post.contrast == "old - P0")].delta_pp.to_numpy(float)
    widths = [float(next(r["halfwidth_median_pp"] for r in noise[t]["registered_function"]["widths"]
                        if r["n_cases"] == 100 and r["n_streams"] == 3)) for t in ["reacher", "pusht"]]
    require(all(len(a) and np.isfinite(a).all() for a in [timing_drops, endpoint_changes, label_changes, replans, library]), "Missing reporting-scale inputs")

    def span(values, signed=False):
        return number(np.min(values), signed) + " to " + number(np.max(values), signed) + " pp"

    reporting_rows = [
        ["Success test and check times", "Any-step minus final-step rates across the 20 held-out task/configuration cells", span(timing_drops)],
        ["History construction", "Held-out Reacher three-frame minus one-frame, any-step", number(h.delta_pp, True) + " pp"],
        ["Termination and reset semantics", "New minus old Reacher block/final rates, five configurations; both continuity and endpoint-label corrections", span(endpoint_changes, True)],
        ["Microsteps versus step end", "END minus OR block/final rates on identical corrected Reacher trajectories", span(label_changes, True)],
        ["Planner budget and replanning", "Largest absolute native-replanning effect in the sealed mixed-case factor analysis", number(np.max(np.abs(replans))) + " pp"],
        ["Cases and planning streams", "Typical paired half-width for 100 cases and three streams, Reacher and PushT", span(widths)],
        ["Software and aggregation", "Absolute elite-standard-deviation/version effects in the sealed factor analysis; report checkpoint averaging order", span(np.abs(library))],
    ]
    write_table(table_dir / "table_reporting.tex", "Minimum reporting fields and measured scales. The success-timing and history rows use corrected held-out results; factor and noise rows retain their original sealed cohorts.", "tab:reporting", "p{3.0cm}p{6.5cm}p{3.2cm}", ["Item", "Why it matters / scope", "Observed scale"], reporting_rows)
    term_rows = []
    for t in TASKS:
        for m in MODELS:
            q = one(terminal, task=t, model=m)
            term_rows.append([TASK[t], MODEL[m]] + [number(q[k + "_pct"]) for k in ["last5_occupancy", "last10_occupancy", "last5_all", "last10_all", "exit_after_first_hit", "outside_fraction_after_first_hit"]])
    write_table(table_dir / "table_terminal_window.tex", "Descriptive terminal-window summaries computed per physical trajectory before checkpoint averaging. Occupancy is the mean END indicator; all-$K$ requires every END label in the window. Exit-after-hit is the proportion of eligible trajectories with at least one later END failure. Outside-after-hit is their mean outside fraction strictly after first ANY hit.", "tab:terminal-window", "llrrrrrr", ["Task", "Configuration", r"Occ. $K=5$", r"Occ. $K=10$", r"All $K=5$", r"All $K=10$", "Exit after hit", "Outside after hit"], term_rows,
                note="All values are percentages. Eligibility requires a first hit before step 50; a first hit only at step 50 has no observable later step and is excluded from both post-hit denominators. -- denotes an empty eligible set. AD-WM metrics are computed separately for each checkpoint trajectory before averaging; eligible trajectory counts are supplied with the table data.")

    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "savefig.dpi": 250})
    figures = []

    def save(fig, name):
        fig.tight_layout()
        for ext in ["png", "pdf"]:
            path = fig_dir / (name + "." + ext)
            fig.savefig(path, bbox_inches="tight")
            figures.append(path)
        plt.close(fig)

    # Intro example is data-selected by the analyst, never the old reset trace.
    example_path = args.analysis / "INTRO_EXAMPLE_STATES.csv"
    if analysis_manifest.get("illustrative_example") and example_path.is_file():
        e = read_csv(example_path, analyzed=True)
        require(len(e) == 50, "Incomplete introductory example")
        require(np.isfinite(e[["abs_error0", "abs_error1", "threshold"]]).all().all(), "Invalid example state")
        fig, (left, right) = plt.subplots(1, 2, figsize=(10, 3.2), gridspec_kw={"width_ratios": [1, 1.25]})
        left.axis("off")
        left.set_title("Paired audit unit")
        for message, xy in [("Same case and start", (.5, .8)), ("Three fixed planning streams", (.5, .52)), ("One trajectory, three success labels", (.5, .24))]:
            left.text(*xy, message, ha="center", va="center", transform=left.transAxes,
                      bbox=dict(boxstyle="round,pad=.6", fc="#e9f2fb", ec="#2c5d87"))
        for start, end in [((.5, .71), (.5, .61)), ((.5, .43), (.5, .33))]:
            left.annotate("", xy=end, xytext=start, xycoords=left.transAxes, arrowprops=dict(arrowstyle="->"))
        right.plot(e.env_step, e.abs_error0, label="Joint 1", color="#286090")
        right.plot(e.env_step, e.abs_error1, label="Joint 2", color="#b55d26")
        right.plot(e.env_step, e.threshold, "k--", linewidth=.9, label="Success threshold")
        first = int(analysis_manifest["illustrative_example"]["first_any_hit_step"])
        right.axvline(first, color="#2b7a4b", linestyle=":", label="First ANY hit")
        right.set(xlabel="Environment step", ylabel="Absolute joint error (rad)", title="One corrected Reacher trajectory", xlim=(1, 50))
        right.legend(frameon=False, fontsize=7)
        right.grid(alpha=.15)
        save(fig, "FIG1_AUDIT_OVERVIEW")
        intro_status = {"status": "COMPLETE", "example": analysis_manifest["illustrative_example"], "error_curve": "Per-joint absolute qpos-target_qpos error; no angular wrapping"}
    else:
        intro_status = {"status": "NEEDS_PUSHT_EXAMPLE_WITH_PHYSICAL_ERROR_TRACE", "reason": "No corrected Reacher illustration satisfying the prespecified illustrative selection; do not reuse the old reset example or manufacture states."}
        notes.append("Figure 1 needs a separately verified PushT example; all other assets are generated.")

    fig, axes = plt.subplots(1, 4, figsize=(12, 3.4), sharey=True)
    x = np.arange(5)
    for ax, t in zip(axes, TASKS):
        for i, d in enumerate(DEFS):
            ax.bar(x + (i - 1) * .23, [rate(t, m, d).rate_pct for m in MODELS], width=.23, label=d, color=COLORS[d])
        ax.set_title(TASK[t]); ax.set_xticks(x); ax.set_xticklabels([MODEL[m] for m in MODELS], rotation=40, ha="right", fontsize=7)
        ax.set_ylim(0, 105); ax.grid(axis="y", alpha=.2)
    axes[0].set_ylabel("Success (%)"); axes[-1].legend(frameon=False, fontsize=7)
    save(fig, "FIG4_SUCCESS_RATES")

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, t in zip(axes, ["reacher", "pusht"]):
        for i, d in enumerate(["any", "final"]):
            rs = [contrast(t, m + " - LeWM_h1", d) for m in MODELS[1:]]
            val = np.array([r.delta_pp for r in rs]); lo = np.array([r.ci95_low_pp for r in rs]); hi = np.array([r.ci95_high_pp for r in rs])
            ax.errorbar(val, np.arange(4) + (i - .5) * .18, xerr=[val - lo, hi - val], fmt="o", capsize=2, label=d, color=COLORS[d])
        ax.set_title(TASK[t]); ax.set_yticks(np.arange(4)); ax.set_yticklabels([MODEL[m] for m in MODELS[1:]], fontsize=8)
        ax.axvline(0, color=".5", linewidth=.8); ax.set_xlabel("Difference from LeWM one-frame (pp)"); ax.grid(axis="x", alpha=.15)
    axes[-1].legend(frameon=False); save(fig, "FIG5_RANKING_REVERSALS")

    fig, axes = plt.subplots(2, 2, figsize=(10, 6))
    for ax, t in zip(axes.ravel(), TASKS):
        for m in MODELS:
            q = occupancy[(occupancy.task == t) & (occupancy.model == m)].sort_values("env_step")
            require(len(q) == 50, f"Occupancy grid incomplete {t}/{m}")
            ax.plot(q.env_step, q.occupancy_pct, linewidth=1.4, label=MODEL[m])
        for step in [25, 50]: ax.axvline(step, color=".65", linestyle=":", linewidth=.8)
        ax.set(title=TASK[t], xlabel="Environment step", ylabel="Target occupancy (%)", xlim=(1, 50)); ax.grid(alpha=.15)
    axes[0, 0].legend(frameon=False, fontsize=7, ncol=2); save(fig, "FIG6_OCCUPANCY_REV2")

    fig, axes = plt.subplots(1, 4, figsize=(11, 3.2), sharey=True)
    for ax, t in zip(axes, TASKS):
        for i, d in enumerate(DEFS):
            rs = [contrast(t, m + " CEM10 - CEM30", d, "D4_iterations") for m in MODELS[:2]]
            val = np.array([r.delta_pp for r in rs]); lo = np.array([r.ci95_low_pp for r in rs]); hi = np.array([r.ci95_high_pp for r in rs])
            ax.errorbar(val, np.arange(2) + (i - 1) * .18, xerr=[val - lo, hi - val], fmt="o", capsize=2, color=COLORS[d], label=d)
        ax.set_title(TASK[t]); ax.set_yticks([0, 1]); ax.set_yticklabels([MODEL[m] for m in MODELS[:2]], fontsize=7)
        ax.axvline(0, color=".5", linewidth=.8); ax.set_xlabel("CEM 10 minus 30 (pp)"); ax.grid(axis="x", alpha=.15)
    axes[-1].legend(frameon=False, fontsize=6); save(fig, "FIG_APPENDIX_CEM_ITERATIONS")

    # Main common-protocol figure is also safe to refresh from the merged view.
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.4), sharey=True)
    for ax, t in zip(axes, TASKS):
        rs = [contrast(t, m + " - LeWM_h1") for m in MODELS[1:]]
        val = np.array([r.delta_pp for r in rs]); lo = np.array([r.ci95_low_pp for r in rs]); hi = np.array([r.ci95_high_pp for r in rs])
        ax.errorbar(val, np.arange(4), xerr=[val - lo, hi - val], fmt="o", capsize=2, color=COLORS["any"])
        ax.set_title(TASK[t]); ax.set_yticks(np.arange(4)); ax.set_yticklabels([MODEL[m] for m in MODELS[1:]], fontsize=7)
        ax.axvline(0, color=".5", linewidth=.8); ax.set_xlabel("Any-step gain (pp)"); ax.grid(axis="x", alpha=.15)
    save(fig, "FIG3_COMMON_PROTOCOL_GAINS")

    # Peak summaries are descriptive and generated from END curves, never
    # inherited from hard-coded prose about the old reset-driven trajectory.
    peaks = []
    for t in TASKS:
        for m in MODELS:
            q = occupancy[(occupancy.task == t) & (occupancy.model == m)].sort_values("env_step")
            peak = q.loc[q.occupancy_pct.idxmax()]
            mid = q[(q.env_step >= 26) & (q.env_step <= 49)]
            low = mid.loc[mid.occupancy_pct.idxmin()]
            peaks.append(dict(task=t, model=m, peak_step=int(peak.env_step), peak_pct=float(peak.occupancy_pct),
                              middle_min_step=int(low.env_step), middle_min_pct=float(low.occupancy_pct),
                              step25_pct=float(one(q, env_step=25).occupancy_pct), step50_pct=float(one(q, env_step=50).occupancy_pct)))
    pd.DataFrame(peaks).to_csv(data_dir / "OCCUPANCY_PEAKS.csv", index=False)
    write_table(table_dir / "table_occupancy_peaks.tex", "Target occupancy at planned endpoints and within the intervening steps; Reacher uses corrected END labels.", "tab:occupancy-peaks", "llrrrr", ["Task", "Configuration", "Step 25", "Step 50", "Peak (step)", "Min. 26--49 (step)"],
                [[TASK[r["task"]], MODEL[r["model"]], number(r["step25_pct"]), number(r["step50_pct"]), f'{number(r["peak_pct"])} ({r["peak_step"]})', f'{number(r["middle_min_pct"])} ({r["middle_min_step"]})'] for r in peaks])

    pd.DataFrame(extra_contrasts).to_csv(data_dir/'ADDITIONAL_PAIRED_CONTRASTS.csv',index=False)
    manifest = {
        "status": "COMPLETE" if intro_status["status"] == "COMPLETE" else "ASSETS_COMPLETE_EXCEPT_INTRO_EXAMPLE",
        "utc": dt.datetime.now(dt.timezone.utc).isoformat(), "intro": intro_status,
        "analysis_manifest": str((args.analysis / "ANALYSIS_MANIFEST.json").resolve()),
        "nonreacher_main_statistics": "VERIFIED_UNCHANGED",
        "missing_summary_intervals": "Additional plotting contrasts use the sealed paired function on complete per-checkpoint trajectories (5000, seed 20261011); original summary rows and existing paired-table intervals remain unchanged.",
        "new_macro_values": macro_changes, "notes": notes,
        "prediction_subconditions": prediction_records,
        "still_to_integrate": ["Edit main.tex prose using actual corrected directions", "Add runtime/technical-gate appendix and compute/stop receipts", "Compile and visually inspect the manuscript; this script does not modify or compile it"],
        "inputs": inputs,
        "outputs": {p.relative_to(args.output).as_posix(): sha(p) for p in args.output.rglob("*") if p.is_file()},
    }
    (args.output / "PAPER_ASSETS_MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": manifest["status"], "output": str(args.output), "figures": len(figures)}, indent=2))


if __name__ == "__main__":
    main()
