# D1 follow-up preregistration (V2): held-out confirmation under three success definitions, and a replanning mechanism check

Status: REGISTERED_BEFORE_GPU for the follow-up conditions below (SHA-256 and UTC in `PREREG_D1_V2_FOLLOWUP_RECEIPT.json`). The main study remains governed by `PREREG_D1_V1_2.md`. Prepared by the author with AI assistance (Claude, Anthropic; Codex, OpenAI).

## 0. Prior exposure
All step-2 results of the main study have been seen, including a stream-matched reanalysis (streams A–C in both arms) and a review that raised four points: the any-step-only scope of the "protocol range" summary, the confounding of replanning interval with warm start in F-replan, the narrow scope of the noise summaries, and degenerate bootstrap intervals for all-success cells. The predictions below are based on those results. No result exists on the HELDOUT cases defined here.

## 1. Purpose
1. Confirm the main comparisons on cases never used in any earlier run.
2. Measure how each model's success and the ranking of models depend on the success definition (any executed step, block boundaries, final state).
3. Separate the replanning interval from warm starting and from the receding arrival time in the F-replan drop.

## 2. Cases, streams and protocol
- **HELDOUT**: 100 new cases per task from episodes never used in R3–R10 or D1 (including UNIFIED, TECH, history, stress and refit sets) and not in any training or retrieval bank, selected by SHA-256 order of the episode identifier with namespace `D1_V2_HELDOUT/<task>/`, start and goal built exactly as for the UNIFIED cases (actual offset 25, budget 50). The manifest is sealed (SHA-256 and UTC) before the first job. TECH cases are those of V1.2.
- Streams A–C with the V1.2 seed rule. All contrasts use the same streams in both arms.
- Protocol: P0 of V1.2 (native reset for every task, commit 63988116, CEM 300/30/30, initial standard deviation 1, population elite standard deviation, horizon 5 × 5 raw, execute 25 raw, budget 50), except that **episodes are not terminated at the first success**: every episode runs to raw step 50 and the official success is logged at every raw step. Any-step success then equals the P0 definition (step 2: 2,400 of 2,400 trajectories identical); block success is evaluated at raw steps 5, 10, …, 50; final success at raw step 50.

## 3. Conditions
**Models on HELDOUT, all four tasks** (default history first):
LeWM h1; LeWM h3; M01 Fast plain h1 (h3 not applicable); M03 AP-CEM h1 and h3 (unified configuration of V1.2: observed-successor retrieval, top 8, from the training-episode bank with all evaluation episodes including HELDOUT excluded; 5-raw planning and replanning; P0 CEM numbers); M07 AD-WM seeds 3072, 4096, 6144, h1 and h3.

**Replanning mechanism, LeWM h1, HELDOUT, Reacher and PushT**:
- R25: P0 (execute 25 raw, then replan).
- R5-warm: execute 5 raw, then replan with the native warm start (the unexecuted remainder of the previous plan initialises the next optimisation); horizon fixed at 5 blocks (as F-replan in V1.2).
- R5-cold: execute 5 raw, replan without warm start; horizon fixed at 5 blocks.
- R5-shrink: execute 5 raw, replan without warm start; the horizon shrinks so that the planned arrival stays at raw step 25 for the first segment and at raw step 50 for the second (5, 4, 3, 2, 1 blocks, then 5, 4, … again).
Optimisation budget per call (candidates, elites, iterations) is identical in all four cells.

## 4. Predictions
Confirmatory (any-step success, stream-matched, 95% case-bootstrap intervals):
- **C1 (history)**: Reacher LeWM h3 − LeWM h1 ≥ +10 pp with lower bound > 0; PushT, TwoRoom and Cube point estimates within ±2 pp.
- **C2 (free setting vs default methods, Reacher)**: LeWM h3 − M01 h1 and LeWM h3 − M07 h1 (seed-averaged): point estimate ≥ 0 and lower bound > −5 pp. LeWM h3 − M03 h1: point estimate < 0.
- **C3 (method gains, TwoRoom and Cube)**: M03 h1 − LeWM h1 and M07 h1 − LeWM h1 have lower bounds > 0.
Descriptive:
- **D1**: any-step, block and final success for every model and task; the ranking of the five default-configuration models (LeWM h1, LeWM h3, M01 h1, M03 h1, M07 h1) under each definition, with Kendall's tau between definitions; paired differences between definitions.
- **D2**: success of the four replanning cells under the three definitions; paired differences R5-cold − R5-warm (warm start), R5-shrink − R5-cold (receding arrival), R25 − R5-shrink (remaining interval effect).
- **D3**: original-cohort, fresh-cohort and HELDOUT estimates side by side for the main-study contrasts.

## 5. Statistics
As V1.2 Section 5 (5,000 case-bootstrap replicates, percentile 95% intervals, seed 20261011, M07 averaged over seeds within case), with every contrast stream-matched. For cells in which every trajectory succeeds or fails, the bootstrap interval is degenerate; absolute rates are therefore also reported with an exact Clopper–Pearson interval on case-level majority outcomes and the count of successful trajectories. Holm sensitivity over method × task contrasts as in V1.2.

## 6. Gates, budget and stopping
Technical gates of V1.2 Section 6 apply, plus: (a) HELDOUT reset and goal checks; (b) for each mechanism cell, the call schedule, warm-start state and horizon per call match the definition on TECH cases; (c) the continue-to-budget prefix equality with first-success termination on TECH cases. Budget cap: 120 RTX 4090 GPU-hours for these follow-up runs. Local problems block only the affected conditions. If the projection exceeds the cap, drop in this order: M03 h3 and M07 h3; then R5-warm (already measured in V1.2 as F-replan, on other cases).
