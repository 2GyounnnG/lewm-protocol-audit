# Changes from PREREG_D1_V1_1.md to PREREG_D1_V1_2.md (2026-10-11 PDT, during formal runs)

Reason: V1.1 gate 3 asked that the post-reset state equal the case-manifest start exactly. For PushT this led the execution to add an adapter that overrides the native library reset (it removes the internal settle step of the native state setter and rewrites the recorded positions, angle and velocity). That override changes PushT's start state relative to the library and to all earlier sealed runs, and it still cannot be exact: the manifest values are float32 and pymunk's centre-of-gravity transform in float64 returns differences of about 2.8e-14 (step2/resume_03/QUESTIONS_FOR_AUTHOR_ZH.md, RESET_PRECISION_DIAGNOSTIC). The 21 PushT unified-protocol conditions were therefore blocked. The V1.1 wording was a drafting error: the intended check is that each task is reset by its native procedure, deterministically, and that the goal is the dataset endpoint frame.

Change: gate 3 now requires the native reset procedure for every task (no adapter override), with (a) two-process bitwise determinism, (b) reproduction of archived references produced with the same procedure where they exist, (c) dtype-cast equality with the manifest start for Reacher, TwoRoom and Cube and a descriptive record of the post-settle offset for PushT, and (d) bitwise goal-frame equality.

Consequences:
- The PushT exact-start override is withdrawn from all formal conditions.
- All PushT unified-protocol trajectories produced so far (partial, under the override) are archived, excluded from every analysis, and every PushT unified-protocol condition is rerun from the start under the native reset.
- Reacher, TwoRoom and Cube results already produced are unaffected: they used the native reset and passed the stricter V1.1 check.

Exposure at the time of this change: the author saw stage-1 aggregates for Reacher, TwoRoom and Cube (official LeWM, h1 and h3, ten streams) at about 01:10 UTC on 12 October 2026. No PushT success rate under the unified protocol has been seen. The change concerns only the reset procedure, defined by reference to the native library and the earlier sealed runs, and does not depend on any outcome.

Unchanged: hypotheses, predictions (including H1b for PushT), conditions, cases, streams, statistics, budget and stopping rule.
