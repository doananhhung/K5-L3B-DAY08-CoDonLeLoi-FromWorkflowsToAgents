# Báo cáo cá nhân: 2A202603880_DoanAnhHung

## 1. Thông tin thành viên

- Họ tên: Đoàn Anh Hùng
- MSSV: `2A202603880`
- Email: `hungdoan772@gmail.com`
- GitHub: `doananhhung`
- Lớp / Nhóm: `L3B` / `CoDonLeLoi` (làm việc cá nhân)

## 2. Phần việc phụ trách

Phụ trách toàn bộ bài Lab 8 LogiX-VN từ CP1 đến CP5: thiết lập môi trường bằng `uv`, cài đặt 3 shape (`workflow`, `single`, `orchestrator`), viết test bổ sung, chạy crash suite và benchmark, thực hiện Bonus B3 (`swarm_verified`) và viết hồ sơ báo cáo.

## 3. Đóng góp cụ thể

- Commit mã nguồn và báo cáo trên nhánh `main`: `fe29592` (3 shape, test an toàn/crash, `crash.json`, `benchmark.json`), `579a6f8` (Bonus B3 `swarm_verified`, `research_card.md`, `bonus_report.md`)
- Triển khai [workflow.py](../../src/lab8/shapes/workflow.py), [single.py](../../src/lab8/shapes/single.py) và [orchestrator.py](../../src/lab8/shapes/orchestrator.py) tuân theo ranh giới code/model, truyền quote đầy đủ vào `durability.issue_refund`, chuyển tiếp `crash_at` và trả `RunResult` qua `common.finish`.
- Bổ sung [test_shapes_safety_and_crash.py](../../src/tests/test_shapes_safety_and_crash.py) (`24` test case kiểm tra 3 điểm crash, approval sai claim/revoked, stacking max, đơn `cancelled`/`in_transit`, homoglyph/injection và `amount_conflict`).
- Cài đặt Bonus B3 tại [swarm_verified.py](../../src/bonus/swarm_verified.py), bộ 8 claim đối kháng ([cases.jsonl](../../src/bonus/cases.jsonl), [world.json](../../src/bonus/world.json)) và [test_bonus_swarm_verified.py](../../src/tests/test_bonus_swarm_verified.py) (`3` test case).

## 4. Bằng chứng

- Kết quả chạy `uv run python -m pytest -q`: `81 passed, 248 deselected` (gồm `54` test host gốc, `24` test an toàn/crash mới và `3` test bonus B3).
- Kết quả chạy `uv run python -m pytest -q -m student -o addopts=`: `248 passed, 81 deselected` (`62/62` cho mỗi shape).
- Bằng chứng JSON sinh tự động: [crash.json](../../src/reports/crash.json) (`20/20`), [benchmark.json](../../src/reports/benchmark.json) (`4` shape × `14` claim × `5` seed), [bonus_benchmark.json](../../src/reports/bonus_benchmark.json) và [bonus_adversarial.json](../../src/reports/bonus_adversarial.json).
- Run id dẫn chứng: `R-workflow-C-001-s11` (workflow chuẩn), `R-swarm_verified-C-002-s55` (verifier ghi đè `delay_days` từ `5` về `2`).

## 5. Công cụ AI đã dùng

- Công cụ sử dụng: Antigravity (Gemini) để giải thích cấu trúc codebase starter, gợi ý cấu trúc các nhánh trạng thái của 3 shape và rà soát câu chữ tài liệu.
- Cách tự kiểm tra kết quả: tự đối chiếu toàn bộ luật nghiệp vụ trong [business_rules.md](../../docs/business_rules.md) và [contracts.md](../../docs/contracts.md); tự kiểm tra lỗi `unexpected_ledger_rows` phát sinh khi chạy thử [test_shapes_safety_and_crash.py](../../src/tests/test_shapes_safety_and_crash.py) để tách DB độc lập cho từng trial; trực tiếp chạy lại `lab8.smoke`, `pytest`, `lab8.crash_test`, `lab8.benchmark` và đọc file JSON trace trong `src/traces/` để xác nhận không có dữ liệu nhạy cảm lọt ra ngoài.

## 6. Tự đánh giá

- Hoàn thành đầy đủ 3 shape đạt `1.000` pass rate trên bộ public (`0.000000` seed variance), `20/20` crash suite, `0` secret leak và `0` approval bypass trên toàn bộ ca kiểm thử hiện có, cùng phần mở rộng Bonus B3 chứng minh tác dụng của verifier bằng code.
- Phần tự kiểm tra trên `student_drop/` chưa thực hiện được do chưa có thư mục `src/student_drop/` trong bản starter hiện tại; điểm chấm chính thức trên 40 claim ẩn phụ thuộc vào lần chạy của giảng viên.
