# SPLITUNIFY B2b 重審（R2，定向）

brief-kind: review
task-id: 20260911-SPLITUNIFY-B2-REVIEW-R2
findings-round: R2

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；
findings 用 `## <FAMILY>-R2-P<0-3>-<NN>`，結尾附 **Verdict**。
**禁改碼**；碼證以檔案:行號指名。
審查對象＝commit `e2e4314c`（`momentum/Analysis/event_samples/split_projection.py`、
`momentum/core/split_preview.py`、`tests/momentum/Analysis/test_splitunify_derive.py`、
`tests/golden/splitunify/clusters_oracle.json`、`handoffs/20260911-splitunify-b2b-mutate.py`）。

## 🔴 這是定向重審，不是全面重來

R1 收斂 8 群集（`handoffs/reconcile/20260911-splitunify-b2-review-r1/synth.md` 之 H0–H7）。
codex 判「不可進 B2c：三條 P1」，**三條全部已修**；composer／grok 判「可進」。
本輪只問 **H1–H5 是否閉合**，外加一次負向注入掃描。
非 H1–H5 之意見一律標 P2/P3 並註明「不擋 B2c」。

## R1 → 現況的實質變更

| R1 群集 | 修法 |
|---|---|
| H1 manifest ID 未對帳 | 投影前 `set(event_keys.event_id) == set(manifest.table.event_id)`，**不接受 subset** |
| H2 symbol 只看基數 | 重構為三道有序守衛：plan 須帶 symbol → train/test plan symbol 一致 → 事件 symbol 集合與 plan **相等**；並**刪掉** `len(symbols) > 1`（第三道存在後是死碼） |
| H3 malformed index | 新增 `split_preview.assert_epoch_ms_array`（**逐元素**，混合單位也擋）與 `assert_positional_rows`（`0 <= i < n`、無重複、無負值） |
| H4 兩份單位 policy | 提為公開 `MS_MAGNITUDE_FLOOR`，投影 import 共用 |
| H5 oracle 循環＋mutation 缺口 | clusters oracle 改為依 `w=1/n` 手推並凍結之 JSON（與被測程式無因果）；舊 `split_events` 比對降級為「同形」輔助並註明非 oracle；mutation 9 → **15** 條 |

## 主委已跑的驗收（請複驗）

- `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` → **35 passed**。
- `venv/bin/python handoffs/20260911-splitunify-b2b-mutate.py` → **UNCOVERED=0**（15 條全 rc=1、C0 綠）。
- 回歸 `tests/momentum/core tests/momentum/event_samples` ＋兩支 splitunify ＋
  `tests/api/test_evtlabel_staging.py` → **703 passed**。
- `bash scripts/check_decoupling.sh` → `R2=1 R3=17 R4=3`（逐值等於 baseline）。

## 🔴 必答（只有五題）

1. **H1–H5 逐條閉合了嗎**？逐條回「閉合／未閉合＋ID」。
2. 🔴 **負向注入掃描（本輪最重要）**：請**主動餵 malformed 輸入**，不要只讀碼對照契約。
   R1 的教訓是——H1/H2/H3 三條讀碼看不出來（契約本身沒寫「要檢查身份」），
   只有 codex 做了負向注入才現形。請至少試：
   NaN／NaT 時間戳、`event_keys` 缺欄或欄型別錯、`row_index` 為 float、
   `manifest.table` 缺 `decision_at_ms`、`bucket_ms=0` 或負值、
   `label_end_ms < label_start_ms`、`feature_index` 未排序或有重複值。
   逐條回「已擋／未擋＋實跑輸出」。
3. **刪掉 `len(symbols) > 1` 是對的嗎**？我的理由是「第三道守衛存在後它是死碼，
   留著只會變成殺不掉的 mutant」。有沒有反例（某種輸入下第三道不會觸發但多 symbol 仍通過）？
4. **獨立 oracle 真的獨立嗎**？`tests/golden/splitunify/clusters_oracle.json` 的
   `expected_clusters` 是我依 `w=1/n` 手推的。請驗算，並說它是否足以偵測
   「桶寬換算改錯」「權重公式改錯」兩類。
5. **可否進 B2c**？直接回「可以」或「不可以＋ID」。

## 停輪條件

① 必答 1–5 皆有明確立場；② 必答 2 每一條都有**實跑輸出**（不接受「讀碼認為會擋」）；
③ 三家若分歧，各自寫出判準（看碼證不數人頭）；
④ 禁以「三家零 finding」當停輪——零 finding 須走 sentinel 契約，且**必須**附必答 2 的實跑輸出。

## 本 brief 之前提（逐條標）

fact-verified: 上方所有數字皆為主委實跑，命令逐字如上。

fact-verified: R1 之三條 P1 由 codex 實跑負向注入證明 → `handoffs/20260911-splitunify-b2-review-r1-codex.md` 之 `CODEX-R1-P1-01`..`P1-03`。

assumed: 15 條 mutation ＋ 35 條測試已覆蓋「身份與完整性」這一類的主要失敗模式
← 否證觀測：必答 2 的清單裡有任何一條未被擋。／我跑了：**沒跑**那份清單（它是我列給你們的，
我自己只跑了 mutation 表內那 15 條）。請正面打。

## 🔴 我沒查的

| claim | observable_if_false | reason_code |
|---|---|---|
| `feature_index` 未排序／有重複時的行為 | 成員判定用 set 故不受序影響，但 `test_rows[0]` 會取到非最早的列 | cost |
| `bucket_ms <= 0` 時 `build_time_clusters` 的行為 | 整數除法拋 ZeroDivisionError 或給出荒謬的 cluster id | cost |

## ⚠️ 前置

- **禁改碼**、禁改 `docs/SPLITUNIFY_*.md` 與任何 reconcile synth。
- 不得跑 `pytest tests/governance`；`tests/momentum/Analysis` 全套 17 分鐘，非必要別跑。
- 跑完測試請 `bash scripts/restore_golden_inventory.sh`。收尾清 /tmp workdir（保留 claude-501）。

## 產出

canonical 四欄 findings ＋ **Verdict**（第一句必須是「可進 B2c」或「不可進 B2c：<ID>」）。
