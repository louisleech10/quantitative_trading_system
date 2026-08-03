# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-03 | **Branch**: **main** | **狀態**: 🔴 **凍結程序 v2.0 條文已定案生效（三家戳記 rc=0）；階段 1 工具實作尚未開始**

## 🔴 現行有效程序＝`docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md`

| 項 | 值 |
|---|---|
| 條文 sha256 | `176c58e0c914153dce33f08710f3a08994b5ac98bf40b74745c9c511e4192a40`（**戳記綁定此值，改動即作廢**） |
| 戳記 | `handoffs/reconcile/20260803-frozen-proc-v2-text/synth.md`；`reconcile_stamps_check.sh` **rc=0** |
| v1.0 | `docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` **已標 SUPERSEDED**，檔頭附 v1.0→v2.0 節號對照表 |
| 下一步 | **階段 1 工具實作**；硬前置＝`GOV-DOCS-STAMP-PROVENANCE`（條文 §6.3 已裁決主案＋輔案） |

## 🔴 使用者定死（最高優先）

1. **不能 100% 擋下 → 解決 95%，出問題再記錄**
2. **擋意外，不要在「阻擋蓄意」上撞牆**
3. **寫出來的工具就是要有強制使用的機制——不准靠紀律和記憶**
4. **狀態回報**：寫【進行中】必須 (a) 同回覆有工具呼叫 或 (b) 附背景任務 ID；否則寫【停住】。
   已機械強制：`scripts/status_marker_check.sh`（Stop hook）
5. 🔴 **問題 A 的目標函數（逐字）**：
   > 「如何修改程序或流程，可以**最無痛且有效率且最低成本地修改 SPEC 或相關文檔**，然後繼續執行延伸或修改的任務。」
   「最少輪次」指**整條流程長期**，不是單一任務內。
6. **檢查放在產出端**——不得等派工才退回重跑
7. **治理投資看「所有 epic 完成後對整條流程的合計貢獻」，不以單一輪次的 findings 數評斷**（2026-08-03 使用者糾正主委的停損建議）

## ▶ 當前任務：凍結文件修訂程序 v2.0

**設計稿**：`handoffs/20260803-FROZEN-PROC-V2-DESIGN.md`（**rev6**）
**收斂**：`handoffs/reconcile/20260803-frozen-proc-v2-r{1,2,3,4,5}/synth.md`

| 輪 | findings | 關鍵結論 |
|---|---|---|
| R1 | 26 | 兩個 BLOCKING 打穿核心機制（baseline 無錨點、刪節不算改動） |
| R2 | 28 | 確診 rev2 是**加機制型**修訂，三個新元件全被打穿 |
| R3 | 25 | 三家一致「刪機制方向正確，剩餘是**規格文字非架構**」 |
| R4 | 16 | 兩家「差兩句話、95% 可收」；codex 被格式閘擋在 lock 外 |
| **R5** | **6** | **composer 判「可派工、可進條文」**；grok「不需再一輪架構 R」；**codex 專項確認 R4 手抄摘要忠實，lock 缺口關閉** |

**累計刪掉 5 個元件、新增 0 個**：baseline registry／`expires` 三段式／raw-byte escaping／`DEPENDS-ON`＋環檢／bounded inventory 承諾。

### 下一步：寫 v2.0 條文（階段 0 收尾）

**順序（三家交集，見設計稿 §D17.2）**：
① **§D5（T6）裁決**——`register-output` 白名單 ＋ synth authority 分工（三家一致列第一）
② §D0 目標＋四分解 inventory ＋ §D1 核心決策 → ③ §D2 schema／VALID 雙述詞／roster 時點
→ ④ §D3 mode／grandfather write-once → ⑤ §D4 resolve／closure 誠實邊界
→ ⑥ **§D6 C ＋ §D7 §6′ 同輪** → ⑦ §D8 → §D9 manifest → **§D10 oracle 全表收口**

**階段 0 程序檔自身維持 `whole-body`**（雞生蛋）；section-map schema 可放 v2.0 附錄節。
**條文合併進 `docs/` 前不得進階段 1 工具實作**（三家一致）。

## 🔴 本 epic 產生的新票

| 票 | 內容 |
|---|---|
| `GOV-COMPLETENESS-IDLIKE-FP` | `completeness_check` 把「首 token 形如 `XX-NN`」的 heading 誤判為畸形 finding ID（codex 因此整輪卡死）。判準應收窄為「含 `-R<digit>-` 節段或以已知家族名起始」。**須先盤攻擊面＋連動測試矩陣** |
| **重啟 `D-003`（`result_state` 收窄）** | 格式不合規但 `cli_rc=0`＋產出非空 ⇒ 記為 `success` ⇒ 守衛⑥拒絕重派 ⇒ **家族在該輪永久卡死**。已有具體事故（R4）。改法＝`success` 須加「產出端格式檢查通過」 |
| `GOV-ROLEGATE-PREDISPATCH` | `brief-kind` 與角色 SoT 的相容性只在 `cx_run` 派工當下才驗，此時債已開、其他家已跑完 ⇒ 半失敗輪。應前移到 `committee_run` **開債前**逐家驗 |

## ⚠️ 主委在本 epic 的錯誤（供稽核，設計稿 §D14 有完整版）

1. 「分節後 R 變便宜 ⇒ A/B 可省」——前輪三家打穿
2. rev2 用**加機制**補洞，三個新元件全被打穿
3. 手寫閉包「12 支／15 檔」，算術與定義皆錯
4. **戳記檔數錯三次**：報「2」→ 更正「31」→ **兩者都不是**；正解＝canonical in-file row **0** 份（因 T6 全外置）
5. rev5 改詞界**未同步同節舊定義**（`GROK-R5-P1-01`）——已改用 grep 機械掃描修正

## 📌 開工前必做

1. 稽核本檔／ROADMAP vs repo 實況
2. `bash scripts/agent_preflight.sh`
3. 派工一律 `committee_run.sh`；收集用 `reconcile_build.sh`
4. **`git push` 會跑整套 governance（約 180s）→ 一律丟背景**
5. **不要對 `docs/*.D-NNN.md` 跑 `reconcile_stamps_check.sh`**（必 rc=1，＝T6）
6. **禁用專案外絕對路徑**（觸發 600 秒 A 類卡頓）
7. 🔴 **brief 內的假設標籤不得命名為 `X-N` 形態**（`E-1` 等會撞 `completeness_check` 的 ID 誤報，見上票）
8. 🔴 **`handoffs/*` 被 `.git/info/exclude` 排除**——本 epic 產物須 `git add -f` 才進版控

## ▶ 其他待辦

| # | 任務 |
|---|---|
| T3 | D-002 送三家戳記（`handoffs/20260802-D002-DRAFT.md`，218 行，過 dext rc=0） |
| T4 | `Task 3.2` → B5 完工 → P1-6 epic 結案 |
| T6 | `GOV-DOCS-STAMP-PROVENANCE`——**已升為 v2.0 階段 1 硬前置**（設計稿 §D5） |
| T7 | `GOV-FAILCLOSED-DEP-GUARD`／`GOV-TESTHARNESS-SCRIPTLIST-SSOT`／docs 24 檔 backlog／`P16-SPEC-STAMP-DELTA-STALE`／`GOV-XREF-SYNC`／B-6／B-8／`GOV-VERIFY-RECEIPT-RUNNER`／`P16-DEBT-ROSTER-BINDING` |
