# HANDOFF — 當前任務狀態

**更新：2026-09-12｜現行票：`SPLITUNIFY 收尾`（大；RISK a,b,c）——用已結案之 `VERDICTGATE` 四閘全程跑，並記錄摩擦（使用者 2026-09-12：「把 SPLITUNIFY 後來發現要補上的都做完，順道檢驗新治理票在整個流程上實際運用的狀況和摩擦」）｜**偵察輪已收斂清債（round `5722105c`，18 條）**，下一步＝ b8 開工｜`VERDICTGATE`（B-62）已結案**
- **偵察收斂（三家 consult）**：18 條＝15 採納／1 部分採納／2 駁回。收斂檔 `handoffs/reconcile/20260911-splitunify-x-consult-r2/synth.md`（歸戶閘 18/18 過、清債 rc=0）。主委自產版 `handoffs/20260912-SPLITUNIFY-CLOSEOUT-RECON-claude.md`。
- 🔴 **主委初判被三家否證兩處**：①R-1 不是「唯一性未定義」——`ICSplitAdapter._base_universe_hash(frame,…)`（`ic_split_adapter.py:189-199`）對**整框**算一份 hash 並打進每個 symbol 的 plan（`ic_filter_orchestrator.py:907`），**跨 symbol 共用同一字面 hash 是合法且已發生**，不得寫成「必互異」之閘；②D1 改條件式**不能**走 D 延伸。
- 🔴 **D1 走 R 重開**（codex／grok 判 R；凍結程序明文「與原檔互斥者非 D、爭議一律預設 R」）。D1 裁定住在已三家戳記之共識檔 `handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`（rc=0、body `120b4d04…`）⇒ 改它＝改已戳記內容。**`docs/SPLITUNIFY_SPEC.md` 本身無 in-file 戳記、不在 `stampable_artifacts.txt`**。
- **批次序（採 codex 保守案）**：**b8＝R-1＋SU-RESID-3**（識別基礎）→ **b9＝SU-RESID-2＋下游單鍵**→ **D1 R 重開重戳** → **b10＝R-5**。R-5 不得與未完成之 D1 同批上線。
- **各條定案修法**：R-1＝投影收 `Mapping[symbol,(train,test)]`＋逐 symbol 同源對證，不變式改為「同 symbol 之 train/test hash 一致、跨 symbol 允許共用 joint hash、事件 symbol 必匹配 plan.symbol」；SU-RESID-3＝producer-attested **完整有序** `row_time_fingerprint`（固定排序／epoch-ms／含 symbol scope 與 provenance，接受 IC golden digest 位移）；SU-RESID-2＝**additive** 加 `timeframe` 欄、保留 `event_id` 身分、既有五組 golden 不重凍、另加多 TF 組；R-5＝per-symbol／per-TF **ref manifest**（path＋config_hash＋post-trim row-time digest），缺任一即 fail-closed，**禁 auto-discover**，且須補 `capability.split=ok` 分支與前端最小入口。
- 🔴 **b8 必修連動**（codex P1-07＋主委自查同題）：`split_projection.py:569` 之 `insufficient = [s for s in per_symbol_n if n_test < …]` 條件與迴圈變數無關、用**整批** `n_test` ⇒ 多標的下 per-symbol 門檻失效；須配「一標的低於門檻但總數高於門檻」負例。另 `test_splitunify_derive.py:537` 之「`single_symbol` 恆亮是預期的」在 R-1 後變假前提，解除條件須寫死「僅 `n_symbols > 1` 才解除」並配 mutation。
- 🔴 **SU-RESID-2 下游單鍵面**（codex P1-08，已抽驗屬實）：`feature_materialization.py:132/138`、`baseline.py`、`pattern_bridge.py`、`tables.py`、`ic_feed.py:109` 皆以 `event_id` 單鍵；未全面改前，多 TF 同批一律 fail-closed。另 `dedupe.py:124-127` 之 `cluster_first` 取每簇最早一列，同事件不同 TF 落同簇會被折疊。
- 🔴 **兩閘互斥（本輪摩擦，處置已定為慣例）**：委員交件格式錯（grok 用 `###` 而抽取器只認 `##`）⇒ 不改則 completeness 硬閘擋（掉項）、改了則 debt_clear「交件後不得改動」擋。**處置：`handoffs/` 原檔保持交件原狀供稽核，格式正規化只落在 `handoffs/reconcile/<session>/sources/` 複本**（lock 記錄複本 sha、completeness 驗複本、debt_clear 驗原檔）。修法方向已登記於白話摩擦記錄，本輪不做。
- 摩擦記錄：`白話說明/流程摩擦記錄.md`（2026-09-12 段，5 筆；含我自己兩次判讀錯誤）。舊骨架改名保留於 `handoffs/reconcile/zz-stale-consult-r2-skeleton/`（未刪，供稽核）。
- 殘留不動：`R-3`（UAT 最後，使用者裁定）、`R-4`（`extract_event_patterns` 無 production caller，屬 GAP-3）；`SU-RESID-1` 已由 VERDICTGATE Task 4.1 實作完成。
- 🔴 `FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` 檔頭仍寫「狀態：草案，尚未生效」，但其戳記檔 rc=0、三家 APPROVED、commit `d45f29be` 標題為「v2.0 定案生效」⇒ **檔頭為過期行**，下一張治理票處理。
- 開工前固定動作：`bash scripts/agent_preflight.sh`；b8 開工前 `bash scripts/gate.sh dispatch --impl-self --task-id 20260911-SPLITUNIFY-impl-b8-claude …` 自證；生產路徑 commit 必帶 `Ticket-Batch: 20260911-SPLITUNIFY/b8`。
- 🔴 task-id／session 之日期前綴屬 root：本票一律沿用 `20260911-SPLITUNIFY`（跨日不得改前綴，否則語料對不上、CLOSED 被拒）。
