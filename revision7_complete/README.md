# Revision 7 complete supplement: records and code

Additive A/B analyses and C native AP Reacher replication. The published base archive remains https://doi.org/10.5281/zenodo.23350373; this supplement is prepared for a separate new-version draft and is not yet archived there. No manuscript PDF/source, model weights, input HDF5 datasets, environment secrets or latent-cache body are distributed.

- A: saved-record threshold/window sensitivity, bootstrap contrasts and case differences.
- B: static code audit, repository commits and exact source excerpts. No claim that another paper's results are wrong.
- C: native AP code at 984327424ca7a2e52c75a8279197750d9d0b7c8e, protocol/case lists, independent Linux lock, asset URLs/SHA, 328 formal/diagnostic trajectories, TECH/pilots, renderer reset images, statistics and return evidence.

## Main findings

Native OSMesa: 97/128 = 75.78125% [67.96875,82.8125], matching the paper's aggregate (12 case outcomes differ, six each direction). Fixed first50: OSMesa37/50 vs EGL49/50, paired EGL minus OSMesa24.0pp [12.0,36.0]. The EGL run reproduces all50 historical full action arrays and first-hit steps. The historical97.7% value remains a valid record of the earlier EGL launch. The renderer diagnostic uses a300-step budget and is separate from common50-step comparisons. Appendix case-sampling seeds42/43/44 use50 cases each, offset24,budget50: 74%,66%,70%; they are not compared to the75.8% main-table rate.

## CPU verification

Python3.12 and NumPy1.26.4 are sufficient. Run `python C/recompute_C.py --root C --output /tmp/recomputed_C.json`. This uses saved outcomes and the unchanged frozen statistics function (5,000 bootstrap draws,seed20261011), not a model or simulator. `--verify-traces` additionally validates all328 outcomes against full raw traces and all50 EGL action arrays against the old reference, and needs the complete archive. The GitHub small-file mirror omits raw traces.

A/B scripts preserve original paths and provenance; run in a working copy, adjusting input roots to the base archive layout. Existing base numeric results were not replaced. Historical receipts may refer to local directories or assets intentionally excluded from this public supplement; MATERIALS_MANIFEST.json is the integrity map for this distribution.

## GPU reproduction

C/RUN_PROTOCOL_ZH.md and C/THREE_SEED_PROTOCOL_APPROVED.json define separate main and appendix protocols. Use C/linux_cuda_wheels.lock and C/LINUX_DOWNLOAD_MANIFEST.json, obtain data/checkpoints from their source under their terms, check SHA, build the native cache, then complete TECH. C/evidence records the actual environment and two/four-worker gate. Formal selection was two workers on two physical GPUs; four matched trajectories but exceeded the90% memory gate. Runtime paths in shell launchers refer to the original /workspace/ap_revision7 layout and must be mapped in a new workspace. No resumption of the completed instance is needed.

## License

New audit code: MIT (LICENSE). Derived records and documentation: CC BY4.0 (LICENSE-DATA). Upstream AP source retains C/ap_source/LICENSE; audited excerpts retain their upstream notices and licenses. No license is granted over externally obtained checkpoints/input datasets. Full upstream notices are included in THIRD_PARTY_LICENSES.
