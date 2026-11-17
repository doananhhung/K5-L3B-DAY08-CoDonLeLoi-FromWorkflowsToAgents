# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 | R1 |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Google Research / DeepMind / MIT, 2025/2026, *Towards a Science of Scaling Agent Systems* (`https://arxiv.org/abs/2512.08296`, slide 15, 33, 68), loại bằng chứng: benchmark thực nghiệm |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Với các tác vụ có phụ thuộc tuần tự chặt giữa các bước, hệ thống multi-agent không cải thiện tỷ lệ thành công so với luồng đơn giản mà làm tăng chi phí điều phối (coordination overhead) và khuếch đại sai số. |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Kết luận trong bài báo đo trên các benchmark agent cụ thể (lập kế hoạch tuần tự, web navigation, tài chính, lập trình) với các LLM sản xuất được khảo sát; tác vụ có thể tách nhánh đọc độc lập sẽ cho xu hướng khác. |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Trên bài toán claims của LogiX-VN (bước sau phụ thuộc dữ liệu từ bước trước), việc chuyển từ `workflow` sang `orchestrator` (thêm bước lập kế hoạch, handoff và investigator read-only) sẽ giữ `pass_rate` bằng `1.000` nhưng làm `cost_per_success_vnd` tăng khoảng gấp đôi và tăng `mean_steps`. |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Biến giữ cố định: `MockLLM`, read tools, `as_of = 2026-11-15`, seeds `11,22,33,44,55`, corpus `data/public_claims.jsonl` (14 claim), `config/pricing.yaml`, evaluator `lab8.metrics`, mỗi trial 1 SQLite mới. Biến duy nhất thay đổi: topology điều phối (`workflow` so với `orchestrator`, mở rộng so sánh thêm `single` và `swarm`). |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: chi phí điều phối dư thừa trên quy trình tuần tự hoặc rò rỉ context qua handoff; đo bằng `pass_rate`, `pass_5`, `seed_variance`, `cost_per_success_vnd`, `mean_steps`, `p95_steps` và kiểm tra chuỗi cấm trong trace. |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json`
- Run id / file report: [src/reports/benchmark.json](../../src/reports/benchmark.json) (các run id `R-workflow-C-001-s11` .. `R-orchestrator-C-014-s55`)
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: Đúng với giả thuyết trên tập public. Giữa `workflow` và `orchestrator`, `pass_rate` giữ nguyên ở `1.000` (`70/70` trials, `pass^5 = 1.000`, `seed_variance = 0.000000`), nhưng `cost_per_success_vnd` tăng từ `28.79 VND` (`workflow`) lên `57.00 VND` (`orchestrator`, tăng `98.0%`), `mean_steps` tăng từ `3.79` lên `4.71` (`p95_steps` từ `4.0` lên `5.0`), và `mean_tool_calls` tăng từ `2.79` lên `5.57`. Khi tăng tự chủ tự do hơn nữa ở `swarm`, `pass_rate` giảm còn `0.986` (`69/70`), `pass^5` giảm còn `0.929` với `seed_variance = 0.000816` và `cost/success = 49.57 VND`.
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`.
