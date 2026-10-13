"""Reproduce Appendix/Section 7 occupancy observations from sealed A1 curves.

This CPU-only script reads the already sealed occupancy summary, emits a public-label
summary and an appendix table, and records source hashes for auditability.
"""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
IN = ROOT / "a1_results" / "A1_OCCUPANCY_CURVES.csv"
OUT_CSV = ROOT / "a1_results" / "REV2_OCCUPANCY_SUMMARY.csv"
OUT_TEX = ROOT / "tables" / "table_occupancy_peaks.tex"
OUT_JSON = ROOT / "a3_results" / "REV2_OCCUPANCY_AUDIT.json"
MODEL = {
    "LeWM_h1": "LeWM one-frame",
    "LeWM_h3": "LeWM three-frame",
    "M01_h1": "Fast-LeWM",
    "M03_h1": "AP",
    "M07_h1": "AD-WM",
}
TASK = {"reacher": "Reacher", "pusht": "PushT", "tworoom": "TwoRoom", "cube": "Cube"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def f1(x):
    return f"{x:.1f}"


def main():
    rows = []
    with IN.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({"model": r["model"], "task": r["task"],
                         "step": int(r["raw_step"]), "occupancy": float(r["occupancy"]) * 100.0})
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r["task"], r["model"])].append(r)
    out = []
    for task in ["reacher", "pusht", "tworoom", "cube"]:
        for model in ["LeWM_h1", "LeWM_h3", "M01_h1", "M03_h1", "M07_h1"]:
            g = sorted(grouped[(task, model)], key=lambda x: x["step"])
            by = {x["step"]: x["occupancy"] for x in g}
            peak = max(x["occupancy"] for x in g)
            peak_steps = [x["step"] for x in g if abs(x["occupancy"] - peak) < 1e-12]
            mid = [x for x in g if 26 <= x["step"] <= 49]
            mid_min = min(mid, key=lambda x: x["occupancy"])
            out.append({
                "task": TASK[task], "configuration": MODEL[model], "model_code": model,
                "peak_step": "/".join(map(str, peak_steps)), "peak_pct": peak,
                "step25_pct": by.get(25, float("nan")), "step50_pct": by.get(50, float("nan")),
                "mid_min_step": mid_min["step"], "mid_min_pct": mid_min["occupancy"],
                "peak_to_mid_drop_pp": peak - mid_min["occupancy"],
                "mid_decline_after_25": bool(mid_min["occupancy"] < by.get(25, float("inf"))),
            })
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        fields = list(out[0].keys())
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(out)
    # Compact table intended for Appendix B; all values are percentages.
    lines = [r"\begin{table*}[t]", r"\centering", r"\caption{Occupancy-curve landmarks computed from the recorded 50-step trajectories. Percentages are the fraction of cases in the goal at each raw step; steps 25 and 50 are the ends of the two 25-step plans. The middle minimum is the minimum over steps 26--49.}", r"\label{tab:occupancy-peaks}", r"\scriptsize", r"\begin{tabular}{llrrrrrr}", r"\toprule", r"Task & Configuration & Peak step & Peak (\%) & Step 25 (\%) & Step 50 (\%) & Mid. min. step & Mid. min. (\%) \\", r"\midrule"]
    for r in out:
        lines.append(f"{r['task']} & {r['configuration']} & {r['peak_step']} & {f1(r['peak_pct'])} & {f1(r['step25_pct'])} & {f1(r['step50_pct'])} & {r['mid_min_step']} & {f1(r['mid_min_pct'])} \\\\")
        if r["configuration"] == "AD-WM": lines.append(r"\addlinespace")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Four-panel occupancy figure (all tasks; public labels).
    try:
        import matplotlib.pyplot as plt
        fig, axs = plt.subplots(2, 2, figsize=(8.4, 6.0), sharex=True, sharey=False)
        for ax, task in zip(axs.ravel(), ["reacher", "pusht", "tworoom", "cube"]):
            for model in ["LeWM_h1", "LeWM_h3", "M01_h1", "M03_h1", "M07_h1"]:
                g = sorted(grouped[(task, model)], key=lambda x: x["step"])
                ax.plot([x["step"] for x in g], [x["occupancy"] for x in g], lw=1.4, label=MODEL[model])
            ax.axvline(25, color="0.65", ls="--", lw=.7); ax.axvline(50, color="0.65", ls=":", lw=.7)
            ax.set_title(TASK[task]); ax.set_xlim(1, 50); ax.set_ylim(bottom=0); ax.grid(alpha=.2)
            ax.set_xlabel("Raw step"); ax.set_ylabel("Occupancy (%)")
        axs[0,0].legend(fontsize=6, frameon=False, ncol=2)
        fig.tight_layout()
        fig.savefig(ROOT / "figures" / "FIG6_OCCUPANCY_REV2.pdf", bbox_inches="tight")
        fig.savefig(ROOT / "figures" / "FIG6_OCCUPANCY_REV2.png", dpi=220, bbox_inches="tight")
        plt.close(fig)
        fig_paths = ["figures/FIG6_OCCUPANCY_REV2.pdf", "figures/FIG6_OCCUPANCY_REV2.png"]
    except Exception as exc:
        fig_paths = [f"figure_generation_error:{type(exc).__name__}:{exc}"]
    # Record source hash and machine-readable observations for the paper audit.
    audit = {"source": str(IN.relative_to(ROOT)), "source_sha256": sha256(IN),
             "rows": len(rows), "generated_from_sealed_results": True,
             "landmarks": out,
             "figure_paths": fig_paths,
             "interpretation": {
                 "Reacher": "Most configurations peak at step 25 and dip during steps 26--49; LeWM three-frame peaks at step 50.",
                 "PushT": "Most configurations peak at step 25, decline during the second plan, then rebound near step 50; Fast-LeWM peaks at both endpoints.",
                 "TwoRoom": "All configurations climb toward a second-plan endpoint; intermediate dips occur for steps 26--49.",
                 "Cube": "All configurations peak at steps 25/26 and decline through the middle before a modest step-50 rebound.",
             }}
    OUT_JSON.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT_CSV} ({len(out)} rows), {OUT_TEX}, {OUT_JSON}")

if __name__ == "__main__": main()
