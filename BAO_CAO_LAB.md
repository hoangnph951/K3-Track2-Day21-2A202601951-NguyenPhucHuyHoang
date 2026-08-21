# Báo Cáo Lab MLOps Day 21

## Kết quả thực nghiệm

Mô hình được đánh giá trên tập held-out gồm 500 mẫu. Bốn lần chạy đã được lưu trong MLflow:

| Run | n_estimators | max_depth | min_samples_split | Accuracy | F1 weighted |
|---:|---:|---:|---:|---:|---:|
| 1 | 50 | 3 | 2 | 0.5580 | 0.5185 |
| 2 | 100 | 5 | 2 | 0.5640 | 0.5534 |
| 3 | 200 | 10 | 5 | 0.6440 | 0.6417 |
| 4 | 200 | không giới hạn | 2 | **0.6740** | **0.6730** |

Cấu hình run 4 được chọn vì đạt đồng thời accuracy và F1 cao nhất. Model sâu không giới hạn nắm bắt được quan hệ phi tuyến tốt hơn các cấu hình giới hạn độ sâu. `random_state=42` được cố định để kết quả có thể tái tạo.

## Kiểm thử và chất lượng

- 5/5 tests đã thành công, bao gồm huấn luyện, artifacts, `/health`, `/predict` và kiểm tra input sai kích thước.
- Dữ liệu có đúng 12 features, không có giá trị thiếu và được quản lý bằng DVC.
- Pipeline giữ eval gate ở mức 0.70. Model phase 1 đạt 0.6740 nên bị chặn đúng thiết kế; bản continuous-training trên 5.996 mẫu đạt accuracy **0.7440** và F1 **0.7429**, vượt eval gate.
- Model được upload vào `models/candidates/<git-sha>/model.pkl` và chỉ được promote thành `models/latest/model.pkl` sau khi qua eval gate.

## Khó khăn và cách giải quyết

Starter data giữ tên cột UCI có khoảng trắng nhưng API yêu cầu snake_case, làm model thật từ chối payload dù unit tests ban đầu qua. Script sinh dữ liệu đã được sửa để chuẩn hóa schema. MLflow 2.13 cũng không tương thích với setuptools mới do còn dùng `pkg_resources`; dependencies đã pin `setuptools==80.9.0`. Cuối cùng, kết quả phase 1 thấp hơn ngưỡng 0.70 được giữ nguyên thay vì hạ gate hoặc làm rò rỉ tập eval; continuous training với dữ liệu phase 2 là cơ chế hợp lệ để cải thiện model.

## Bằng chứng cloud cần điền sau triển khai

- GitHub repository: `https://github.com/hoangnph951/K3-Track2-Day21-2A202601951-NguyenPhucHuyHoang`
- GCS bucket: `gs://mlops-lab-2a202601951-hoang-20260821`
- GitHub Actions run: `<điền URL sau khi chạy>`
- VM endpoint: `http://35.238.137.44:8000` (service được khởi động sau pipeline continuous-training)
