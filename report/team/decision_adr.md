# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: 579a6f8
- Run id dẫn chứng: R-workflow-C-001-s11 (va 69 trial cua workflow trong src/reports/benchmark.json)
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000-1.000 / 0.000000
- Cost per success (mô phỏng, VND): 28.79
- Crash safety: 20/20 (src/reports/crash.json)
- Secret leak / approval bypass: 0 / 0 (78/78 host gate, 248/248 student matrix)

## Vì sao shape này

So trên cùng tập `14` claim public (`70` trials mỗi shape qua 5 seed `11,22,33,44,55`) trong [benchmark.json](../../src/reports/benchmark.json), cả `workflow`, `single` và `orchestrator` đều đạt `pass_rate = 1.000`, `pass^5 = 1.000` và `seed_variance = 0.000000`. Tuy nhiên, `workflow` đạt mức chi phí mô phỏng trên mỗi thành công thấp nhất (`28.79 VND`, thấp hơn `26.8%` so với `single` ở `39.35 VND` và thấp hơn `49.5%` so với `orchestrator` ở `57.00 VND`) cùng số bước trung bình `3.79` (`p95 = 4.0`). Quy trình xử lý claim tại LogiX-VN có thứ tự phụ thuộc dữ liệu tuyến tính (lấy claim, đối chiếu order theo principal, tính tiền theo policy hiện hành rồi gọi host duyệt và ghi sổ), nên `workflow` đáp ứng đúng nguyên tắc chọn kiến trúc ít tự chủ nhất mà vẫn giải quyết được bài toán.

## Có đáng đổi lấy multi-agent không

Không đáng trong điều kiện bài toán hiện tại. Ở [benchmark.json](../../src/reports/benchmark.json), `orchestrator` tốn chi phí gần gấp đôi (`57.00 VND` so với `28.79 VND`) mà không tăng `pass_rate` (`1.000`), còn `swarm` lại giảm `pass_rate` xuống `0.986` (`pass^5 = 0.929`, `seed_variance = 0.000816`, chi phí `49.57 VND/success`) do tin vào số ngày ghi trên ticket ở seed `55`. Ngay cả khi thử nghiệm thêm lớp verifier bằng code ở Bonus B3 ([bonus_benchmark.json](../../src/reports/bonus_benchmark.json)), `swarm_verified` cũng chỉ đưa độ chính xác về bằng `workflow` (`1.000`) với chi phí `49.00 VND/success`. Quyết định này chỉ đảo ngược khi bài toán chuyển sang xử lý nhiều nguồn bằng chứng phi cấu trúc độc lập cần đọc song song hoặc cần suy luận nhiều bước mà tập luật xác định không bao phủ được, kèm điều kiện chi phí thêm đó giúp nâng pass rate vượt ngưỡng sai số chấp nhận của nghiệp vụ.

## Trace và bằng chứng

Trace của `workflow` ghi `4` nhóm event gọn qua `lab8.trace.Trace`: `claim` (chỉ gồm `claim_id`, `found`, `order_id`), `lookup_order` (đã lọc theo `ORDER_FIELDS`), `quote` (kết quả từ `compute_compensation`), cùng `decision`/`host_refund` hoặc `crash` khi có sự cố. Các field cố ý không ghi vào trace gồm `parent_secret`, `raw_headers`, nội dung `ticket` thô, `approval_id`, cùng các trường PII của bảng `orders` (`phone`, `address`, `internal_note`, `item_name`) để ngăn rò rỉ dữ liệu nhạy cảm và tránh prompt injection lọt vào log. Trong bộ kiểm tra, [test_trace_contract.py](../../src/tests/test_trace_contract.py) và [test_shapes_safety_and_crash.py](../../src/tests/test_shapes_safety_and_crash.py) xác minh mọi file trace tuân theo Trace contract v1 (được tạo mới trong chính lần chạy, khớp `run_id`, có mảng `events`), và công cụ đánh giá áp dụng cơ chế fail-closed với `missing_trace`, `stale_trace`, `invalid_trace`, `trace_run_id_mismatch` để mọi log không đọc được đều bị tính là fail.

## Giới hạn

MockLLM không phải model sản xuất. Latency để `unavailable`. Không sửa JSON cho đủ 0.75. Các con số trên đo trên `14` claim public; kết quả trên `40` claim ẩn (`eval/instructor/`) do máy chấm của giảng viên thực thi độc lập ngoài repo này.
