# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-03 | **Branch**: **main**（同步，`1787986`） | **狀態**: **問題 B 已收斂；問題 A 方向已定案（三家一致）；下一步＝起草修訂版設計稿**

## 🔴 使用者定死（最高優先）

1. **不能 100% 擋下 → 解決 95%，出問題再記錄**
2. **擋意外，不要在「阻擋蓄意」上撞牆**
3. **寫出來的工具就是要有強制使用的機制——不准靠紀律和記憶**
4. **狀態回報**：寫【進行中】必須同時滿足其一——(a) 同一則回覆有實際工具呼叫；(b) 附可查的背景任務 ID。
   兩者皆無 → 寫【停住】。**已做成機械強制**：`scripts/status_marker_check.sh` 掛 Stop hook。
5. 🔴 **問題 A 的目標函數（2026-08-03 逐字）**：
   > 「如何修改程序或流程，可以**最無痛且有效率且最低成本地修改 SPEC 或相關文檔**，然後繼續執行延伸或修改的任務。」
   「最少輪次」指**整條流程長期**，**不是**單一任務內；以「本輪要多跑幾輪」否決長期解**不符**目標。
6. **檢查放在產出端**：「不要有派工發現格式有問題、退回去重跑一輪的情況——**這就是檢驗審查放在錯誤的地方**。」

## 🔴 兩個問題必須分開（使用者 2026-08-03 糾正主委的混淆）

| | 問題 A：改文件成本 | 問題 B：退回重跑 |
|---|---|---|
| 觸發 | ①分類爭議 ②兩份 D 觸及面重疊 ③設計被證偽 | 格式錯到消費端才發現 → 整輪 abandon |
| 對策 | 凍結程序修訂（D/C；A/B 不做） | 檢查移到產出端 |
| 狀態 | **方向定案，未實作** | ✅ **已收斂** |

**主委曾把兩者混為一談**（宣稱「A/B/C/D 沒處理退回來源」）——**錯**：R 的觸發條件無一是格式寫錯。

## ✅ 問題 B：已收斂（四節點全在產出端）

| 產物 | 檢查點 | commit |
|---|---|---|
| brief | 派工時 ＋ **寫檔時** | `901a8d9`（T1） |
| SPEC／TODO | freeze 時 ＋ **寫檔時** | `901a8d9`（T1） |
| 委員產出 | **交件時**（`completeness_check --single`） | `8193582`（T5 第一段） |
| 收斂檔 `synth.md` Verdict | **寫檔時**（`verdict_filled_check.sh` 唯一實作） | `1787986` |

⚠️ **殘留（窄）**：`RECONCILE-STAMP` 的**真戳記缺陷**（hash 錯／缺家族／provenance 斷）仍只在 gate 消費端發現。
`cx_run.sh:374` **不是 fail-closed**（`GROK-R2-P0-02`）；malformed stamp row 是 no-op、`stamp-target` 只驗路徑、
外部/人工 append 不進產出端 hook（`CODEX-R2-P1-04`）。**主委兩度誤判此項**（先憑印象列缺口、再憑不完整實測刪除）。

## ▶ 問題 A：方向定案（`handoffs/reconcile/20260803-proba-direction/synth.md`）

| 項 | 裁定 |
|---|---|
| **D 分節簽名** | 修改後採用，**分階段** |
| **C 窄版**（觸及面機檢） | 同期採用；**須同輪改 §6「本程序不新增任何檢查器」** |
| **A**（R 範圍收窄） | **不做**；grandfather 期靠 C 擋誤觸發 |
| **B**（爭議預設） | **原案不做，維持現行 §1 default-R**（＝不改安全閥，非刪除） |

🔴 **主委核心推論已被三家打穿、作廢**：「分節後 R 變便宜 ⇒ A/B 可省」**不成立**——
分節只讓**重簽的機械成本**變小，**對抗審勞動／分類爭議／跨節依賴／provenance 不會自動變成單節成本**。
除非 **R 的定義同步改成「節級重審＋依賴閉包」且 brief／gate 機械綁定 scope**，否則審查仍逼近全檔。
⇒ **簽名的粒度 ≠ 審查的粒度**。

### 下一步（**只起草設計稿，不進工具實作**——三家一致）

設計稿須先鎖定：D schema／mode／legacy registry／section inventory／C 誠實邊界／pilot gate。

- **工具清單**（比主委設想長）：`reconcile_body_hash.sh`／`reconcile_stamps_check.sh`／`verify_task_provenance.py`／
  `cx_run.sh`／`completeness_check.sh`／`reconcile_build.sh`／`reconcile_add_stamp_section.sh`／`reconcile_clear_stamps.sh`；
  `verify_spec_stamp_delta.sh` 須明定 **legacy-only 或退場**
- **輪次**：codex＝1A 程序 R 審＋戳記／1B 工具實作＋獨立驗證／1C pilot；grok＝**3–5 操作輪**
- **pilot**：codex 建議 `DECOUPLE_SCAN2_SPEC.md` ＋ paired TODO
- **紅線**：檔級 mode 標誌 ＋ **dual-read fail-closed**（legacy whole-body **XOR** section-map）；
  **禁止「算得出任一 hash 就算過」**；缺節／重排／heading 改名／map 不一致／schema fallback **一律 FAIL**
- **C 誠實邊界**：硬 gate 只涵蓋 anchor 存在/重複、`PREDECESSOR`/`BASE` 鏈、生效 D 宣告覆寫相交、index binding；
  「正文引用 ⊃ 宣告」**只能 advisory**，**不得宣稱能抓 D-002 型宣告不實**

## ▶ 其他待辦

| # | 任務 | 狀態 |
|---|---|---|
| **T3** | 線 C ＝ **D-002 已修完六項 P1 ＋ 補上申報不實的 `§P` 觸及面**，過 `dext` rc=0，`handoffs/20260802-D002-DRAFT.md`（218 行） | **待送三家戳記** |
| **T4** | `Task 3.2` → B5 完工 → P1-6 epic 結案 | 未動 |
| **T6** | `GOV-DOCS-STAMP-PROVENANCE` | 未動 |
| **T7** | 清尾小票 | 未動 |

**D-003（`result_state` 收窄）已停止推進**：與 D-002 觸及面重疊（同覆寫 `## §P`），依 §3.3 不得平行生效。
草案留 `handoffs/20260802-D003-DRAFT.md`，待 D 分節簽名落地後成本結構會改變，屆時重估。

## T7 清單

- `GOV-FAILCLOSED-DEP-GUARD`：主委原案（靜態探針硬 gate + `OPTIONAL-DEP` 註記）**經 codex 實跑否決**
  （60 支 shell／命中 5／**真陽性 0**／漏抓 `gate_check.sh:66`）。採委員版：tripwire 警告 ＋ 隔離 runtime mutation 硬 gate ＋ 可過期豁免 registry ＋ `require` helper
- `GOV-TESTHARNESS-SCRIPTLIST-SSOT`：隔離 repo 腳本清單散在 **4 份 fixture**，本 session 因此紅了 **6 次**。
  ⚠️ 最新一次失效形態值得記：**拒發案例「紅對了但原因是錯的」**（缺檢查器→非零→判成未填），靠放行案例才抓出
- `docs/` 既有 **24 檔**格式 backlog（多為 `Archived/*` 與 `*_SPEC_PLAIN*` 誤報）
- `P16-SPEC-STAMP-DELTA-STALE`／`GOV-XREF-SYNC`／B-6／B-8／`GOV-VERIFY-RECEIPT-RUNNER`／`P16-DEBT-ROSTER-BINDING`

## 委員品質觀察（T5 動機證據）

composer 本 session 三次同型缺陷（格式／嚴格度寬鬆）。
**T5 上線後已連續 4 輪正常銷帳、零 abandon**（此前最近 4 輪有 3 輪只能 abandon）。

## 📌 開工前必做

1. 稽核本檔／ROADMAP vs repo 實況
2. `bash scripts/agent_preflight.sh`
3. 派工一律 `committee_run.sh`；收集節點用 `reconcile_build.sh`
4. **`git push` 會跑整套 governance（約 180s）→ 一律丟背景**，否則被 2 分鐘 timeout 砍
5. **不要對 `docs/*.D-NNN.md` 跑 `reconcile_stamps_check.sh`**（必 rc=1，＝T6）
6. **禁用專案外絕對路徑**（`/private/tmp/...`）——本 session 因此觸發 600 秒 A 類卡頓
