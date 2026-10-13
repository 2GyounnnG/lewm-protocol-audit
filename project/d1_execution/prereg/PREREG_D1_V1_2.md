# D1 preregistration, version 1.2

**Evaluation-protocol factors, free planner settings and claimed gains on the LeWM four-task suite**

Status: REGISTERED_BEFORE_GPU. The SHA-256 of this file and the UTC time of registration are in `PREREG_D1_V1_2_RECEIPT.json`. Version 1.1 superseded version 1 (SHA-256 ab599de6…) before any formal job by changing technical gates 3 and 6 (`CHANGES_V1_TO_V1_1.md`). Version 1.2 supersedes version 1.1 (SHA-256 1e2c0131…) during the formal runs; it changes only technical gate 3 and applies only to the PushT unified-protocol conditions, none of which has a complete result (`CHANGES_V1_1_TO_V1_2.md`). No formal D1 trajectory has been run. A change made before the first formal job creates version 1.1 with a written reason; a change made after it is a deviation (Section 9). Prepared by the author with AI assistance (Claude, Anthropic; Codex, OpenAI); the step-1 draft `PREREG_D1_DRAFT.md` (SHA-256 a39ab87e…) is superseded by this file, and the changes are listed in `CHANGES_FROM_DRAFT.md`.

## 0. Prior exposure

Known to us before registration:
- Official LeWM and refit-predictor results on the 100 original cases per task, and official-predictor single-frame results on the R8 M2 fresh cases used here (R3–R8 of the earlier audit).
- Real-history adapter results (`H_REAL3_REPLAN`) on Reacher, PushT, TwoRoom and Cube; the library-native `history_len=3` result on the Reacher R6 history set (R10 A, +12.0 pp [7.7, 16.7]).
- The published numbers compiled in the step-0/1 literature audit (`BASELINE_AUDIT.csv`, SHA-256 d0eefef6…).

Not seen: any result of M01, M03 or M07 on any case; library-native `history_len=3` on the unified case sets; any result on planner streams D–J; any result under F-version, F-offset, F-goal, F-CEM, F-angle, F-replan or F-success.

## 1. Questions

1. Published LeWM baselines on this suite differ widely under the same nominal protocol (offset 25, budget 50). Which evaluation choices can produce differences of that size on the official checkpoint?
2. How large is the effect of free planner settings (library-native history, more frequent replanning) relative to the gains claimed by published methods?
3. Under a common protocol and paired case-level analysis, how much of the claimed gain of methods with public artifacts remains?
4. How much of an apparent effect can planner randomness produce at common sample sizes?

## 2. Definitions

**Base protocol P0.** Official LeWM weights (`quentinll/lewm-{reacher,pusht,tworooms,cube}` `weights.pt`, SHA-256 eb70b1fd…, 48938400…, 566f2236…, 2839a907…); stable-worldmodel commit 63988116; CEM with 300 candidates, 30 elites, 30 iterations, initial standard deviation 1, elite standard deviation without small-sample correction (population), candidate 0 equal to the current mean, no candidate clipping; planning horizon 5 macro-steps of 5 raw steps; execute 25 raw steps, then replan; raw budget 50; start–goal offset equal to the sealed actual index difference of 25; goal image is the dataset endpoint frame; model normalization uses the sealed full-data statistics; the official environment success is checked after every executed primitive and the first success ends the episode (any-step success); `history_len=1`.

**History.** `h1`: library default, one real frame. `h3`: library-native `history_len=3` (commit 63988116): the first call receives one real frame and no action history; later calls receive the real frames at t−10, t−5 and t and the two executed 5-raw action blocks between them. No future frame and no padding is supplied. `H_REAL3_REPLAN` is the earlier audit's adapter and is used only as a mechanism reference.

**Cases.** UNIFIED = the 100 original cases plus the 100 R8 M2 fresh cases per task (`UNIFIED_CASES_V1.json`: the case entries of `UNIFIED_CASES_DRAFT.json`, SHA-256 1020514f…, unchanged; only the status field is set to FROZEN_V1); original and fresh episodes do not overlap. TECH cases (`tech_{task}.json`) are disjoint from UNIFIED and are used only for technical gates and throughput.

**Planner streams.** A, B, C = `R3_ORIGINAL`, `R4_ALT_CEM_1`, `R4_ALT_CEM_2`; D–J = `D1_CEM_STREAM_4` … `D1_CEM_STREAM_10`. The CEM generator is reset at every planning call with seed = first 8 bytes (big-endian uint64) of SHA-256(namespace/task/case_id/replan_index); stream A uses namespace `R3_CEM_CASE_20261002`, the others use the stream name (`CASE_AND_RANDOM_STREAM_MANIFEST.json`, SHA-256 a33deab1…). Streams are never selected by outcome.

**Unit of analysis.** A trajectory yields success 0 or 1. A case score is the mean over planner streams; for M07 it is the mean over the three training seeds (equal weight) of the stream means. Cases are the independent unit.

## 3. Conditions

The frozen job manifest is `RUN_PLAN_V1.csv` (SHA-256 in the receipt).

### 3.1 Factor sweep on the official checkpoint (H1)
All on UNIFIED, streams A–C unless stated; each factor changes one element of P0.
- P0 (h1), streams A–J.
- F-history: P0 with `h3`, streams A–J.
- F-version-old: stable-worldmodel commit abdced49.
- F-version-pip: stable-worldmodel PyPI 0.0.6 distribution, defined by the SHA-256 of the installed distribution file recorded at install time (the nearest git commit is reported descriptively).
- F-offset: actual start–goal offset 24.
- F-goal: goal image re-rendered from the goal state in an isolated copy of the environment. Runs only if its technical gate passes; otherwise recorded as not run.
- F-CEM: elite standard deviation with small-sample correction (sample standard deviation).
- F-angle (PushT only): the older angle-difference formula of the success check.
- F-replan: receding horizon, executing 5 raw steps (one block) before replanning, horizon unchanged; at `h1` and at `h3`.
- F-success: no termination at first success; the episode runs to the raw budget of 50. Success is computed from the same trajectory three ways: any executed step (P0 definition), at block boundaries (every 5 raw steps) and at the final state (step 50).
- F-n (derived; no new trajectories): distribution of 50-case and 100-case subsample estimates of P0 success.
- Mechanism reference: `H_REAL3_REPLAN`.

### 3.2 Methods under the unified protocol (H2, H3b)
UNIFIED, streams A–C, P0 settings except for the components each method defines.
- M01 Fast-LeWM, plain variant (self-consistency weight 0), released checkpoints. Its released rollout fixes the dynamic history at 1, so only `h1` is run; `h3` is recorded as not applicable.
- M07 AD-WM, training seeds 3072, 4096 and 6144 evaluated separately; `h1` and `h3`.
- M03 AP-CEM on the frozen official LeWM: observed-successor retrieval (top 8) from a training-episode bank that excludes all UNIFIED, TECH and AP original-protocol evaluation episodes; 5-raw planning and replanning; CEM numbers as in P0; `h1` and `h3`. This is the unified version of AP, not a byte-identical copy of the authors' planner; its original settings (standard deviation 1/3, clipping, standard-deviation floor, prior/mean choice) are used only in Section 3.3.

### 3.3 Original-protocol checks (H3a)
Each method's own entry point and configuration, with its original single evaluation seed:
- M01: the Fast plain cell of the paper's Table 1, 50 cases per task, and the official LeWM under the same entry.
- M07: the paper's main protocol, 50 cases per task for each of the three training seeds (evaluation seed 42, actual offset 24). The paper's matched LeWM baseline weights are not public; the matched gain is therefore not estimable and the official LeWM is not substituted for it.
- M03: the clean AP-CEM cell of the paper's Table 1 (128 cases per task; offsets 150/140/150/100 and budgets 150/280/300/200 for Cube/PushT/Reacher/TwoRoom) and the native LeWM under the same entry.

## 4. Hypotheses and predictions

**H1 (protocol factors).** For each factor: the paired difference from P0 with a 95% interval; for F-history and P0 over streams A–J, the range and standard deviation of single-stream success; for F-n, the 2.5–97.5% range of subsample estimates. These are placed beside the per-task ranges of published LeWM baselines (`BASELINE_AUDIT.csv`).
- **H1a (confirmatory).** In Reacher, F-history has the largest absolute paired difference among {F-history, F-version-old, F-version-pip, F-offset, F-goal, F-CEM}, and its point estimate is at least +10 pp with a 95% interval whose lower bound exceeds 0.
- **H1b (confirmatory).** In PushT, TwoRoom and Cube, the point estimate of F-history lies within ±2 pp.
- No prediction for planner streams, F-replan, F-success, F-n or F-angle.

**H2 (free settings vs methods).**
- **H2a (confirmatory).** In Reacher, for each method m in {M01, M03, M07 averaged over seeds} at `h1`, the paired difference LeWM(`h3`) − m(`h1`) has a point estimate ≥ 0 and a 95% interval whose lower bound exceeds −5 pp.
- Descriptive: the same contrast in the other three tasks; m(`h3`) − LeWM(`h3`) for M03 and M07; LeWM with F-replan (`h1`, `h3`) against each method.

**H3 (claimed gains).**
- (a) Original protocol: a reported absolute success rate is "reproduced" if it lies inside our 95% case-bootstrap interval for the same cell (M07: seeds averaged within case; per-seed values also reported). For M01 and M03 the gain over native LeWM under the same entry is also estimated and compared with the reported gain.
- (b) Unified protocol: m − LeWM(`h1`) and m − LeWM(`h3`) for every method and task. No directional prediction.

**H4 (planner noise).** Single-stream false signals (thresholds 5, 10, 15 pp, positive and absolute, with the step-0 definition of a near-zero cell: |mean of A–C| ≤ 2 pp) and 95% interval half-widths for 50/100/200 cases × 1/3/10 streams, computed from the P0 and F-history ten-stream data. Descriptive. Whole streams are resampled; ten streams are never constructed from three.

## 5. Statistics

- Paired case bootstrap, 5,000 replicates, percentile 95% two-sided intervals, random seed 20261011. Primary: resampling cases in the mixed 200-case set; sensitivity: resampling within the original and fresh cohorts separately and reporting each cohort.
- Within a case, outcomes are averaged over planner streams and, for M07, then over training seeds, before resampling.
- Labels: "gain established" if the lower bound exceeds 0; "loss established" if the upper bound is below 0; "practically negligible" only if the whole interval lies within [−5, +5] pp; otherwise "not detected".
- Multiplicity (sensitivity only): Holm adjustment over the 12 method × task contrasts, separately for the references LeWM(`h1`) and LeWM(`h3`), using two-sided p-values from the centered bootstrap. Primary intervals are not adjusted.
- Missing cells stay missing. Delivery must cover the whole job manifest; a contrast with any missing cell is reported as incomplete and is not used for H1a, H1b or H2a.
- Analysis code: `tools/statistics_d1.py` from the step-1 upload package (SHA-256 recorded in the receipt). Any analysis not listed here is labeled post hoc.

## 6. Technical gates (before any formal job)

1. Fidelity: for each method × task (M07 per seed), the authors' entry point and our adapter in original-protocol mode, in separate processes, on the first 4 evaluation episodes of the original protocol: actions equal within atol 1e−6 and rtol 1e−5, identical success, identical case, reset and goal identity.
2. History: for LeWM, M03 and M07, first plans under `h1` and `h3` are bitwise identical (dtype, shape, bytes) on TECH cases.
3. Reset and goal: every task uses its native library reset procedure, as in the earlier sealed runs; for PushT this includes the internal settle step of the native state setter, and Cube uses the R10 reset (`clear_internal` with exact qpos, qvel and target). No adapter may override the native reset. On TECH cases: (a) two independent processes give bitwise identical post-reset states; (b) archived reset or first-plan references produced with the same procedure are reproduced where they exist; (c) for Reacher, TwoRoom and Cube, the post-reset state equals the start state recorded in the case manifest after casting to the manifest's dtype; for PushT, the offset of the post-settle state from the manifest start is recorded descriptively; (d) the goal image equals the dataset endpoint frame bit for bit. F-goal runs only after its isolated goal-render gate passes.
4. F-success: on TECH cases, the executed action sequence up to the first success equals the P0 trajectory bitwise.
5. F-replan: number of planning calls and the history construction match the definition.
6. Planner streams and numerical reproduction. (a) Per-call CEM seeds for streams A–J follow the rule in Section 2, and for streams A–C they equal the sealed seed values recorded for the same case and replanning index. (b) Where a sealed first-plan reference produced with the same library version exists on a TECH case, the new first plan reproduces it within the recorded cross-machine tolerance: for P0, the Reacher stream-A references of R10 (commit 63988116); for F-version-old, the stream-A references of the earlier audit (commit abdced49) where they exist. (c) For every task, streams A–C give bitwise identical first plans in two independent processes on TECH cases. Streams B and C have no archived first-plan references on the TECH cases (search of 394,826 files, `GATE6_BC_REFERENCE_SEARCH.json`); they are covered by (a) and (c). A task without any same-version reference under (b) is reported as such.
7. Each environment records pip freeze, driver, hardware and the file hashes of key packages.
A gate that compares against an archived reference which does not exist is evaluated with the same-run checks defined above, and the missing reference is recorded; a missing reference alone does not block formal runs. A failed gate is fixed and rerun; a fix that changes a definition in this document stops the affected conditions and requires a new version before they run.

## 7. Budget and stopping rule

- Cap: 300 RTX 4090 GPU-hours for formal runs (summed over GPUs). Earlier LeWM runs on 8 × RTX 4090 took about 3–9 GPU-minutes per 100 trajectories (R10 receipts); this is a planning figure only.
- After the gates, throughput is measured on TECH cases for each condition type. Projected total = measured upper rate × manifest units + 15% reserve. Formal runs start only if the projection is ≤ 300; the check is repeated before each stage.
- If the projection exceeds 300, the run stops and reports. Reductions are then applied only in this order, as a registered change before further formal runs, until the projection is ≤ 300: (1) drop F-version-pip; (2) drop F-replan at `h3`; (3) reduce P0 and F-history to streams A–F; (4) drop F-goal; (5) drop the `h3` rows of M03 and M07. P0, F-history, the `h1` rows of all methods and the original-protocol checks are never dropped.
- Stage order: (i) P0 and F-history on streams A–J; (ii) methods under the unified protocol; (iii) the other factors; (iv) original-protocol checks.

## 8. Confirmatory and exploratory

Confirmatory: H1a, H1b, H2a. Everything else is descriptive or exploratory, and analyses added after outcomes are seen are labeled post hoc.

## 9. Deviations

Every change after registration is written to `DEVIATIONS.jsonl` with UTC time, old and new SHA-256, reason, affected condition IDs and whether any outcome had been seen. Earlier results are kept; affected analyses are labeled.

## 10. Records

Per-trajectory raw table (case, stream, seed, condition, success under each success definition where available, executed raw steps, planning calls, model-call counts, wall time, first-plan hash), the job manifest, the budget ledger, gate evidence, environment locks and seals are archived with the results.
