# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-04 | **Branch**: **main** | **狀態**: 🟢 **GOVFLOW epic B0–B4 五批全數完工並進版控**

## GOVFLOW（派工控制流四缺陷 A-1..A-4）— 完工

| 批 | 內容 | commit | 測試 |
|---|---|---|---|
| B0 | manifest 生成器 | `0d0f3a0` | 617 |
| B1 | A-1 heading 誤報 ＋ 四步程序 ＋ `T1-I1` | `d36d76b` | 642 |
| B2 | A-2 `result_state` 三值 ＋ emit 順序 ＋ P16 v3.0（R 重開） | `c0a7004` | 655 |
| B3 | A-3 角色檢查前移 ＋ `scripts/_role_gate.sh` | `2696e77` | 675 |
| B4 | A-4 claim checker 委員逐字豁免（Task 4.1＋4.2） | **`6a06f0c`** | **701** |

**B4 走了 6 輪**（實作→NO-GO 7 條→修補一→複核→修補二→複核→收窄→複核）。
輪 6 由**主委自實作**（使用者核准；斷路器超額後選最省輪次），codex＋composer 仍為非實作者。
最終雙家族皆 **GO**（`CODEX-R16-P3-00` sentinel／`COMPOSER-R16-P3-01` minor 已修）。
**實測回歸**：85 份真實收斂檔（排除 `probe-b4-*`）違規 **26→16 條、18→12 檔**。

## 🔴 具名接受的殘留（**是未完成，勿當已解**）

- **A-4 全域未解**：主委摘要／群集段無 backing 的 claim 仍不能 commit ⇒ **12 檔仍有違規**。
  兩家判「屬 Task 4.2 契約正確執行」；缺口＝主委摘要段需 backing 或更窄豁免，**另案**。
- **12 個非 M code mutation 未逐一執行**（`T4-U1/N1/N2/C1/U2/N3/N4/N5/B1/B2/N6/B3`）。
- TODO §0 數字對照表**本 epic 內漂了四次**（四格曾錯三格）⇒ `票 B-17` 未做前還會再漂。

## 🔴 使用者定死（最高優先）

1. **不能 100% 擋下 → 解決 95%，出問題再記錄**；**擋意外，不在「阻擋蓄意」上撞牆**
2. **寫出來的工具就是要有強制使用的機制——不准靠紀律和記憶**
3. **狀態回報**：寫【進行中】必須 (a) 同回覆有工具呼叫 或 (b) 附背景任務 ID；否則寫【停住】
   （機械強制：`scripts/status_marker_check.sh`）
4. 🔴 **問題 A 目標函數（逐字）**：「如何修改程序或流程，可以**最無痛且有效率且最低成本地
   修改 SPEC 或相關文檔**，然後繼續執行延伸或修改的任務。」「最少輪次」指**整條流程長期**
5. **檢查放在產出端**；**治理投資看所有 epic 完成後的合計貢獻**，不以單輪 findings 數評斷

## 下一步（依序）

1. **【使用者約定】討論「如何同時錯誤更少且每輪更便宜」**——本 epic 是最好的材料：
   6 輪裡 2 輪源於「上一輪沒驗到的東西」，非需求變更
2. backlog `handoffs/20260801-GOV-AMEND-BACKLOG.md`（**唯一票登記處**，`B-1`～`B-28`）
   第 0 層：`票 B-27` 文件分類 → 7 張無號票編號 → v2.0 講法統一
   白話版＝`handoffs/20260804-BACKLOG-白話總覽.md`（52 項 checklist，✅8／🔨1／🗑5／空38）
3. 凍結程序 v2.0 階段 1 工具實作（`docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md`，
   sha256 `176c58e0…`，戳記 `handoffs/reconcile/20260803-frozen-proc-v2-text/synth.md` rc=0）；
   硬前置＝`GOV-DOCS-STAMP-PROVENANCE`
4. 其他：D-002 送戳記／`Task 3.2`→B5→P1-6 結案

## 📌 開工前必做

1. 稽核本檔／ROADMAP vs repo 實況　2. `bash scripts/agent_preflight.sh`
3. 派工一律 `committee_run.sh`；收集用 `reconcile_build.sh`
4. **`git push` 會跑整套 governance（約 180s）→ 一律丟背景**
5. 不要對 `docs/*.D-NNN.md` 跑 `reconcile_stamps_check.sh`（必 rc=1，＝T6）
6. **禁用專案外絕對路徑**（觸發 600 秒 A 類卡頓）
7. **brief 內假設標籤不得用 `X-N` 形態**（`E-1` 會撞 `completeness_check` ID 誤報）
8. **`handoffs/*` 被 `.git/info/exclude` 排除**——須 `git add -f` 才進版控

## ⚠️ 本 session 新增的坑

- **`core.hooksPath = scripts/git_hooks`**——查 `.git/hooks/` 會誤判「hook 沒裝」（主委犯過，
  並據此對使用者說了錯話；正解＝用有效探針實測 rc，且探針須先確認會被擋）
- `gate_check.sh` 看到指令含**委員家族名**就當派工，擋掉唯讀清帳（`票 B-15`，本 session 6 次）
- 委員探針會在 `handoffs/reconcile/` 留 `probe-*` 目錄，**污染統計基準**（89 vs 85）
- 委員家族偶發 `RetriableError: [resource_exhausted]`（連線中斷非配額），**重派即可**，勿逕自歸因額度
