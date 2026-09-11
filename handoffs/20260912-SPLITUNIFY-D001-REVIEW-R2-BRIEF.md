# SPLITUNIFY SPEC 延伸 D-001 對抗審 R6（R5 修訂後重驗＋補做實質審查）

brief-kind: review
task-id: 20260911-SPLITUNIFY-X-REVIEW-R6
findings-round: R6

🔴 **這是規格審查（review），不是實作。禁改碼、禁動 tracked 檔（含 git checkout／stash）；禁在本 repo commit／push；禁跑 `tests/governance` 全套。** 隔離實驗之指令列與暫存路徑**不得含任何委員家族名稱**（`gate_check` 會誤判為派工）。

🔴 **交件格式（本票已三度因此回頭正規化，請逐字遵守）**：
- findings 一律 `## <FAMILY>-R6-P<0-3>-<NN>` **二級**標題（用 `###` 會被收斂抽取器抽成 0 條）
- 末段三行機械塊：`VERDICT: proceed|blocked`／`BLOCKED-BY:`／`CLOSED:`。**無內容就留空**，不得寫 `none`
- 完成訊號**逐字** `STATUS: DONE`（即使裁決是 blocked 也寫 DONE）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical 四欄。

## 審查對象
- **主檔**：`docs/SPLITUNIFY_SPEC.D-001.md`（R5 後修訂版）
- **BASE 原檔**：`docs/SPLITUNIFY_SPEC.md` @ `b095cc754cb9de26bbf2dd35564db329aca3c98f`
- **上游收斂**：`handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md`（R5 三家 11 條之處置）、`handoffs/reconcile/20260911-splitunify-x-consult-r2/synth.md`（consult 18 條）
- **程序**：`docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1／§2.2
- **相關碼**：`momentum/Analysis/event_samples/split_projection.py`、`momentum/core/contracts.py`、`momentum/Analysis/ic_split_adapter.py`、`momentum/Analysis/ic_filter_orchestrator.py`、`momentum/Analysis/event_samples/pipeline.py`、`scripts/freeze_splitunify_golden.py`

## R5 之處置摘要（本輪要驗的就是這些改對了沒）
| R5 finding | 處置 | D-001 落點 |
|---|---|---|
| producer 指紋寫入點未列 | 採納 | Task 8.2 檔案清單具名三處 producer＋相容 default＋derive 入口仍 fail-closed＋新增「生產路徑建出之 plan 必帶指紋」ASSERT |
| C-4 應列覆寫 | 採納 | 觸及面「覆寫」新增 C-4；D-001-C1 第 1 點給新簽名與薄 wrapper |
| ASSERT 與 C1.1 字面互斥 | 採納 | C1.3 三角相等＋專用訊息；ASSERT 拆為「未給 Mapping」與「給了但 symbol 不一致」兩條 |
| payload 與 §G G-5 不一致 | 採納 | C2 第 1 點對齊四元組，並禁用舊欄名 |
| producer 取哪條 ts 未定 | 採納 | C2 第 4 點：必從該 symbol 之 post-trim `feature_index` 取 |
| int 強制／重複/空 plan／函式未點名 | 採納 | C2 第 2、3、5 點 |
| 身分保證過歸 | 採納 | C1 第 2 點末段改為「指紋證時刻、symbol 身分由三角相等承擔」 |
| C1.4 無 mutation | 採納 | 新增 `M-SU-D1-07`＋對應 ASSERT |
| 上游收斂檔未蓋章 ⇒ 主張不審 | **駁回** | 見 R5 synth「本輪程序記錄」第 5 點（規則原文管的是動工、非唯讀審查；同一家先前三輪相同情境皆照審） |

## 🔴 必答
1. **你自己 R5 提的每一條**：逐條回「已閉合／未閉合」＋重驗碼證。（R5 未提 finding 者跳過此題。）
2. 🔴 **實質審查（若你 R5 只提程序阻塞而未實質審查，本題為必做）**：對 D-001 修訂版逐項給立場——①類別判定 D vs R；②觸及面四欄錨點是否逐字存在且無漏宣告；③hash 不變式；④指紋定義可重算性（含 `int` 強制、空 plan、重複 `position`、正規化函式點名是否足夠封閉）；⑤golden 重凍與獨立 oracle；⑥ASSERT 可證偽性；⑦mutation 對照（含新增之 `M-SU-D1-07`）；⑧範圍切割（排除 `D1`／`R-5`／`SU-RESID-2` 是否留下上線即不自洽的中間態）。
3. **駁回之重驗**：R5 之程序阻塞主張被駁回，理由與碼證見 R5 synth 第 5 點。①接受／不接受＋理由；②**反面**：若你仍主張須先蓋章，請指出「唯讀規格審查」落在規則原文哪一個字上。
4. **新引入的面**：C-4 覆寫後，單標的舊呼叫式改走薄 wrapper——①此 wrapper 是否會成為「第二份判定邏輯」的入口？②`pipeline.py` 現行呼叫要改成哪一式才不會兩套並存？
5. **可否進入實作**（`VERDICT: proceed`）？

## 停輪條件
①必答 1–5 皆有立場；②必答 2 之八項逐項有答（不得整段略過）；③**禁以「三家零 finding」當停輪**；④P0/P1 須說明「不改會在 b8 實作或收案時具體怎麼失敗」。

## 前提
fact-verified: R5 三家共 11 條、10 條實質全採納、1 條程序性駁回 → 讀 `handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md` 群集表（主委 2026-09-12）
fact-verified: 生產碼目前無 `row_time_fingerprint` 欄 → `grep -rn row_time_fingerprint momentum/ --include='*.py'` 命中 0
fact-verified: BASE C-4 簽名逐字為單一 `train_plan: SplitPlan`／`test_plan: SplitPlan`／`feature_index: pd.Index` → `git show b095cc75:docs/SPLITUNIFY_SPEC.md` 之 C-4 區塊
fact-verified: §G G-5① 與 `scripts/freeze_splitunify_golden.py` 皆用四元組 `(position, feature_ts_ms, symbol, base_universe_hash)` → 對讀該節與該腳本
fact-verified: R5 輪債已清 → `bash scripts/debt_ledger.sh --has-open` rc=0（派工後預期值: rc=1——本輪 OPEN，非 2）
assumed: D-001 修訂後觸及面宣告仍與原檔逐字對得上（C-4 新列入覆寫） ⇒ 否證觀測：必答 2② 對讀時任一錨點在原檔找不到逐字相同 heading。／我跑了：**只對新增的 C-4 一條做過 grep，其餘沿用 R5 兩家已對讀之結論**
assumed: 薄 wrapper 不構成第二份判定邏輯 ⇒ 否證觀測：必答 4① 指出 wrapper 內必須有獨立分支才能成立之情形。／我跑了：**沒跑**（尚未實作）

## ⚠️ 前置
禁改碼；只讀；收尾清 /tmp workdir（保留 `claude-501`）。
