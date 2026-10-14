#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${AP_PYTHON:?Set AP Python}"
"$AP_PYTHON" compare_cases.py --group main --traces outputs/main128/traces --reference reference_step2_original128.jsonl --output comparisons/MAIN128.json
"$AP_PYTHON" compare_cases.py --group appendix --traces outputs/appendix --output comparisons/APPENDIX_42_43_44.json
