#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <gcs-bucket-name>" >&2
  exit 2
fi

GCS_BUCKET="$1"
VM_USER="$(id -un)"
VM_HOME="$(getent passwd "${VM_USER}" | cut -d: -f6)"

sudo apt-get update
sudo apt-get install -y python3-venv curl

python3 -m venv "${VM_HOME}/mlops-venv"
"${VM_HOME}/mlops-venv/bin/pip" install \
  numpy==1.26.4 \
  fastapi==0.111.0 \
  uvicorn==0.29.0 \
  scikit-learn==1.4.2 \
  pandas==2.2.2 \
  joblib==1.4.2 \
  google-cloud-storage==2.16.0

mkdir -p "${VM_HOME}/models" "${VM_HOME}/src"

sudo tee /etc/systemd/system/mlops-serve.service >/dev/null <<EOF
[Unit]
Description=MLOps Wine Quality Inference API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${VM_USER}
WorkingDirectory=${VM_HOME}
Environment="GCS_BUCKET=${GCS_BUCKET}"
ExecStart=${VM_HOME}/mlops-venv/bin/python ${VM_HOME}/src/serve.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable mlops-serve
echo "VM configured. Upload src/serve.py to ${VM_HOME}/src/serve.py before starting the service."
