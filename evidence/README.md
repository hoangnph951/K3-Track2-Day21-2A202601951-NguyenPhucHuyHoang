# Evidence Checklist

Các file bằng chứng không được chứa key, GitHub Secret hoặc nội dung credential.

- [x] `01-mlflow-runs.png` — MLflow hiển thị bốn thí nghiệm.
- [x] `02-cloud-storage-dvc.png` — dữ liệu DVC và model trên GCS, xác minh bằng `gcloud`.
- [x] `03-actions-eval-gate.png` — run chứng minh model dưới 0.70 bị chặn.
- [x] `04-actions-continuous-training.png` — push commit dữ liệu tự kích hoạt bốn jobs xanh.
- [x] `05-api-health-predict.png` — kết quả gọi `/health` và `/predict` trên VM.

Các artifacts `phase1/`, `phase2/` và `continuous-push/` chứa metrics/report tải trực tiếp từ GitHub Actions.
