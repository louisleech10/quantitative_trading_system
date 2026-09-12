# SPLITUNIFY D-001 閉合確認 R8（原提出方重驗 R7 之一條）

brief-kind: closure
task-id: 20260911-SPLITUNIFY-X-REVIEW-R8
findings-round: R8

🔴 **這是閉合確認（closure），不是實作、不是重新全審。禁改碼、禁動 tracked 檔；禁在本 repo commit／push；禁跑 `tests/governance` 全套。** 隔離實驗之指令列與暫存路徑**不得含任何委員家族名稱**（派工閘會誤判為派工）。

🔴 **交件格式（本票已四度因此回頭正規化，請逐字遵守）**：
- findings 一律 `## <FAMILY>-R8-P<0-3>-<NN>` **二級**標題
- 末段三行機械塊：`VERDICT: proceed|blocked`／`BLOCKED-BY:`／`CLOSED:`。**無內容就留空**，不得寫 `none`
- 完成訊號**逐字** `STATUS: DONE`

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`；零新 findings 用 sentinel `## <FAMILY>-R8-P3-00`。

## 你要重驗的（只看自己 R7 提的那一條）

主委修法已落 `docs/SPLITUNIFY_SPEC.D-001.md`（R7 後修訂版）：

| R7 ID | 修法落點 |
|---|---|
| `CODEX-R7-P1-01`（membership 未定義 global→symbol-local 映射） | **D-001-C2 第 4 點**：轉換邊界由「只在指紋計算與比對兩處」**上移至投影入口**——取得該 symbol 之 `feature_index` 後立即把兩個 plan 的 `row_index` 整批轉為 symbol-local ordinal，其後函式內部一律只用 symbol-local，不得再出現全框值。並新增**受覆蓋消費點之封閉清單**①長度閘 `:453-458` ②首尾同源對證 `:473-484` ③成員判定時刻集合 `:486-487` ④測試段起點 `:488` ⑤指紋計算與比對，明寫「R6 版只涵蓋⑤，①～④漏網」。指定複用既有 `momentum/core/contracts.py::_local_ordinals_for_symbol`（`:505-519`）而非另寫。**Task 8.1** 新增兩條交錯 ASSERT（越界不得發生、交錯下之歸屬須等同單獨只跑該 symbol）；**變異表**新增 `M-SU-D1-10`（成員判定跳過入口轉換 ⇒ 應紅） |
| 同上，歧義面 | **D-001-C1 第 1 點**新增「`feature_index_by_symbol` 之數字空間限定」段：釘死其為**該 symbol 自己的 post-trim 短索引**、不可被全框 `row_index` 直接索引；明記 R7 另一家之相反讀法（須為可被全框列號索引之同一 universe）**不採**及其理由（與 C2 第 4 點 `position` ＝ symbol-local ordinal 互斥）；禁以全框索引冒充 per-symbol 索引繞過換算 |

## 🔴 必答

1. **`CODEX-R7-P1-01` 是否已閉合**？附重驗碼證（對讀修訂後之 D-001）。
2. **`CODEX-R6-P1-01`**（你在 R7 判「未閉合」的那條）**是否隨之閉合**？若否，指出還差什麼。
3. **封閉清單是否真的封閉**：D-001-C2 第 4 點列了五個消費 `row_index` 的落點。請獨立讀 `momentum/Analysis/event_samples/split_projection.py` 之 `derive_event_split_from_plans` 全函式，回答**是否存在第六個消費點**（含 purge 段、cluster 段、summary 段）未被該清單涵蓋。這是本輪最重要的一問——主委的清單若漏項，b8 會重演同一類錯誤。
4. **數字空間之裁決是否可執行**：C1 採「per-symbol 短索引」讀法後，`derive` 入口是否還有任何一處**必須**拿到全框索引才能成立（例如跨 symbol 之 cluster 折疊或 purge 窗計算）？若有，指名該處並說明修法。
5. **可否進入實作**（`VERDICT: proceed`）？

## 停輪條件

①必答 1–5 皆有立場；②必答 1–3 逐條附碼證（必答 3 須實際讀完整個函式，不得只讀主委列出的行）；③**禁以「無 finding」當停輪**；④若仍 blocked，須說明「不改會在 b8 實作或收案時具體怎麼失敗」。

## 前提

fact-verified: R7 兩條 finding 全數採納並已落 D-001 → 讀 `handoffs/reconcile/20260911-splitunify-x-review-r7/synth.md` 群集表 W1／W2（主委 2026-09-12）
fact-verified: 主委抽驗你的 R7 碼證屬實且範圍更大 → `split_projection.py:453-458`／`:473-484`／`:486-487`／`:488` 四處皆以全框列號索引該 symbol 之短索引，非僅成員判定一處
fact-verified: 修訂後 D-001 之格式、範本、歸戶與交叉引用皆通過 → `doc_format_precheck.sh` rc=0、`template_check.sh dext` rc=0、`reconcile_cluster_attribution_check.sh` rc=0、`spec_xref_check.sh --synth` 對 R5／R6／R7 三份皆 rc=0
fact-verified: R7 輪債已清 → `debt_clear.sh --round-id --session` rc=0（派工後預期值: 本輪 OPEN）
assumed: C2 第 4 點之五點清單已窮盡 derive 內消費 `row_index` 之處 → 否證觀測：必答 3 指出第六處／我跑了: `awk` 掃該函式 `row_index`／`index_ms`／`train_rows`／`test_rows` 出現行，未見第六類消費形態，但未逐段人工讀完 purge 與 cluster 段
assumed: 採 per-symbol 短索引讀法後無一處必須全框索引 → 否證觀測：必答 4 指名該處／我跑了: **沒跑**（未實作）

## ⚠️ 前置

禁改碼；只讀；收尾清 /tmp workdir（保留 `claude-501`）。
