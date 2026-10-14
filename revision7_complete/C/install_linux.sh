#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3.12 -c 'import sys,platform; assert sys.version_info[:2]==(3,12) and platform.system()=="Linux" and platform.machine()=="x86_64"'
[[ ! -e venv_ap_linux ]] || { echo 'Use a fresh environment directory; never overwrite/reuse partial install'; exit 2; }
python3.12 -m venv venv_ap_linux
venv_ap_linux/bin/python -m pip install --require-hashes -r linux_cuda_wheels.lock
venv_ap_linux/bin/python -m pip install --no-deps --no-build-isolation ./ap_source/code/ap
venv_ap_linux/bin/python -m pip check | tee pip_check_linux.txt
venv_ap_linux/bin/python -m pip freeze > linux_installed.freeze.txt
venv_ap_linux/bin/python -c 'import torch,importlib.metadata as m; assert m.version("stable-worldmodel")=="0.0.6"; assert m.version("mujoco")=="3.10.0"; assert m.version("dm-control")=="1.0.43"; assert torch.__version__=="2.7.1+cu128"; print(torch.__version__,torch.version.cuda)'
