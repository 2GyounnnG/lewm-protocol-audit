#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${AP_PYTHON:?Set independent AP Python}"
: "${AP_CPU_ASSETS:?Set JSON with SHA-verified full dataset and retrieval cache}"
"$AP_PYTHON" -m anchored_planning inspect-assets --task reacher --assets "$AP_CPU_ASSETS"
"$AP_PYTHON" -m anchored_planning evaluate --task reacher --assets "$AP_CPU_ASSETS" --device cpu --root protocol_main128 --study main --limit 1 --output outputs/cpu_full_smoke
