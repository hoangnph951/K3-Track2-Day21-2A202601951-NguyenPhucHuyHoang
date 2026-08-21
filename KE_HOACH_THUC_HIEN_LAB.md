# Kế Hoạch Thực Hiện Lab MLOps Day 21

## 1. Mục tiêu

Triển khai hoàn chỉnh quy trình MLOps cho bài toán Wine Quality:

1. Theo dõi thí nghiệm cục bộ bằng MLflow.
2. Phiên bản hóa dữ liệu bằng DVC và Google Cloud Storage.
3. Xây dựng pipeline GitHub Actions theo chuỗi `Test → Train → Eval → Deploy`.
4. Phục vụ mô hình trên Google Compute Engine qua FastAPI.
5. Tự động huấn luyện và triển khai lại khi có dữ liệu mới.

Kế hoạch ưu tiên hoàn thành chắc chắn toàn bộ 80 điểm bắt buộc trước khi thực hiện các phần bonus. Tổng thời gian dự kiến khoảng **9–12 giờ**, chưa tính thời gian chờ cloud và GitHub Actions.

## 2. Giả định và hiện trạng

- Chọn **GCP** vì code khung, dependencies và tài liệu đang sử dụng `dvc[gs]`, `google-cloud-storage` và GCS.
- Repository đang ở nhánh `main`, worktree sạch và đã cấu hình remote `origin`.
- Các file [`src/train.py`](src/train.py), [`src/serve.py`](src/serve.py), [`tests/test_train.py`](tests/test_train.py) và [`.github/workflows/mlops.yml`](.github/workflows/mlops.yml) vẫn còn các phần `TODO`.
- Chưa có thư mục dữ liệu, cấu hình DVC, model, metrics hoặc MLflow database.

## 3. Kế hoạch triển khai

| Giai đoạn | Công việc chính | Điều kiện hoàn thành | Ước tính |
|---|---|---|---:|
| 0. Chuẩn bị | Dùng Python 3.10, tạo `.venv`, cài dependencies; xác nhận tài khoản GCP, billing và CLI; chạy `generate_data.py` | Có 2.998 mẫu train phase 1, 500 mẫu eval, 2.998 mẫu phase 2; đúng 12 features và cột `target` | 45–60 phút |
| 1. Training | Hoàn thiện `src/train.py`: đọc dữ liệu, train RandomForest, tính accuracy/F1, log MLflow, lưu metrics và model | Sinh `outputs/metrics.json`, `models/model.pkl`; hàm `train()` trả về accuracy | 60–90 phút |
| 2. MLflow | Chạy ít nhất ba cấu hình tham số, so sánh trên UI và chọn cấu hình tốt nhất | MLflow có ít nhất ba runs, mỗi run đủ params, accuracy, F1; đã chụp ảnh UI | 45–60 phút |
| 3. Tests và API | Hoàn thiện ba test huấn luyện; hoàn thiện tải model, `/health`, `/predict` và kiểm tra đúng 12 features | `pytest tests/ -v` thành công; API trả đúng JSON và lỗi 400 khi input sai | 60–90 phút |
| 4. GCP và DVC | Tạo bucket, service account quyền `storage.objectAdmin`; `dvc init`, track ba CSV và `dvc push` | Cloud Storage có dữ liệu DVC; Git chỉ chứa file `.dvc`, không chứa CSV hoặc key | 90–150 phút |
| 5. VM serving | Tạo GCE VM, mở cổng 8000, cài runtime, cấu hình systemd và SSH deploy key | Service tải được model từ bucket và có thể tự khởi động lại | 60–120 phút |
| 6. CI/CD | Hoàn thiện chuỗi `Test → Train → Eval → Deploy`, cấu hình năm GitHub Secrets | Bốn jobs xanh; model tại `models/latest/model.pkl`; eval chặn khi accuracy dưới 0.70 | 90–150 phút |
| 7. Continuous training | Thêm phase 2, cập nhật DVC, push dữ liệu rồi mới push Git | Train tăng 2.998 → 5.996 mẫu; commit dữ liệu tự kích hoạt bốn jobs; model mới được deploy | 45–60 phút |
| 8. Nộp bài | Thu thập ảnh, bảng so sánh metric và viết báo cáo một trang | Đủ URL repo, ảnh MLflow, Actions, Cloud Storage, kết quả curl và báo cáo | 30–45 phút |

## 4. Chi tiết từng giai đoạn

### Giai đoạn 0 — Chuẩn bị môi trường

1. Kiểm tra Python 3.10+, Git và Google Cloud CLI.
2. Tạo và kích hoạt môi trường ảo `.venv`.
3. Cài dependencies từ `requirements.txt`.
4. Chạy `python generate_data.py`.
5. Kiểm tra số dòng, schema và phân phối nhãn của ba tập dữ liệu.

Điều kiện chuyển bước:

- `data/train_phase1.csv`: 2.998 mẫu.
- `data/eval.csv`: 500 mẫu.
- `data/train_phase2.csv`: 2.998 mẫu.
- Không có dữ liệu thiếu hoặc sai schema.

### Giai đoạn 1 — Hoàn thiện huấn luyện

Hoàn thiện [`src/train.py`](src/train.py) để:

1. Đọc tập train và eval.
2. Tách 12 đặc trưng và cột `target`.
3. Khởi tạo `RandomForestClassifier` với tham số từ `params.yaml` và `random_state=42`.
4. Tính `accuracy` và weighted `f1_score`.
5. Ghi params, metrics và model vào MLflow.
6. Ghi `outputs/metrics.json`.
7. Lưu `models/model.pkl`.
8. Trả về accuracy dạng `float`.

### Giai đoạn 2 — Thí nghiệm MLflow

Chạy tối thiểu ba cấu hình; khuyến nghị bốn cấu hình sau:

| Run | `n_estimators` | `max_depth` | `min_samples_split` |
|---|---:|---:|---:|
| A | 50 | 3 | 2 |
| B | 100 | 5 | 2 |
| C | 200 | 10 | 5 |
| D | 200 | `null` | 2 |

Quy tắc lựa chọn:

1. Chọn run có accuracy cao nhất.
2. Nếu accuracy bằng nhau, ưu tiên F1 cao hơn.
3. Nếu hai metric gần tương đương, chọn mô hình đơn giản hơn.
4. Cập nhật cấu hình thắng vào `params.yaml`.
5. Chụp MLflow UI thể hiện ít nhất ba runs, params và cả hai metrics.

### Giai đoạn 3 — Tests và FastAPI

Hoàn thiện [`tests/test_train.py`](tests/test_train.py):

- Kiểm tra `train()` trả về `float` trong `[0, 1]`.
- Kiểm tra `outputs/metrics.json` tồn tại và có đủ hai metrics.
- Kiểm tra `models/model.pkl` được tạo.

Hoàn thiện [`src/serve.py`](src/serve.py):

- Tải `models/latest/model.pkl` từ GCS khi ứng dụng khởi động.
- `GET /health` trả `{"status": "ok"}`.
- `POST /predict` chỉ chấp nhận đúng 12 features.
- Trả `prediction` dạng số nguyên và nhãn `thap`, `trung_binh` hoặc `cao`.
- Trả HTTP 400 khi số features không hợp lệ.

Chạy kiểm tra cục bộ trước khi thiết lập cloud:

```bash
pytest tests/ -v
```

### Giai đoạn 4 — GCP và DVC

1. Tạo GCS bucket có tên duy nhất.
2. Tạo service account riêng cho lab.
3. Chỉ cấp `roles/storage.objectAdmin` trên bucket.
4. Khởi tạo DVC và cấu hình GCS remote.
5. Đưa credential path vào `.dvc/config.local`, không commit credential.
6. Theo dõi ba file CSV bằng DVC.
7. Commit các file `.dvc` và cấu hình remote an toàn.
8. Chạy `dvc push` và xác nhận object xuất hiện trên Cloud Storage Console.

Tuyệt đối không commit `sa-key.json` hoặc nội dung bất kỳ secret nào.

### Giai đoạn 5 — Triển khai VM

1. Tạo GCE VM và gắn firewall rule cho TCP 8000.
2. Tạo Python virtual environment trên VM và cài dependencies phục vụ inference.
3. Tạo các thư mục `~/models` và `~/src`.
4. Đưa `serve.py` và GCP credential lên VM.
5. Cấu hình systemd service `mlops-serve`.
6. Tạo SSH deploy key dành riêng cho GitHub Actions.
7. Xác nhận user deploy có thể restart service qua `sudo`.

### Giai đoạn 6 — GitHub Actions CI/CD

Thêm các GitHub Secrets sau. Project có policy chặn service-account key nên dùng Workload Identity Federation:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`
- `CLOUD_BUCKET`
- `VM_HOST`
- `VM_USER`
- `VM_SSH_KEY`

Hoàn thiện [`.github/workflows/mlops.yml`](.github/workflows/mlops.yml):

1. **Test:** cài dependencies và chạy pytest.
2. **Train:** xác thực GCP, `dvc pull`, train, đọc accuracy, upload model và lưu metrics artifact.
3. **Eval:** chuyển accuracy sang `float`; kết thúc lỗi nếu accuracy dưới `0.70`.
4. **Deploy:** SSH vào VM, restart systemd service và retry `/health` cho đến khi thành công hoặc hết thời gian.

Nên bổ sung các trigger cho workflow, tests và dependencies để thay đổi CI tự kiểm chứng được:

```yaml
paths:
  - "data/**.dvc"
  - "src/**.py"
  - "tests/**.py"
  - "params.yaml"
  - "requirements.txt"
  - ".github/workflows/mlops.yml"
```

Kiểm tra tích hợp:

- Bốn jobs đều xanh.
- Cloud Storage có `models/latest/model.pkl`.
- `/health` trả trạng thái OK.
- `/predict` trả kết quả hợp lệ.
- Eval gate đã được kiểm chứng có thể chặn deploy dưới ngưỡng.

### Giai đoạn 7 — Continuous training

1. Lưu metrics của lần chạy với 2.998 mẫu.
2. Chạy `python add_new_data.py` đúng một lần.
3. Xác nhận train mới có 5.996 mẫu.
4. Chạy `dvc add data/train_phase1.csv`.
5. Commit riêng `data/train_phase1.csv.dvc` với message thể hiện đây là thay đổi dữ liệu.
6. Chạy `dvc push` trước.
7. Sau khi dữ liệu đã có trên cloud, chạy `git push origin main`.
8. Xác nhận commit dữ liệu tự kích hoạt toàn bộ pipeline.
9. Tải metrics artifact và so sánh kết quả trước/sau.
10. Gọi lại `/health` và `/predict` để xác nhận model mới đã được phục vụ.

Không chạy `add_new_data.py` nhiều lần vì script không có tính idempotent và sẽ ghép trùng dữ liệu.

### Giai đoạn 8 — Bằng chứng và nộp bài

Chuẩn bị các đầu ra theo đúng thứ tự:

1. URL repository GitHub công khai.
2. Ảnh MLflow UI có ít nhất ba runs.
3. Ảnh GitHub Actions có bốn jobs xanh ở Bước 2.
4. Ảnh GitHub Actions ở Bước 3, hiển thị commit dữ liệu đã kích hoạt run.
5. Ảnh terminal gọi `/health` và `/predict`.
6. Ảnh Cloud Storage Console có dữ liệu DVC và model.
7. Báo cáo không quá một trang A4, gồm:
   - Bộ siêu tham số được chọn và lý do.
   - Bảng so sánh accuracy và F1 trước/sau khi thêm dữ liệu.
   - Khó khăn gặp phải và cách giải quyết.

Không để key, secret hoặc nội dung credential xuất hiện trong ảnh hay báo cáo.

## 5. Các điểm kiểm soát quan trọng

- Trên PowerShell, sử dụng:

  ```powershell
  $env:MLFLOW_TRACKING_URI = "sqlite:///mlflow.db"
  ```

  thay cho cú pháp Bash `export` trong tài liệu.

- Luôn chạy `dvc push` trước `git push` khi cập nhật dữ liệu.
- Không dùng chung service-account key cho mục đích khác.
- Health check deploy nên retry nhiều lần thay vì chỉ chờ cố định năm giây.
- Chụp bằng chứng ngay sau mỗi checkpoint.
- Giữ commit dữ liệu ở Bước 3 tách biệt để chứng minh continuous training.
- Sau khi chấm bài, tắt hoặc xóa VM, firewall rule và thu hồi service-account key để tránh chi phí.

## 6. Chiến lược bonus

Chỉ thực hiện sau khi toàn bộ 80 điểm bắt buộc đã ổn định. Thứ tự khuyến nghị:

1. Cảnh báo lệch phân phối nhãn.
2. Báo cáo hiệu suất tự động.
3. Hỗ trợ nhiều thuật toán.
4. Chặn hoặc rollback model kém hơn phiên bản đang chạy.
5. MLflow từ xa qua DagsHub.

Hai bonus đầu có tỷ lệ điểm trên công sức tốt nhất. Cơ chế promotion/rollback nên được thiết kế sao cho model chỉ được đưa vào `models/latest/` sau khi vượt qua eval gate.

## 7. Tài liệu đối chiếu

- [Rubric và hướng dẫn nộp bài](README.md#rubric-chấm-điểm)
- [Bước 1 — MLflow](tasks/buoc-1.md)
- [Bước 2 — CI/CD và DVC](tasks/buoc-2.md)
- [Bước 3 — Continuous training](tasks/buoc-3.md)

## 8. Tiến độ thực tế

- [x] Tạo môi trường Python và cài dependencies.
- [x] Sinh và kiểm tra ba tập dữ liệu.
- [x] Hoàn thiện training, MLflow tracking, metrics, report và model artifact.
- [x] Chạy bốn thí nghiệm và chọn tham số tốt nhất.
- [x] Hoàn thiện năm unit/API tests.
- [x] Hoàn thiện FastAPI và smoke test với model thật.
- [x] Khởi tạo DVC và tạo ba file con trỏ dữ liệu.
- [x] Hoàn thiện workflow Test → Train → Eval → Deploy.
- [x] Tạo script bootstrap GCP, DVC và VM runbook.
- [x] Xác thực GCP, tạo bucket/VM và `dvc push`.
- [x] Cấu hình Workload Identity Federation, VM deploy key và GitHub Secrets.
- [ ] Chạy pipeline thật.
- [ ] Thực hiện commit continuous-training và thu thập bằng chứng cloud.
