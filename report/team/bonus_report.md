# Bonus report: B3

- Topic + nguồn (tên, năm, slide): B3 · Verifier/aggregator chống khuếch đại lỗi. Nguồn: Google Research 2026 (Yubin Kim et al., [arXiv:2512.08296](https://arxiv.org/abs/2512.08296)), *Towards a Science of Scaling Agent Systems* (error amplification, slide 17 Evaluator-optimizer, 22 Reflection, 42).
- CLAIM của nguồn (1 câu): Các agent hoạt động độc lập khuếch đại lỗi tới 17,2x trong khi điều phối tập trung giảm hệ số khuếch đại còn 4,4x, và vòng kiểm tra lại giúp chặn sai lệch trước khi chốt kết quả.
- BOUNDARY (model / dataset / setup): Kết quả gốc đo trên LLM sản xuất và các benchmark đa agent có truyền tin liên tiếp; trong Lab 8, lỗi của `swarm` được mô hình hóa xác định qua nhánh `REFERENCE_WEAKNESS` ở `seed % 5 == 0` khi `MockLLM` tin số ngày trên `ticket` thay vì bảng `orders`.
- HYPOTHESIS trên LogiX: Thêm một verifier bằng code vào `swarm` ([swarm_verified.py](../../src/bonus/swarm_verified.py)) để đối chiếu `delay_days`, `status`, `damage_verified` với dữ liệu có cấu trúc trước khi gọi host sẽ đưa `pass_rate` và `pass^5` về `1.000` (bằng `workflow`), nhưng `cost_per_success_vnd` vẫn cao hơn `workflow` do giữ nguyên các bước gọi model và investigator phía trước.
- Biến cố định / biến thay đổi: Cố định `MockLLM`, read tools, `as_of = 2026-11-15`, `pricing.yaml`, seeds `11,22,33,44,55`, evaluator `lab8.metrics`. Biến duy nhất thay đổi: kiến trúc xử lý (`workflow` so với `swarm` và `swarm_verified`).
- Lệnh tái lập (copy-paste được):
  - Bộ public: `python -m lab8.benchmark --shapes workflow,swarm,swarm_verified --extra-shape swarm_verified=bonus.swarm_verified:run_claim --seeds 11,22,33,44,55 --out reports/bonus_benchmark.json`
  - Bộ 8 claim đối kháng tự viết: `python -m lab8.benchmark --shapes workflow,swarm,swarm_verified --extra-shape swarm_verified=bonus.swarm_verified:run_claim --cases bonus/cases.jsonl --world bonus/world.json --seeds 11,22,33,44,55 --out reports/bonus_adversarial.json`
  - Bộ test đơn vị: `python -m pytest -q tests/test_bonus_swarm_verified.py`
- File report + run id: [bonus_benchmark.json](../../src/reports/bonus_benchmark.json), [bonus_adversarial.json](../../src/reports/bonus_adversarial.json); run id minh họa `R-swarm_verified-C-002-s55`, `R-swarm_verified-B-002-s55`.

## Kết quả

Bảng so sánh trên `14` claim public × `5` seed (`70` trials mỗi shape, từ [bonus_benchmark.json](../../src/reports/bonus_benchmark.json)):

| Shape | Pass rate | Pass^5 | Variance | Cost/success (VND mô phỏng) | Mean / p95 steps | Số lần verifier can thiệp |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| `workflow` | `1.000` (`70/70`) | `1.000` | `0.000000` | `28.79` | `3.79 / 4.0` | `0` |
| `swarm` | `0.986` (`69/70`) | `0.929` | `0.000816` | `49.57` | `2.80 / 3.0` | `0` |
| `swarm_verified` | `1.000` (`70/70`) | `1.000` | `0.000000` | `49.00` | `2.83 / 3.0` | `1` (`R-swarm_verified-C-002-s55`) |

Bảng so sánh trên `8` claim đối kháng tự viết (`B-001`..`B-008`, nhãn viết tay trong [cases.jsonl](../../src/bonus/cases.jsonl)) × `5` seed (`40` trials mỗi shape, từ [bonus_adversarial.json](../../src/reports/bonus_adversarial.json)):

| Shape | Pass rate | Pass^5 | Variance | Cost/success (VND mô phỏng) | Mean / p95 steps | Số lần verifier can thiệp |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| `workflow` | `1.000` (`40/40`) | `1.000` | `0.000000` | `30.93` | `4.00 / 4.0` | `0` |
| `swarm` | `0.900` (`36/40`) | `0.500` | `0.040000` | `60.38` | `3.20 / 4.0` | `0` |
| `swarm_verified` | `1.000` (`40/40`) | `1.000` | `0.000000` | `56.35` | `3.60 / 6.0` | `8` (cả `8` claim ở seed `55`) |

- Trên bộ đối kháng, `swarm` sai ở seed `55` trên `4` claim: `3` ca chi sai tiền do ticket nói quá (`B-001`, `B-003`, `B-004`: `status resolved != denied`) và `1` ca từ chối nhầm do ticket nói thiếu (`B-002`: ticket ghi `tre 1 ngay` khi order trễ `4` ngày, `status denied != resolved`). Ở các ca như `B-005` hay `B-008`, verifier vẫn phát hiện sai lệch `delay_days` và ghi đè lại đúng dữ kiện gốc trước khi chuyển xuống host.
- Cả `workflow` và `swarm_verified` giữ `0` secret leak và `0` approval bypass qua [test_bonus_swarm_verified.py](../../src/tests/test_bonus_swarm_verified.py) (`3 passed`).
- Trích đoạn trace minh họa `R-swarm_verified-B-002-s55` (sửa lỗi từ chối nhầm của `swarm`):

```json
{"kind": "model_override", "payload": {"delay_days": 1}},
{"kind": "quote", "payload": {"amount_vnd": 0, "reason": "no_entitlement", "clause_ids": [], "parts": {}}},
{"kind": "verifier_override", "payload": {"mismatches": {"delay_days": {"proposed": 1, "structured": 4}}, "previous_proposal_vnd": 0}},
{"kind": "verifier_quote", "payload": {"amount_vnd": 40000, "reason": "entitled", "clause_ids": ["SHIP-LATE-03"], "parts": {"SHIP-LATE-03": 40000}}}
```

## Kết luận

Kết quả thực nghiệm ủng hộ giả thuyết. Lớp verifier bằng code đưa `swarm` đạt đúng độ chính xác và độ ổn định của `workflow` (`pass_rate = 1.000`, `pass^5 = 1.000`, `variance = 0.000000`) cả trên bộ public lẫn 8 ca đối kháng. Tuy nhiên, `cost/success` của `swarm_verified` (`49.00 VND` trên public, `56.35 VND` trên bộ đối kháng) vẫn cao hơn đáng kể so với `workflow` (`28.79 VND` và `30.93 VND`) vì vẫn phải trả phí cho các lượt gọi `peer`, `parse` và `investigator` trước đó.

Khi verifier bằng code đã có đầy đủ chân lý nền trong `lookup_order` và có quyền thay thế toàn bộ quyết định tính tiền, các agent `swarm` phía trước không còn mang lại giá trị gia tăng cho phần tính tiền; vai trò duy nhất còn lại là soạn thảo văn bản phản hồi hoặc tổng hợp các tín hiệu phi cấu trúc ngoài phạm vi bảng `orders`. Kết luận này có thể đảo ngược nếu tác vụ chứa thông tin quan trọng chỉ tồn tại ở dạng phi cấu trúc (ví dụ ảnh hoặc văn bản không có cột DB tương ứng), khi mà code verifier chỉ kiểm tra tính nhất quán chứ không thể tự tạo quote thay thế toàn phần.

## Giới hạn

MockLLM không phải model sản xuất và lỗi sai của `swarm` được tiêm xác định tại `seed % 5 == 0`. Latency là `unavailable` nên chưa đo được độ trễ thực của vòng sửa verifier. Tập đối kháng gồm `8` claim tự viết là bộ mẫu nhỏ, chỉ đại diện cho các dạng lệch `ticket` đã thiết kế.
