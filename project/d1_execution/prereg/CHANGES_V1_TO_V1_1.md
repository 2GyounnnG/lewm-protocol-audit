# Changes from PREREG_D1_V1.md to PREREG_D1_V1_1.md (2026-10-11, before any formal job)

Reason: during the step-2 technical gates, gate 6 of V1 ("streams A-C reproduce the sealed first plans of the earlier audit on TECH cases") could not be evaluated for streams B and C, because no archived first-plan references exist for the 16 TECH cases (search of 394,826 files; step2/resume_01/evidence/GATE6_BC_REFERENCE_SEARCH.json). The V1 wording assumed references that were never archived; it was a drafting error, not a failed check.

Evidence seen before this change: technical first-plan comparisons only (Reacher stream-A first plans bitwise identical to the sealed R10 native references, maximum difference 0; h1/h3 first plans bitwise identical in 12 pairs for Reacher, PushT and TwoRoom). No formal trajectory has been run and no formal outcome has been seen.

Changes:
1. Gate 6 now consists of (a) seed-rule equality against the sealed seed values for streams A-C, (b) reproduction of same-version archived first-plan references where they exist (Reacher stream A under commit 63988116 for P0; earlier-audit stream-A references under commit abdced49 for F-version-old), and (c) bitwise determinism of streams A-C across two independent processes on every task.
2. Gate 3 now compares reset states with the case-manifest start states and goal images with the dataset endpoint frames directly, and with archived hashes only where they exist.
3. General rule: a missing archived reference is recorded and does not by itself block formal runs; a definition change stops only the affected conditions.

Unchanged: hypotheses, predictions, conditions, cases, streams, statistics, budget and stopping rule.
