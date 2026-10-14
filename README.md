# LeWM protocol audit

The complete audit records are archived at Zenodo, DOI **[10.5281/zenodo.23350373](https://doi.org/10.5281/zenodo.23350373)**, under CC BY 4.0. Audit code is MIT. This repository is the small-file code and summary mirror. It contains no manuscript, model weights or input datasets.



## Archive layout (full trajectories are in Zenodo)

- `project/d1_execution/`: case lists, preregistrations, checkpoint/data manifests, frozen statistics, original formal trajectories and result tables.
- `project/paper_jair/r3_part2_work/analysis_final/`: corrected Reacher CPU analyses.
- `project/paper_jair/r3_part2_work/paper_assets_final_v2/data/`: derived cross-task measures.
- `project/paper_jair/r3_part2_work/revision4/`: full 2,700-record audit, 300-pair first-plan check, terminal-window intervals, worker diffs and minimal CPU instructions.
- `project/paper_jair/r3_part2_work/revision5/`: three-label contrasts and unified-seed paired intervals.
- `returned_experiment/formal_verified/`: the 2,700 valid corrected formal trajectories; `tech_verified/` holds the 108 TECH trajectories. Other attempt directories are diagnostic, not formal analysis inputs.
- `returned_experiment/final_code/`, `code_frozen/`: final and reference workers and adapters; `complete.freeze.txt` records the full experimental environment.
- `return_evidence/`: retained transfer/stop receipts. Operational authentication files and environment dumps are excluded from the public derivative.
- `MATERIALS_MANIFEST.json`: distributed-file SHA-256 and original hashes for sanitized files. `RELEASE_SCAN.json`: content scan and exclusion/redaction decisions.

No manuscript PDF, manuscript source, public checkpoint weights, or input datasets are redistributed. Public assets are identified by source URL and SHA-256 in `HF_ASSETS_MANIFEST.json` and the binding/manifests. Obtain them from their authors under their own terms. The trajectory arrays are outputs of this study, not input datasets.

## CPU reproduction

Use Python 3.12 (the analysis was checked with NumPy 1.26.4, pandas 2.2.2, SciPy 1.13.1 and Matplotlib 3.9.2):

```sh
python3.12 -m venv .venv-cpu
. .venv-cpu/bin/activate
python -m pip install numpy==1.26.4 pandas==2.2.2 scipy==1.13.1 matplotlib==3.9.2
python project/paper_jair/r3_part2_work/revision4/verify_formal_c1_d.py \
  --project-root project --corrected-experiment returned_experiment \
  --output-dir recomputed_c1_d
python project/paper_jair/r3_part2_work/revision4/analyze_windows_a_g.py
python project/paper_jair/r3_part2_work/revision5/analyze_revision5.py
```

These commands only read saved records and compute CPU statistics; no model or simulator is executed. Paired case bootstrap: 5,000 draws, seed 20261011, identical case-index vectors across contrasts. Streams/checkpoints are averaged within case before bootstrap. Recompute in a working copy, leaving the distributed archive unchanged.

To reconstruct the historical model-evaluation environment separately, use **Python 3.12.3** and the frozen full requirements (CUDA 12.8 wheels):

```sh
python3.12 -m venv .venv-experiment
. .venv-experiment/bin/activate
python -m pip install --index-url https://pypi.org/simple \
  --extra-index-url https://download.pytorch.org/whl/cu128 \
  -r returned_experiment/complete.freeze.txt
python -m pip check
```

The environment includes local editable/upstream-source entries. Recreate those from the commits/source manifests recorded in the environment evidence before installing the frozen list; do not silently substitute a release. Worker entry points and the final TECH report record the original commands and preconditions. Installing this environment is not needed for the saved-record CPU checks above. Frozen third-party versions may no longer be available on every mirror.

Historical SEAL files authenticate historical snapshots and can refer to files intentionally not redistributed here (weights, datasets, operational files or the manuscript). For this public derivative, use the root `MATERIALS_MANIFEST.json`; do not treat an omitted historical path as a missing formal record. Original local sealed directories were not modified.

## Licenses

The derived records, case selections, tables and documentation are **CC BY 4.0**; see the complete `LICENSE-DATA`. Ruiqi Wang's audit code (`*.py` and script directories, including worker patches, analysis and plotting code) is **MIT**; see `LICENSE`. Third-party source excerpts retain their original copyright and licenses; this grant does not relicense upstream stable-worldmodel/stable-pretraining or the checkpoint/data providers. Patch licenses cover the author's modifications only. The public code mirror has an MIT root license and identifies CC BY 4.0 record summaries separately.

For CPU reproduction, extract the full Zenodo archive first; this small-file mirror intentionally omits raw trajectories and large tables. The commands above refer to the full archive layout.

The root LICENSE is MIT for the author’s code. LICENSE-DATA is CC BY 4.0 for case lists, preregistrations and result summaries. Third-party source notices remain applicable.

Original upstream license texts for redistributed source excerpts are retained in `THIRD_PARTY_LICENSES/`; they apply to the corresponding upstream code, not to new authorship by Ruiqi Wang.


## Revision 7: native AP Reacher renderer check

`revision7_complete/` adds A/B sensitivity and static-code audit records plus the completed C replication. Native OSMesa yields97/128 (75.8%,95%CI68.0–82.8), equal to the paper aggregate; six cases switch each way. On the frozen first50 cases, changing only OSMesa to EGL raises first-arrival success from37/50 to49/50: +24.0pp [12.0,36.0]. All50 EGL action arrays and first-hit steps match the historical EGL run. Appendix seeds42/43/44 separately yield74%,66%,70% under offset24,budget50. These are separate from the common50-step evaluation.

Run `python revision7_complete/C/recompute_C.py --root revision7_complete/C --output /tmp/recomputed_C.json` for a CPU-only summary check. Full traces, image probes and historical action references are in the separately prepared records/code archive; this GitHub mirror omits them. The Revision7 new-version Zenodo draft is pending authentication and has not been published. The existing DOI above identifies the published base archive only.

An earlier A/B supplement accidentally tracked a manuscript PDF and TeX. They have been removed from the current tracked version while local copies are preserved. Earlier Git history may still contain them; history rewriting was not performed. This update contains only records and code, not the current manuscript.

## Revision7 renderer provenance follow-up

`revision7_renderer_followup/` adds the12-source renderer column evidence, saved-image pixel differences and A/B/C scientific logs. The Reacher collection script selectsGLFW; official HF metadata confirms LeWM training on the same dataset, but does not specify the productionHDF5 renderer. NeitherEGL norOSMesa is a verified training-renderer match. MeanRGB-byte differences across three saved pairs are2.56–2.59, maximum72. All primary audit formal runs usedEGL configuration; the nativeAP reproduction explicitly distinguishesOSMesa/EGL.

The complete Revision7 records/code archive is prepared for **version2 of the Zenodo record** (draft only; not published). Creation/upload is currently blocked because the task process has no ZENODO_TOKEN. The published base record23350373 is unchanged. Bundle SHA and scan are in PACKAGE_RECEIPT.json and RELEASE_SCAN.json; no manuscript is included.
