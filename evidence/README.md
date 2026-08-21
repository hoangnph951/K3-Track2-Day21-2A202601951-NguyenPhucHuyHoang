# Evidence Checklist

Các file bằng chứng không được chứa key, GitHub Secret hoặc nội dung credential.

- [x] `01-mlflow-runs.png` — MLflow hiển thị bốn thí nghiệm.
- [ ] `02-cloud-storage-dvc.png` — dữ liệu DVC trên GCS.
- [ ] `03-actions-eval-gate.png` — run chứng minh model dưới 0.70 bị chặn.
- [ ] `04-actions-continuous-training.png` — bốn jobs xanh sau commit dữ liệu.
- [ ] `05-api-health-predict.png` — kết quả gọi `/health` và `/predict` trên VM.

Ảnh còn thiếu cần được chụp sau khi cấu hình tài khoản GCP, GitHub Secrets và triển khai VM theo [`DEPLOYMENT.md`](../DEPLOYMENT.md).
