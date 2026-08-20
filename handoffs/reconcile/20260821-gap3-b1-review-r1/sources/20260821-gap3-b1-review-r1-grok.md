# GAP-3 B1 review r1 — grok

task-id: 20260821-GAP3-B1-REVIEW-R1
family: grok
brief: handoffs/20260821-gap3-b1-review-brief.md
diff: `git diff 45fa3774..df45bc82 -- momentum/ tests/ docs/GAP3_EVENT_TODO.D-001.md`

## Verdict：可進 B2（本輪無 BLOCKING）

逐條必答：

1. **B1.0–B1.6 對 TODO**：七 Task 之驗證／邊界／不可做與實作＋測試對得上；白名單外既有檔未改（diff 僅新增 `event_samples/`、`event_import_contract.json`、`tests/momentum/event_samples/`、`docs/GAP3_EVENT_TODO.D-001.md`）。
2. **D-001**：A-01＝誠實前提修正（非降標）；A-02 檔名規約 OK；A-03 `>=` 與 `events=` context keyword 成立。
3. **mutation guard**：M2/M3/M8/M9/M12 為生產路徑 seam；M1/M5/M10 為「斷言會抓到 mutation」型，baseline 斷言仍鎖住生產行為（M10 baseline `_classify_one==unclassifiable` 會在生產改猜時轉紅）。未見假綠縫隙足以列 finding。
4. **§G-2 手算**：整數 ms 字面值與連續網格算術一致（含非整點 as-of 三 TF）。
5. **PIT／資料品質**：無 silent skip；warmup 任一 NaN→`warmup_insufficient_<tf>`；cutoff as-of 無 look-ahead；記帳守恆有測。
6. **可進 B2**：是（無 BLOCKING 必修）。

## 被當成事實的未驗證假設（§0）

| 前提 | 本輪判定 | 證據摘要 |
|------|----------|----------|
| A-01 分層容差＝誠實前提修正 | **成立** | 本機重跑：15 欄中 14×float16／1×float32；末端截斷 14/15 exact、唯 `meta_12h_Volume_PriceChange` rel≈2.9e-4 |
| `entry_after_label_start` 用 `>=` | **成立** | 連續網格 `next_open` entry＝t₀ close＝c2c `label_start`；`>` 會假陰 |
| `events=` 不違 receipt 閉集 | **成立** | context 入 manifest／materialize 層；receipt_schema 未擴欄 |
| T9 名目 `t0−k×TF` | **成立** | ETHUSDT 12h 全段 `diff==H12`（n=1696）；對齊層以實際 bar 複驗 |

## GROK-R1-P3-00

**斷言**: 本輪逐項核對後無 finding——B1.0–B1.6 對 TODO 驗收／D-001 三裁決／mutation 可證偽性／§G-2 手算／PIT 品質均未發現需列 P0–P2 的可證偽缺陷。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 87 passed rc=0；git diff 45fa3774..df45bc82 僅契約／event_samples／tests／D-001；§G-2 重算 T0_100=1708387200000 與 1h/4h/12h cutoff 字面一致且 kline 12h 全連續；A-01 複驗 float16×14＋因果截斷 exact 14/15；warmup 任一 NaN→failures、M2/M12 seam 可證偽。

**來源摘要**: docs/GAP3_EVENT_TODO.md#df04bdabf37d；docs/GAP3_EVENT_TODO.D-001.md#69d05c3d05e6；docs/GAP3_EVENT_SPEC.md#544c2922ef2e；momentum/Analysis/event_samples/alignment.py#fb29aa1feb90；tests/momentum/event_samples/test_mutation_guard.py#e6a324a96632；tests/momentum/event_samples/test_feature_materialization.py#2749aa26d9a1

正文：adversarial 候選（M10 假綠、dedupe 非 UF、causal rtol 未機器強制「14/15 exact」文案）逐一核對後不成立或不達可證偽 finding 門檻——M10 baseline 斷言會抓生產改猜；interval 排序相鄰鏈對 overlap 連通分量等價；A-01 修訂義務即分層 rtol（文案 14/15 為誠實性證據非機器義務）。禁捏造湊數。

ASSUMPTIONS_VERIFIED: A-01 float16／14/15 exact；A-03 `>=` 網格等式；kline 連續；白名單 diff；87 passed
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 87 passed rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT: handoffs/20260821-gap3-b1-review-r1-grok.md
STATUS: DONE
