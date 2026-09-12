# SPLITUNIFY D-001 閉合確認 R9（原提出方重驗 R8＋第二家審設計取捨）

brief-kind: closure
task-id: 20260911-SPLITUNIFY-X-REVIEW-R9
findings-round: R9

🔴 **這是閉合確認（closure），不是實作、不是重新全審。禁改碼、禁動 tracked 檔；禁在本 repo commit／push；禁跑 `tests/governance` 全套。** 隔離實驗之指令列與暫存路徑**不得含任何委員家族名稱**（派工閘會誤判為派工）。

🔴 **交件格式（本票已五度因此回頭正規化，請逐字遵守）**：
- findings 一律 `## <FAMILY>-R9-P<0-3>-<NN>` **二級**標題
- 末段三行機械塊：`VERDICT: proceed|blocked`／`BLOCKED-BY:`／`CLOSED:`。**無內容就留空**，不得寫 `none`
- 完成訊號**逐字** `STATUS: DONE`
- 🔴 **戳記若要附，`sha256:` 必須是 `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` 之實際輸出**，不得寫 `PLACEHOLDER`（R8 有一份如此，該戳記無效）

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`；零新 findings 用 sentinel `## <FAMILY>-R9-P3-00`。

## R8 的裁決與本輪修法

`CODEX-R8-P1-01` 成立且經主委抽驗屬實：`_local_ordinals_for_symbol(row_index, symbol_arr, symbol)`（`momentum/core/contracts.py:504-519`）需要全框 `symbol_arr`，而 R7 版之新簽名與 `SplitPlan`（`:377-390`）皆無此向量 ⇒ R7 所寫的「入口整批轉換」**在契約上不可執行**。

🔴 **主委未採 R8 建議之修法方向，改採等價但不同的落點——這是本輪最需要你攻擊的地方**：

| R8 建議 | 主委實際採用 | 理由 |
|---|---|---|
| 在簽名或 plan 契約補入**全框 symbol membership 向量**，入口先轉兩個 plan | **`SplitPlan` 新增 `row_index_local` 欄，由 producer attest**；`derive` 只消費該欄，內部一律不索引 `row_index`；簽名**不收任何全框輸入** | ①三個 producer 皆已持有 local ordinal（`contracts.py:659-661` 之 `train_local`／`test_local`、`ic_split_adapter.py:230-231` 同、`ic_filter_orchestrator.py:631-643` 因單標的而 `row_index` 本即 local），寫入零成本、無需反推 ②建 plan 之處 `symbol_arr` 皆可得（`contracts.py:690`、`ic_split_adapter.py:258`、`ic_filter_orchestrator.py:643-648`），故 attest 可用**同一支具名 helper** 在 producer 端逐值驗證 ③若把 `symbol_arr` 傳進 `derive`，等於在 C1 剛釘死「投影只收 per-symbol 短索引」之後又送回一份全框輸入，R7 的歧義會復發 |

其餘落點：`derive` 缺 `row_index_local` ⇒ fail-closed 且不得回退 `row_index`；Task 8.2 檔案清單補該欄；驗證段新增五條 ASSERT（producer attest 逐值相等、跨 symbol 位置應紅、交錯下各自連續遞增、缺欄應紅、單標的路徑下 `row_index_local` 逐值等於 `row_index`）；變異表新增 `M-SU-D1-11`（attest 不 fail-closed）與 `M-SU-D1-12`（缺欄回退）。

R8 另已確認之事實（本輪不必重查，除非你要推翻）：`derive_event_split_from_plans` 全函式內消費 `row_index` 者僅四處＋指紋一處，**無第六處**（purge 只消費已導出之 `test_start_ms`、cluster 只吃 manifest、summary 只吃已導出結果）。

## 🔴 必答

1. **`CODEX-R8-P1-01` 是否已閉合**？附重驗碼證。
2. **主委改採之落點是否真的等價**：以 `row_index_local` 取代「傳全框向量＋入口轉換」，是否存在 R8 原修法能擋、而本修法擋不住的失效路徑？請具體指出或明說找不到。
3. **並存欄是否構成第二份 row 語意**：`row_index` 與 `row_index_local` 同時住在 `SplitPlan` 內，兩者可能漂移嗎？producer 端 attest（以同一 helper 逐值比對）是否足以封住？若不足，指出漂移可發生之路徑。
4. **單標的路徑之不對稱**：orchestrator 路徑（`:631-643`）之 `row_index` 本來就是 symbol-local，另兩個 producer 則是全框。此不對稱在加入 `row_index_local` 後是否還有殘留風險（例如某消費端假設兩者恆等）？
5. **可否進入實作**（`VERDICT: proceed`）？

## 停輪條件

①必答 1–5 皆有立場；②必答 1–4 逐條附碼證；③**禁以「無 finding」當停輪**；④若仍 blocked，須說明「不改會在 b8 實作或收案時具體怎麼失敗」。

## 前提

fact-verified: `CODEX-R8-P1-01` 已採納並已落 D-001 → 讀 `handoffs/reconcile/20260911-splitunify-x-review-r8/synth.md` 群集表（主委 2026-09-12）
fact-verified: 三個 producer 皆持有 local ordinal，且建 plan 處 `symbol_arr` 皆可得 → `contracts.py:659-661`／`:690`、`ic_split_adapter.py:230-231`／`:258`、`ic_filter_orchestrator.py:631-643`／`:643-648`
fact-verified: `SplitPlan` 為 frozen dataclass 且 `__post_init__` 無未知欄位檢查 → `contracts.py:377-395`（新增帶 default 之欄安全）
fact-verified: 修訂後 D-001 之格式與範本閘通過 → `doc_format_precheck.sh` rc=0、`template_check.sh dext` rc=0
assumed: producer 端 attest 足以封住兩欄漂移 → 否證觀測：必答 3 指出漂移路徑／我跑了: **沒跑**（未實作）
assumed: 以 `row_index_local` 取代入口轉換不損失任何 R8 原修法之防護 → 否證觀測：必答 2 指出 R8 修法能擋而本修法擋不住之路徑／我跑了: **沒跑**（未實作）

## ⚠️ 前置

禁改碼；只讀；收尾清 /tmp workdir（保留 `claude-501`）。
