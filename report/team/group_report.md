# Báo cáo nhóm — Lab 8 LogiX-VN

Báo cáo tổng hợp kết quả thực hiện bài toán xử lý claim hoàn phí vận chuyển cho công ty giả lập LogiX-VN trên 4 kiến trúc (`workflow`, `single`, `orchestrator`, `swarm`). Số liệu trong báo cáo được trích từ [benchmark.json](../../src/reports/benchmark.json) và [crash.json](../../src/reports/crash.json).

## 1. Thông tin nhóm

- Tên nhóm: `CoDonLeLoi` (làm việc cá nhân, lớp `L3B`)
- Thành viên: xem [TEAM.md](../../TEAM.md) và [2A202603880_DoanAnhHung.md](./2A202603880_DoanAnhHung.md)
- Commit chốt (trùng [decision_adr.md](./decision_adr.md)): `579a6f8` (chứa mã nguồn, test và các báo cáo JSON)

## 2. Mục tiêu và cách tiếp cận

Bài toán đặt ra yêu cầu cài đặt cùng một chữ ký `run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult` trên 3 kiến trúc có mức tự chủ tăng dần (`workflow`, `single`, `orchestrator`) để đối chiếu với kiến trúc tham chiếu `swarm`, qua đó chọn ra phương án ít tự chủ nhất mà vẫn đảm bảo đúng nghiệp vụ, an toàn bí mật và bền vững khi crash.

Trình tự thực hiện chia làm 5 chặng theo [CHECKPOINTS.md](../../CHECKPOINTS.md): kiểm định môi trường `uv` (Python `3.12.13`) và cổng host (`54` test gốc), cài đặt cả 3 shape kèm cơ chế truyền `crash_at`, chạy demo phản ví dụ `buggy_workflow` và crash suite `20/20`, viết bổ sung bộ kiểm thử an toàn và crash `24` ca trong [test_shapes_safety_and_crash.py](../../src/tests/test_shapes_safety_and_crash.py), cuối cùng chạy benchmark đối chứng trên `14` claim public × `5` seed (`11,22,33,44,55`) và thực hiện Bonus B3 (`swarm_verified`).

## 3. Giải pháp

### Kiến trúc 3 shape và ranh giới code / model

Cả 3 shape giữ chung ranh giới an toàn với host ([durability.py](../../src/lab8/durability.py), [policy.py](../../src/lab8/policy.py)):

1. **Shape A (`workflow`, [workflow.py](../../src/lab8/shapes/workflow.py)):** thực thi luồng Python xác định theo thứ tự `get_claim_view` (loại `parent_secret` và header), kiểm tra thiếu `order_id` (`needs_info`), gọi `lookup_order` kiểm tra chủ sở hữu `principal_id` (`escalated`), dùng `compute_compensation` tính quote từ bảng `orders` và policy hiệu lực (`is_current=1`, `effective_date <= 2026-11-15`), rồi gọi `durability.issue_refund` khi `proposal > 0`. `MockLLM` chỉ chạy ở mục `draft`.
2. **Shape B (`single`, [single.py](../../src/lab8/shapes/single.py)):** dùng vòng lặp ReAct qua `lab8.runtime.run_react` với `max_steps=8` và `worker=True`. Ở mỗi bước, hàm `decide` ghi nhận chi phí model qua `MockLLM` vào `Budget` và chỉ gọi các read tool (`get_claim_view`, `lookup_order`, `lookup_refund_history`, `compute_compensation`), không đọc số ngày từ `ticket`. Thao tác ghi `durability.issue_refund` nằm hoàn toàn ngoài vòng ReAct.
3. **Shape C (`orchestrator`, [orchestrator.py](../../src/lab8/shapes/orchestrator.py)):** lớp điều phối lập kế hoạch rồi đóng gói yêu cầu bằng `lab8.handoff.make_handoff` (`contract_version: handoff.v1`, `facts` rỗng không chứa bí mật hay claim thô, `allowed_tools` chỉ gồm `lookup_order`, `lookup_policy`, `lookup_refund_history`) trước khi gọi `run_readonly_investigators`. Sau khi nhận `order` view sạch từ investigator, orchestrator tự chạy `compute_compensation` và gọi `durability.issue_refund`.

### Quản lý quote đầy đủ, crash và ranh giới trace

- Khi `proposal > 0`, cả 3 shape truyền **quote đầy đủ** vào `durability.issue_refund` và giữ `proposal_amount` bằng quote đầy đủ ngay cả khi host từ chối (approval hỏng, approval của claim khác, hoặc đơn đã hoàn đủ như T13), đảm bảo host ghi đúng audit `policy_denied` và trừ đúng phần chênh lệch theo trần từng đơn (T14).
- Tham số `crash_at` được truyền thẳng vào `issue_refund`; khối `except InjectedCrash:` chỉ ghi event `crash` vào trace, gọi `trace.write()` và ném tiếp ngoại lệ để thử nghiệm resume giữ đúng 1 dòng `refund_ledger` và 1 audit `refund_committed`.
- Handoff của `orchestrator` dùng allowlist cứng của [handoff.py](../../src/lab8/handoff.py) thay vì tóm tắt bằng LLM. Trace ghi theo `Trace contract v1` chỉ chứa các event `claim`, `handoff`/`react_step`, `lookup_order`/`investigator`, `quote`, `decision`/`host_refund`, không ghi `ticket` thô, `parent_secret`, `raw_headers`, SĐT, địa chỉ, tên hàng hay ghi chú nội bộ.

## 4. Kết quả

Số liệu benchmark trên `14` claim public (`C-001`..`C-014`) × `5` seed (`11,22,33,44,55`, tổng `70` trial mỗi shape) từ [benchmark.json](../../src/reports/benchmark.json):

| Shape | Pass rate | Pass^5 | Seed min–max | Seed variance | Cost/success (VND mô phỏng) | Mean / p95 steps |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| `workflow` | `1.000` (`70/70`) | `1.000` | `1.000–1.000` | `0.000000` | `28.79` | `3.79 / 4.0` |
| `single` | `1.000` (`70/70`) | `1.000` | `1.000–1.000` | `0.000000` | `39.35` | `8.29 / 9.0` |
| `orchestrator` | `1.000` (`70/70`) | `1.000` | `1.000–1.000` | `0.000000` | `57.00` | `4.71 / 5.0` |
| `swarm` | `0.986` (`69/70`) | `0.929` | `0.929–1.000` | `0.000816` | `49.57` | `2.80 / 3.0` |

- **Crash safety ([crash.json](../../src/reports/crash.json)):** `20/20` kịch bản pass (`CR-01`..`CR-20`, gồm `before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`, `amount_conflict_on_retry`, `retry_without_approval` và `swarm_after_effect_before_checkpoint`).
- **Bộ kiểm thử tự động:** `uv run python -m pytest -q` đạt `81 passed, 248 deselected`; `uv run python -m pytest -q -m student -o addopts=` đạt `248 passed, 81 deselected`; kiểm tra tự động `student_drop/` chưa chạy do thư mục chưa được cung cấp trong bản starter.
- **Quyết định kiến trúc & nghiên cứu:** xem [decision_adr.md](./decision_adr.md) (chọn `workflow`) và [research_card.md](./research_card.md) (ablation `R1`). Phần mở rộng Bonus `B3` đạt `1.000` trên cả `70` trial public và `40` trial đối kháng, xem [bonus_report.md](./bonus_report.md).

## 5. Khó khăn và cách xử lý

1. **Lỗi `unexpected_ledger_rows` khi viết test bổ sung đa claim:** khi viết [test_shapes_safety_and_crash.py](../../src/tests/test_shapes_safety_and_crash.py), hàm kiểm tra `C-STACK`, `C-CANCEL` và `C-TRANSIT` ban đầu dùng chung một tệp SQLite duy nhất. Sau khi `C-STACK` ghi `1` dòng hoàn tiền vào `refund_ledger`, lượt chấm `C-CANCEL` kế tiếp qua `trial_pass` bị báo `unexpected_ledger_rows` vì phát hiện dòng của `C-STACK` trong bảng. Cách xử lý: khởi tạo lại đường dẫn `.sqlite` độc lập (`init_store`) cho từng claim bên trong vòng lặp, đưa toàn bộ `24` test mới về trạng thái xanh.
2. **Làm việc độc lập trên Windows với `uv`:** dự án dùng `src/requirements.txt` và toàn bộ lệnh chạy trong `src/`, không có `pyproject.toml`. Cách xử lý: tạo `src/.venv` bằng `uv venv --python 3.12` (đã nằm trong `.gitignore`), cài thư viện qua `uv pip install -r requirements.txt` và chạy lệnh qua `uv run python -m ...` trong `src/` mà không làm thay đổi cấu trúc tệp dự án.

## 6. Tổng hợp đóng góp

Chi tiết phân công và bằng chứng đóng góp được khai báo trong [TEAM.md](../../TEAM.md) và báo cáo cá nhân [2A202603880_DoanAnhHung.md](./2A202603880_DoanAnhHung.md).

## 7. Hạn chế và hướng cải thiện

- `MockLLM` không phải model sản xuất, nội dung text được băm cố định theo seed và chi phí tính theo đơn giá mô phỏng trong [pricing.yaml](../../src/config/pricing.yaml); `latency` để `unavailable` nên không đo được độ trễ thực tế của vòng ReAct hay investigator so với workflow.
- Kết luận ưu tiên `workflow` phụ thuộc vào tính chất dữ liệu hiện tại của LogiX-VN (mọi sự thật về đơn hàng, thời gian trễ, trạng thái hư hỏng đã nằm sẵn trong cơ sở dữ liệu có cấu trúc). Nếu nghiệp vụ mở rộng sang phân tích ảnh hư hỏng, đối chiếu hóa đơn PDF tự do hoặc cần hỏi đáp đa lượt với khách hàng, hệ thống có thể cân nhắc kiến trúc agent có bước verifier bằng code chặn trước khi ghi sổ.

## 8. Tài liệu tham khảo

- Tài liệu đề bài và đặc tả Lab 8: [README.md](../../README.md), [business_rules.md](../../docs/business_rules.md), [contracts.md](../../docs/contracts.md), [metrics.md](../../docs/metrics.md).
- Yubin Kim et al., *Towards a Science of Scaling Agent Systems*, Google Research / DeepMind / MIT, [arXiv:2512.08296](https://arxiv.org/abs/2512.08296).
