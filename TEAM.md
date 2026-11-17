# Team

## Thông tin nhóm

- Tên nhóm: CoDonLeLoi
- Lớp: L3B
- Repo nhóm: `K5-L3B-DAY08-CoDonLeLoi-FromWorkflowsToAgents` (xem [SUBMISSION.md](./SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: `https://github.com/doananhhung/K5-L3B-DAY08-CoDonLeLoi-FromWorkflowsToAgents`, nhánh `main`, commit mã nguồn/benchmark chốt `579a6f8`

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
| 1 | Đoàn Anh Hùng | 2A202603880 | hungdoan772@gmail.com | doananhhung | Toàn bộ bài (3 shape, test, benchmark, B3 và báo cáo) |

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Đoàn Anh Hùng | Thực hiện toàn bộ 3 shape (`workflow`, `single`, `orchestrator`), test bổ sung, benchmark, bonus B3 và báo cáo | `fe29592`, `579a6f8` | `src/tests/test_shapes_safety_and_crash.py`, `src/tests/test_bonus_swarm_verified.py` |

## Cá nhân

Báo cáo cá nhân nằm tại [2A202603880_DoanAnhHung.md](./report/team/2A202603880_DoanAnhHung.md) (giữ nguyên file mẫu [MSSV_HoTen.md](./report/team/MSSV_HoTen.md)).

## 2A202603880_DoanAnhHung

### Phần việc phụ trách

- Triển khai và kiểm chứng cả 3 shape (`workflow`, `single`, `orchestrator`), chạy crash suite 20 điểm và benchmark đối chứng 4 shape, thực hiện topic bonus B3 (`swarm_verified`) và hoàn thiện toàn bộ tài liệu nộp bài.

### Đóng góp cụ thể

- Cài đặt luồng xử lý claim qua [workflow.py](./src/lab8/shapes/workflow.py), vòng ReAct read-only 8 bước qua [single.py](./src/lab8/shapes/single.py), và mô hình orchestrator + handoff allowlist qua [orchestrator.py](./src/lab8/shapes/orchestrator.py).
- Viết bổ sung [test_shapes_safety_and_crash.py](./src/tests/test_shapes_safety_and_crash.py) (`24` test kiểm tra crash 3 điểm, `approval_claim_mismatch`, `approval_revoked`, stacking max, trạng thái đơn không hợp lệ, homoglyph/injection và `amount_conflict`).
- Cài đặt biến thể Bonus B3 [swarm_verified.py](./src/bonus/swarm_verified.py), bộ 8 claim đối kháng [cases.jsonl](./src/bonus/cases.jsonl), [world.json](./src/bonus/world.json) và [test_bonus_swarm_verified.py](./src/tests/test_bonus_swarm_verified.py).

### Bằng chứng

- `src/reports/crash.json` (`crash_safety = 20/20`), `src/reports/benchmark.json` (`280` trials), `src/reports/bonus_benchmark.json`, `src/reports/bonus_adversarial.json`, và lịch sử commit trên nhánh `main`.
