# Changes from PREREG_D1_DRAFT.md (step 1) to PREREG_D1_V1.md

Decisions on the eight step-1 questions (2026-10-11):
1. Fast h3: the released rollout fixes the dynamic history at 1, so M01 runs at h1 only; h3 rows dropped (not applicable). Main variant Fast plain (SC = 0).
2. Endpoint: P0 keeps any-step success with first-success stop (as in all sealed runs). New condition F-success runs episodes to the budget and derives any-step, block-boundary and final-step success from the same trajectories, with a prefix-equality gate against P0.
3. Fresh cases: R8 M2 fresh 100 per task for all four tasks; prior exposure stated in Section 0.
4. AD-WM matched baseline: weights not public; original-protocol check reports absolute success only; matched gain not estimable; official LeWM not substituted; 12 blocked rows dropped.
5. pip 0.0.6: F-version-pip is defined by the SHA-256 of the installed PyPI distribution file; nearest git commit reported descriptively.
6. Budget: cap kept at 300 RTX 4090 GPU-hours; planning figure corrected to the R10 receipts (about 3-9 GPU-minutes per 100 LeWM trajectories; the 20-40 minute figure in the step-0/1 prompts came from the much heavier PreJEPA runs). A pre-specified reduction order is added (Section 7).
7. AP unified boundary: accepted as drafted (retrieval and 5-raw replanning kept; P0 CEM numbers; original settings only in the original-protocol check).
8. Cube reset and environment gates: accepted; the gates in Section 6 must pass before formal jobs.

Other changes:
- New free-setting factor F-replan (execute 5 raw then replan) at h1 and h3, also used descriptively against the methods.
- H1a restricted to factors that change the planner or model inputs {history, version old, version pip, offset, goal, CEM}; streams, F-replan, F-success, F-n and F-angle carry no prediction.
- H2a stated as a non-inferiority-style prediction (point estimate >= 0 and lower bound > -5 pp) in Reacher only.
- H3a reproduction criterion: reported value inside our 95% case-bootstrap interval.
- The preregistration is written in English so it can be cited in the paper.
- RUN_PLAN_V1.csv: 129 rows (109 active), 618.24 units; dropped rows are kept with units 0 for traceability.
