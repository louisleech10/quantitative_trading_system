# SPLITUNIFY SPEC 延伸 D-001 對抗審 R1（per-symbol 投影＋逐列指紋）

brief-kind: review
task-id: 20260911-SPLITUNIFY-X-REVIEW-R5
findings-round: R5

🔴 **這是規格審查（review），不是實作。禁改碼、禁動 tracked 檔（含 git checkout／stash）；禁在本 repo commit／push；禁跑 `tests/governance` 全套。** 隔離實驗之指令列與暫存路徑**不得含任何委員家族名稱**（`gate_check` 會誤判為派工）。
🔴 交件檔 findings 一律用 **`## <FAMILY>-R5-P<0-3>-<NN>` 二級標題**（本輪前一次 consult 有一家用 `###` 三級，導致收斂抽取器抽到 0 條、硬閘擋住，且修正後又撞「交件後不得改動」閘）。末段三行機械裁決塊只准值集（`VERDICT: proceed|blocked`／`BLOCKED-BY:`／`CLOSED:`）；**`STATUS: DONE` 逐字**。

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical 四欄。

## 審查對象
- **主檔**：`docs/SPLITUNIFY_SPEC.D-001.md`（新，本輪唯一標的）
- **BASE 原檔**：`docs/SPLITUNIFY_SPEC.md` @ `b095cc754cb9de26bbf2dd35564db329aca3c98f`（特別是 `### C-2`、`**Task 3.2 …**`、`## §N`、`### C-4`、`## §G`、`## §V`）
- **上游收斂**：`handoffs/reconcile/20260911-splitunify-x-consult-r2/synth.md`（三家 consult 18 條）
- **程序**：`docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1／§2.2
- **相關碼**：`momentum/Analysis/event_samples/split_projection.py`、`momentum/core/contracts.py`、`momentum/Analysis/ic_split_adapter.py`、`momentum/Analysis/ic_filter_orchestrator.py`、`momentum/Analysis/event_samples/event_split.py`

## 🔴 必答（每題「立場＋碼證」，正反各一句）
1. **類別判定**：本檔自稱 **D 延伸**，理由是原檔 `Task 3.2` 已自寫「存活至：per-symbol 投影實作後**改寫**為支援分支」「不得只刪 raise」。①此理由是否成立？②**反面**：`C-2` 的「多 symbol 批一律 fail-closed」被改成「以 per-symbol 結構投影」，這算不算與原檔字面互斥而應升 **R**？（你若判 R，請指出哪一句互斥。）
2. **觸及面宣告**：四欄（新增／覆寫／依賴／不觸）之錨點是否**逐字**存在於原檔？有無「實際會動到、卻未宣告」之面？（請實際對讀原檔那幾個 heading。）
3. **hash 不變式**：D-001-C1 第 2 點寫「跨 symbol 允許共用同一字面 joint hash、禁把互異寫成閘」。①碼證是否支持？②**反面**：放寬之後，靠什麼保證兩個 symbol 的 plan 不會互相冒充？（本檔答案是「逐 symbol 同源對證」——夠不夠？）
4. **指紋定義可重算性**：D-001-C2 第 1 點之 payload 定義（epoch ms、依 row_index 排序、`json.dumps(sort_keys=True, separators=(",",":"))`、sha256）是否**足以**讓兩端獨立重算出相同值？①指出任何會使兩端不一致的未定義處（型別、NaT、重複 row_pos、空 plan）；②**反面**：若你認為已足夠，說明為何 `_coerce_timestamp_array` 的秒／毫秒歧異不會漏進來。
5. **golden 重凍**：D-001-C2 第 4 點要求「改前／改後逐值對照重凍、不得只更新 hash」。①這是否足以防止「把錯誤一起凍進去」？②**反面**：有沒有更便宜且同樣可證偽的作法？
6. **ASSERT 可證偽性**：Task 8.1／8.2／8.3 之固定文法斷言，逐條檢查「改壞了會不會紅」。指出任何一條即使實作錯誤也會綠的。
7. **mutation 對照**：`M-SU-D1-01`～`06` 是否每條都對應到**會真紅**的測試？有無應加而未加者（例如跨 symbol row_index 混用）？
8. **範圍切割**：本檔明示不含 `D1`／`R-5`／`SU-RESID-2`。①此切割是否留下「本批上線後即失效」的中間態？②**反面**：是否有任何一條其實非做不可、否則 b8 本身不自洽？
9. **可否進入實作**（`VERDICT: proceed`）？

## 停輪條件
①必答 1–9 皆有立場且正反各一句；②必答 2、4 附實際對讀或重算；③**禁以「三家零 finding」當停輪**；④P0/P1 須說明「不改會在 b8 實作或收案時具體怎麼失敗」。

## 前提
fact-verified: 原檔 Task 3.2 自寫「存活至：per-symbol 投影實作後改寫為支援分支（見 §N R-1）」 → 讀 `docs/SPLITUNIFY_SPEC.md` Task 3.2 末段（主委 2026-09-12）
fact-verified: `ICSplitAdapter._base_universe_hash` 對整框算一份 joint hash 並傳給 `split_per_symbol` → 讀 `momentum/Analysis/ic_split_adapter.py:189-199` 與 `momentum/Analysis/ic_filter_orchestrator.py:907`
fact-verified: 現行同源對證只比首尾兩列 → 讀 `momentum/Analysis/event_samples/split_projection.py:474-486`
fact-verified: `insufficient_events_in_test` 條件與迴圈變數無關、用整批 `n_test` → 讀 `momentum/Analysis/event_samples/split_projection.py:569`
fact-verified: 上游 consult 三家 18 條已收斂清債 → `bash scripts/debt_ledger.sh --has-open` rc=0（派工後預期值: rc=1——本輪 OPEN，非 2）
assumed: D-001 之觸及面四欄錨點皆逐字存在於原檔 ⇒ 否證觀測：必答 2 對讀時任一錨點在原檔找不到逐字相同的 heading。／我跑了：**用 grep 取出 heading 清單後逐一貼上，未逐字 diff**
assumed: 指紋 payload 定義足以兩端重算一致 ⇒ 否證觀測：必答 4 指出任一未定義處（NaT／重複 row_pos／空 plan）。／我跑了：**沒跑**（尚未實作，無法實跑）

## ⚠️ 前置
禁改碼；只讀；收尾清 /tmp workdir（保留 `claude-501`）。
