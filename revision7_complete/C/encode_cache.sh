#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${AP_PYTHON:?Set independent AP Python}"
: "${AP_GPU_SSH_AUTHORIZED:?Author SSH required}"
"$AP_PYTHON" verify_inputs.py
"$AP_PYTHON" gpu_run.py -m anchored_planning encode-cache --assets assets.remote.json --task reacher --device cuda:0 --batch-size 128
"$AP_PYTHON" -c 'import hashlib,json; from pathlib import Path; p=Path("assets/cache/reacher.npy"); h=hashlib.sha256(); f=p.open("rb"); [h.update(b) for b in iter(lambda:f.read(8388608),b"")]; Path("CACHE_SHA256.json").write_text(json.dumps({"sha256":h.hexdigest(),"bytes":p.stat().st_size}))'
