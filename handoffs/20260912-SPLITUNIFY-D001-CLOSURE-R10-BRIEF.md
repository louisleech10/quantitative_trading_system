# SPLITUNIFY D-001 閉合確認 R10（重驗 R9 之兩條）

brief-kind: closure
task-id: 20260911-SPLITUNIFY-X-REVIEW-R10
findings-round: R10

🔴 **這是閉合確認（closure），不是實作、不是重新全審。禁改碼、禁動 tracked 檔；禁在本 repo commit／push；禁跑 `tests/governance` 全套。** 隔離實驗之指令列與暫存路徑**不得含任何委員家族名稱**（派工閘會誤判為派工）。

🔴 **交件格式（本票已五度因此回頭正規化，請逐字遵守）**：
- findings 一律 `## <FAMILY>-R10-P<0-3>-<NN>` **二級**標題
- 末段三行機械塊：`VERDICT: proceed|blocked`／`BLOCKED-BY:`／`CLOSED:`。**無內容就留空**，不得寫 `none`
- 完成訊號**逐字** `STATUS: DONE`
- 🔴 戳記若附，`sha256:` 必須是 `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` 之實際輸出，不得寫 `PLACEHOLDER`

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`；零新 findings 用 sentinel `## <FAMILY>-R10-P3-00`。

## R9 的裁決與本輪修法

R9 兩家裁決相反，且對**同一件事實**給出相反斷言。主委以實跑判定：

| 斷言 | 主委實跑結果 |
|---|---|
| 「`@dataclass(frozen=True)` ⇒ 欄位不能被就地改寫」 | **不成立**。整欄改綁被擋，但 `p.row_index[0] = 99` 成功、讀回 `[99 2]`、`flags.writeable` 為 `True` |
| 「建構時有保護」 | **不成立，且原報未提**：無 defensive copy，改動呼叫端持有之來源陣列後 plan 讀回 `[77 6]` |

落點（皆已入 D-001-C2 第 4 點與 Task 8.2）：

1. **`SplitPlan.__post_init__` 對 `row_index` 與 `row_index_local` 各自複製一份並 `setflags(write=False)`**；新增三條 ASSERT（原地寫入應丟例外、改來源陣列後 plan 不變、attest 前提）與變異 `M-SU-D1-13`／`14`／`15`。
2. **attest 之前提條件**：`momentum/core/contracts.py:562-568` 之「標的內時刻嚴格遞增」僅在 `purge_semantic == "rows"` 分支內；而 `momentum/Analysis/ic_filter_orchestrator.py:930` 之路徑以 `purge_semantic="timedelta"` 建 plan ⇒ 該形狀下 helper（frame 序）與 `train_local`（時間序）可分歧。處置：一律以寫入 `train_local` 為準；attest 遇 frame 序非時間序**不得靜默跳過**，須 fail-closed 並指名 `purge_semantic` 與該標的。
3. 順帶改寫 D-001 內殘留之「入口轉換」措辭（R8 起已改為 producer attest）。

## 🔴 必答

1. **`CODEX-R9-P1-01` 是否已閉合**？附重驗碼證（對讀修訂後之 D-001）。
2. **深層不可變性是否真的封住**：除了「原地寫入」與「來源陣列別名」兩條，是否還有其他路徑能在 attest 之後讓兩欄脫鉤（例如 `np.asarray` 對同型別輸入回傳同一物件、切片視圖、`copy`／`pickle`／`replace` 之往返、或消費端自行 `.copy()` 後改寫再寫回）？請具體指出或明說找不到。
3. **fail-closed 的新增面是否會打到現行綠徑**：第 2 點之處置會讓「frame 序非時間序」在 producer 端直接報錯。請實查 `ic_filter_orchestrator.py:930` 那條 `timedelta` 路徑之 frame 實際是否已按時間排序；若**已排序**則本處置不影響現行行為，若**未必排序**則指出會被新擋下的具體呼叫路徑。這是本輪最重要的一問——我可能為了修正確性而弄紅既有路徑。
4. **（給 R9 判 proceed 的那一家）** 你在 R9 必答三稱「凍結 ⇒ 欄位不能被就地改寫」，已被主委實跑推翻（見上表）。請確認是否接受，並說明你的 `proceed` 裁決在該事實更正後是否改變。
5. **可否進入實作**（`VERDICT: proceed`）？

## 停輪條件

①必答 1–5 皆有立場；②必答 1–4 逐條附碼證（必答 3 須實查該路徑之排序，不得只讀規格）；③**禁以「無 finding」當停輪**；④若仍 blocked，須說明「不改會在 b8 實作或收案時具體怎麼失敗」。

## 前提

fact-verified: R9 兩條皆採納並已落 D-001 → 讀 `handoffs/reconcile/20260911-splitunify-x-review-r9/synth.md` 群集表 W1／W2（主委 2026-09-12）
fact-verified: 凍結擋不住原地改寫、且無 defensive copy → 主委 `venv/bin/python` 實跑，輸出 `[99 2]`／`writeable=True`／`[77 6]`
fact-verified: 單調性保證只在 rows 分支 → `contracts.py:562-568`；生產有 timedelta 路徑 → `ic_filter_orchestrator.py:930`
fact-verified: 修訂後 D-001 之格式、範本、歸戶與交叉引用皆通過 → `doc_format_precheck.sh` rc=0、`template_check.sh dext` rc=0、`reconcile_cluster_attribution_check.sh` rc=0、`spec_xref_check.sh --synth` rc=0
assumed: defensive copy＋唯讀足以封住兩欄脫鉤 → 否證觀測：必答 2 指出第三條路徑／我跑了: 只跑了原地寫入與來源別名兩條，**未**窮舉視圖與序列化往返
assumed: 新增之 fail-closed 不影響現行綠徑 → 否證觀測：必答 3 指出會被擋下之呼叫路徑／我跑了: **沒跑**（未實查該路徑之排序）

## ⚠️ 前置

禁改碼；只讀；收尾清 /tmp workdir（保留 `claude-501`）。
