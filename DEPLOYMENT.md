# GCP Deployment Runbook

Tài liệu này chứa các bước còn cần tài khoản GCP và GitHub để hoàn tất triển khai thật.

## 1. Chuẩn bị GCP

Đăng nhập Google Cloud CLI và chọn tài khoản có quyền tạo tài nguyên:

```powershell
gcloud auth login
gcloud auth application-default login
```

Chạy script bootstrap. Thay các giá trị ví dụ bằng project và bucket thực tế:

```powershell
.\scripts\setup_gcp.ps1 `
  -ProjectId "YOUR_PROJECT_ID" `
  -BucketName "YOUR_UNIQUE_BUCKET" `
  -ProvisionVm
```

Script tạo bucket, service account có quyền `roles/storage.objectAdmin` trên bucket, VM và firewall rule TCP 8000. VM sử dụng attached service account nên không cần chép JSON key lên VM.

Project hiện chặn tạo service-account key theo policy. Cấu hình Workload Identity Federation cho GitHub Actions:

```powershell
.\scripts\setup_github_wif.ps1 `
  -ProjectId "YOUR_PROJECT_ID" `
  -GitHubOwner "YOUR_GITHUB_OWNER" `
  -GitHubRepository "YOUR_REPOSITORY_NAME"
```

## 2. Cấu hình và push DVC

```powershell
.\scripts\configure_dvc_remote.ps1 -BucketName "YOUR_UNIQUE_BUCKET"

.\.venv\Scripts\dvc.exe push
```

Xác nhận dữ liệu xuất hiện dưới `gs://YOUR_UNIQUE_BUCKET/dvc`.

## 3. Cấu hình VM

Lấy zone và instance name đã dùng trong script bootstrap:

```powershell
gcloud compute scp deploy/configure_vm.sh mlops-serve:~/configure_vm.sh --zone us-central1-a
gcloud compute scp src/serve.py mlops-serve:~/src/serve.py --zone us-central1-a
gcloud compute ssh mlops-serve --zone us-central1-a --command "chmod +x ~/configure_vm.sh && ~/configure_vm.sh YOUR_UNIQUE_BUCKET"
```

Script VM tạo virtual environment và systemd service nhưng chưa start service cho đến khi model đầu tiên đã được pipeline promote lên `models/latest/model.pkl`.

## 4. SSH deploy key

Tạo key riêng cho GitHub Actions:

```powershell
ssh-keygen -t ed25519 -f "$HOME/.ssh/mlops_deploy" -N '""' -C "github-actions-deploy"
```

Thêm public key vào `~/.ssh/authorized_keys` trên VM. Private key chỉ được lưu trong GitHub Secret `VM_SSH_KEY`.

## 5. GitHub Secrets

Thêm sáu repository secrets:

| Secret | Giá trị |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Provider resource do `setup_github_wif.ps1` in ra |
| `GCP_SERVICE_ACCOUNT` | Email service account do script in ra |
| `CLOUD_BUCKET` | Tên bucket, không gồm `gs://` |
| `VM_HOST` | Public IP của VM |
| `VM_USER` | User Linux trên VM |
| `VM_SSH_KEY` | Nội dung private deploy key |

Không in hoặc chụp màn hình giá trị của các secret.

## 6. Chạy pipeline và kiểm chứng API

Push các thay đổi lên `main` hoặc chạy `workflow_dispatch`. Sau khi bốn jobs thành công:

```powershell
curl.exe "http://VM_IP:8000/health"
curl.exe -X POST "http://VM_IP:8000/predict" `
  -H "Content-Type: application/json" `
  -d '{"features":[7.4,0.70,0.00,1.9,0.076,11.0,34.0,0.9978,3.51,0.56,9.4,0]}'
```

## 7. Dọn tài nguyên sau khi chấm

```powershell
gcloud compute instances delete mlops-serve --zone us-central1-a
gcloud compute firewall-rules delete allow-mlops-serve
gcloud storage rm --recursive "gs://YOUR_UNIQUE_BUCKET/**"
gcloud storage buckets delete "gs://YOUR_UNIQUE_BUCKET"
```

Thu hồi service-account key và xóa các GitHub Secrets sau khi không còn sử dụng.
