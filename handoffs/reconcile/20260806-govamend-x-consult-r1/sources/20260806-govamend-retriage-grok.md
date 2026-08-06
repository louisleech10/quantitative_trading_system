# GOVAMEND 全票重新裁決 — grok R21

family: grok | task-id: 20260806-GOVAMEND-X-CONSULT-R1 | round: R21
受審：`handoffs/20260801-GOV-AMEND-BACKLOG.md` 票 B-1～B-38 ＋ 第 0 批 B0–B7＋B3R
判準：價值 = (擋掉的 agent 失誤類別 × repo 內實證次數) ÷ 新增摩擦；可讀性非驗收；溯及既往預設關閉

## Verdict

**需修補後派工（backlog 執行順序）／本諮詢輪可收斂**

- 38 張皆有裁定；多張應**關閉**或**降級**（見下表「裁定」欄與 Q1）。
- 第 0 批 **B3R 仍成立且應優先收斂**；B4 必須等 B3R；B5 是 B-29 手動版可保留；B6/B7 對 B-14/B-30 仍有價值。
- **無票但高頻**：`###`/id-like heading 誤殺 與 **群集 ID 未登記** 應立刻掛票或併入既有票（見 findings 與 Q3–Q5）。
- 主委 §0 假設「38 張全部有真實 agent 失誤」**不成立**——至少 B-1/B-2/B-3/B-7/B-8/B-10/B-12/B-18/B-23/B-32/B-35 在新判準下應關閉、維持 DONE、或降級。

FINDINGS_COUNT: 6

## §0 前提宣告

- fact-verified: `scripts/completeness_check.sh:60` `HEADING_LINE_RE='^[[:space:]]*#{2,6}…'`；同檔 body-hash `H2_LINE_RE`（約 :921）僅 `##(?!#)`。VERIFY: `grep -n 'HEADING_LINE_RE\|H2_LINE_RE' scripts/completeness_check.sh`
- fact-verified: id 抽取**不是**「凡 `###` 必 fail」。四步程序（:141 區）：canonical → allowlist → **id-like 畸形 fail** → 其餘放行。VERIFY 探針：
  - `### G-1 extra` → `COMPLETENESS FAIL: invalid finding ID`（rc=1）
  - `### 另外要回答的` → PASS(single)（rc=0）
  - `## Verdict` ＋ 一條 canonical finding → PASS(single)（rc=0）
  - 工作目錄：`/tmp/govamend-retriage-grok-probe/`
- fact-verified: 主委宣稱「裸 `B<數字>` 10,557 處／1,414 檔」——本輪未重跑全庫（成本高、且全庫 lint 已依新判準砍掉）；**採納 brief 數字為 assumed-from-chair，不另建溯及 lint**。
- fact-verified: `docs/GOVERNANCE_ID_NAMESPACES.md` §1 列 12 空間；`grep -c 群集 docs/GOVERNANCE_ID_NAMESPACES.md` → **0**。來源摘要：`docs/GOVERNANCE_ID_NAMESPACES.md#00b06b45dabc`
- fact-verified: `C`/`D`/`E`/`F` 群集式編號會撞已登記或明文禁配空間（該檔 `E-<n>`「不得當作 ID 空間配置」；`F<n>` 另有未登記流通）。
- fact-verified: `gate_deny` 現有 reason 機器值主為 `token_expired`／`open_debt`（本輪：`grep -ao '"reason":…' .claude/gate/audit.log | sort | uniq -c` → token_expired **586**、open_debt **177**）；Phase0 後部分列已有 `match_rule`/`cmd_head`（`grep -c match_rule` → **97**）。
- fact-verified: `scripts/cx_run.sh:517-521` 已對 `stamp|closure` 才注入 RECONCILE-STAMP；`tests/governance/test_cxrun_stamp_prompt.py` 存在 ⇒ **B-32 harness 面已落地（B2）**。
- fact-verified: `grep -c dext scripts/template_check.sh` → **13**；`register-output` 仍只收 `handoffs/`（`gate.sh:167-168`）。
- fact-verified: `gate.sh:528`／`:555` 仍有 `""|waived:*|stamped-waived:*)` 直接跳過。
- fact-verified: audit 內明確寫「票 B-38」之 abandon **≥9** 筆（`grep -c 'B-38' .claude/gate/audit.log` → **9**）。
- assumed（挑戰見 findings）：「38 張全部對應真實 agent 失誤」——**不成立**（見逐項表中實證 0 或已 DONE/OBSOLETE）。
- assumed：第 0 批 B0–B7＋B3R 仍全數高價值——**部分成立**（B3R/B4 高；B5 過渡；B0 已交付）。

## 逐項核對表

> 查法欄可重跑。實證次數 = repo 內可定位之事故／audit／票面自述；**0** 表示本輪查不到可重跑實例（票面宣稱不計）。
> 不受理（不開 `##`）：不改票號；不評 B3R 技術設計；不碰 latency；不評命名美觀。

| 票 | 擋哪類 agent 失誤 | 實證次數 | 查法（可重跑） | 新增摩擦 | 溯及既往 | 裁定 |
|---|---|---|---|---|---|---|
| B-1 | （無——v0.5 缺腳本；v2.0 已取代路徑） | 0 現行 agent 路徑 | `test -e scripts/spec_binding_check.sh`→MISSING；backlog 三家 OBSOLETE | 建全套 A0–A11 檢查器＋遷移 | 是（舊程序） | **關閉**（維持 OBSOLETE） |
| B-2 | （無——同上） | 0 | `test -e scripts/manifest_parse.py`→MISSING；OBSOLETE | 新建 yaml 解析 SSOT | 是 | **關閉**（OBSOLETE） |
| B-3 | （無——同上） | 0 | backlog 表列 OBSOLETE；無 rejections validator 現用事故 | 獨立 validator | 是 | **關閉**（OBSOLETE） |
| B-4 | 戳記區塞非白名單內容仍過機檢／程序與碼不一致 | 1（CODEX-R5 級程序落差；本輪未另重現） | 讀程序 §4.4 vs `reconcile_stamps_check.sh`；ticket KEEP 裁決 | 實作白名單＋遷移 | 部分（舊戳記） | **降級**（forward-only；排 fail-open 批末） |
| B-5 | waive／空戳記**靜默跳過**（fail-open） | ≥2 碼位仍在 | `grep -n 'waived:\*|stamped-waived' scripts/gate.sh` → :528 :555 | 改 gate 分支＋回歸 | 否（改判定） | **做**（排序中後；附 B-29 差集） |
| B-6 | token 跨 session／未綁 worktree → 誤授權派工 | 文件化 fail-open（Claude.md GATE-TOKEN-BINDING）；本輪未計次 | 讀 `gate_check` mtime-only；CLAUDE.md Gotchas | token 綁 worktree／內容 | 否 | **做**（中；意外失效） |
| B-7 | 委員手抄 task-id 抄錯 | 歷史 2 家 R4；**已修** | `grep -n task_id scripts/cx_run.sh` 有注入；backlog ✅ | 0（已落地） | 否 | **關閉**（DONE） |
| B-8 | 主委單方 append 拒絕清單無人 ACK | **0** agent 交件事故 | `ls handoffs/gov_rejected_mechanisms.tsv`；無 audit 衝突實例 | 每次 append 多一輪 ACK | 否 | **關閉**（摩擦＞實證） |
| B-9 | `docs/` D 延伸無法 register-output／STAMP-BLOCKED 空轉一輪 | 1（2026-08-02 codex） | `gate.sh:167-168` 只收 handoffs/；票面事故 | R 修法＋provenance 路徑 | 否 | **做**（硬前置鏈；延後但保留） |
| B-10 | D 延伸當 SPEC 派工永遠 TEMPLATE FAIL | 1 歷史；**已修** | `grep -c dext scripts/template_check.sh`→13 | 0 | 否 | **關閉**（DONE） |
| B-11 | 依賴缺席當「不適用」→ 檢查假綠 | 三家裁定病根；本輪未重跑 runtime mutation | ROADMAP／backlog 原案否決紀錄 | tripwire＋runtime mutation | 否 | **做**（中；吸收 FAILOPEN-GUARD） |
| B-12 | harness 腳本清單漂 → 測試假覆蓋 | **0** 具名 agent 派工事故 | 票面「無 SSOT」；非派工熱路徑 | 建 SSOT＋全 harness 改接 | 可能 | **關閉**（非 agent 熱路徑） |
| B-13 | 文件搬遷／收斂漏節仍宣稱完整 | ≥2 大輪（R8 28f／R9 17f）＋漏搬模式 | backlog B-13 事故段；`grep -c '漏 §D' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 檢查器＋落點表 | 否 | **做**（高；吸收 B-18/B-36） |
| B-14 | 委員寫完不退出 → 整輪空等 | 1（2h20m，fd3 阻塞） | backlog B-14；GOVB0 Phase3 | timeout＋atomic publish | 否 | **做**（第 0 批 B6/B7；timeout 仍 PROVISIONAL） |
| B-15 | 唯讀／引號內／路徑名誤擋為派工 | 票面 7–13 次；audit 無票號欄故**不可從 audit 導出準確次數** | backlog 洞 A/B 實測表；`白話說明/流程摩擦記錄.md`；Phase0 後 `match_rule` 可補 | lexer 重寫（B3R） | 否 | **做**（第 0 批最高優先之一＝B3R） |
| B-16 | 機器契約在散文 → agent grep 漏列／搬錯 | ≥1 主事件（V 表 12 vs 15）＋擴充 A/B 票面 9 次寫檔謊言 | backlog B-16 事故＋擴充表 | precheck 擴充（中） | 否（只擋新散文契約） | **做**（高；擴充 A/B 可先於散文偵測本體） |
| B-17 | 手寫契約表漂／撞號／漏搬 | 同日多起（粗體漏列、M 撞號） | backlog 結構化後對照表；audit_events 先例 | 表→資料檔遷移 | **是若改舊表**→必須 forward／生成視圖 | **做**（高；縮小 B-13 scope） |
| B-18 | 收斂自由書寫漏處置 | 併 B-13 同 session 多起 | backlog MERGE→B-13 | 0 若併實作 | 否 | **關閉獨立票**（MERGE→B-13） |
| B-19 | brief 錯 kind／錯 ID 樣板／缺授權 → 整輪作廢 | 3（B0R／授權／review 誤標） | backlog B-19 事故表 | brief precheck 三項 | 否 | **做**（高；B-29 掛點） |
| B-20 | 結案無閘仍標 DONE | 使用者論證；遞迴漏層 | 票面；難計次 | 結案二擇一機檢 | 是若掃舊票 | **做**（forward-only 結案閘；批後） |
| B-21 | artifact 無對應檢查器 | 間接（多票無閘） | 票面 | 註冊表＋fail-closed | 是若全量 | **降級**（forward 新 artifact；批後） |
| B-22 | 派工無監看放大 B-14 | 與 B-14 同 1 次 | backlog；與 UNTRACKED② 重疊 | **新常駐元件**（高摩擦） | 否 | **降級**（先交付 B-14/B-30；觀察是否仍需 watcher） |
| B-23 | 標記逃脫打地鼠 | P16 列 20 變體（形式空間） | P16 §A #12 自陳無界 | 全量白名單＋誤擋率（**極高摩擦**） | 是若掃舊文 | **關閉**（違反低摩擦；與「不在散文形式撞牆」衝突） |
| B-24 | 驗收看 rc 不看狀態 → 假完成 | ≥3 同型（開票／併回／golden） | backlog 三次表；PARTIAL 已標 | 紀律面≈0；機械面大 | 機械面易溯及 | **做**紀律面（已在第 0 批）；**機械面獨立降級** |
| B-25 | 多副本事實改一漏多 | 票面 5 次同日 | backlog；MERGE→GOV-XREF-SYNC | xref 機檢 | 否（新寫） | **做**（作 XREF 子項；不雙開） |
| B-26 | 新 ID 未盤點既有空間→撞號 | **8–9**（backlog 事故清單＋HANDOFF ID 錯位 9） | backlog §5 表；`grep -c 撞號 handoffs/20260801-GOV-AMEND-BACKLOG.md`→12；HANDOFF「ID 錯位 9」 | 配置前閘（小） | **否——只約束新建** | **做**（高；forward-only；含群集空間登記） |
| B-27 | 票／檔亂放→重複開票／找不到 SoT | 根因級（B-11/12 跨檔、XREF 重發明、69 收斂 0 進版控） | backlog 七組語意詞 0 命中；票面 | 規則便宜；機械中 | 否（新規則） | **做**規則本體（中先）；機械強制**降級** |
| B-28 | v2.0 白名單元件不存在→程序空轉 | 3 檔 MISSING | `test -e` section_sig／dext_touchset／stamp_legacy_registry → 全 MISSING | 大任務＋B-9 前置 | 否 | **降級**（等 B-9；非每日 agent 熱路徑） |
| B-29 | 改判定只驗瞄準效果、不驗附帶放行 | GOVFLOW 批次 B4：**3／8 輪** | backlog 輪 6–8 表；60→27 放行對照 | EXPECTED-DELTA 強制（中，但省後續輪） | 否 | **做**（高；接在 B-19 後） |
| B-30 | 委員覆蓋自產出路徑、主委只見「很久」 | 1（codex 43m 中 ~28m 重工） | backlog 自述；GOVB0 Phase3 與 B-14 同機制 | atomic publish（與 B-14 共用） | 否 | **做**（第 0 批 B6） |
| B-31 | format-failed 只能整輪重跑＋擋後續派工 | ≥2 輪 RECON＋R5 同型；prompt 警告無效 | backlog 三牆表＋R5 二次事故 | fixup kind 或近似 ID 規則（中） | 否 | **做**（高；與 heading 規則同批） |
| B-32 | harness 無條件注入 STAMP→誘導 `## RECONCILE-STAMP` | 歷史 composer 2×format-failed；**B2 已修產生器** | `scripts/cx_run.sh:517-521` stamp\|closure 分支；test 檔存在 | 0 | 否 | **關閉**（DONE）。殘餘「主委手寫 brief 誘導」→歸 **B-19**，不重開 B-32 |
| B-33 | locale 非 UTF-8 → 守衛 fail-open | 1 session（LC_ALL=C 三案例） | backlog 三案例表；兩家 R1 裁定開票 | 腳本內鎖 locale（**小**） | 否 | **做**（低成本高不對稱；第 1 批後可插） |
| B-34 | stamp roster=全 review_families 但角色閘排除 implementer → 結構性缺章 | 每 review 輪結構必現（R1 現場） | `governance_families.json` vs `governance_roles.json`；票面 | roster 改實際 participants（小） | 否 | **做**（高；每輪摩擦） |
| B-35 | 截斷但末條完整 → 全綠 | **0 致害**（票面自承未曾實際致害） | codex 截 6 行仍 PASS 探針（存在於票面）；無 production 事故 | expected manifest（跨元件） | 否 | **關閉**（0 致害×高成本；殘留記 B-14） |
| B-36 | 群集漏引／錯位 completeness 無感 | ≥4 同型（R2 漏、R3 錯 3 ID、錯位、session 9 次歸錯群） | backlog B-36；HANDOFF「ID 錯位 9」；`--lock` 只驗附錄存在 | 產出端預列 ID（中，併 B-13） | 否 | **關閉獨立票**（MERGE→B-13；錯位為具名殘留） |
| B-37 | 優先序靠人工數次、不可稽核 | 1 方法論事故（「B-15 咬 N 次」audit 導不出） | audit reason 僅 token_expired/open_debt；票面 | tally 腳本（中；前置 Phase0） | 否 | **做**（Phase0 後；次數≠唯一排序） |
| B-38 | 合法 0 findings → completeness vacuous FAIL → 不能正規銷帳 | **≥9** audit 具名 B-38；流程摩擦「今天 7」；HANDOFF 升級 | `grep -c 'B-38' .claude/gate/audit.log`→9；`白話說明/流程摩擦記錄.md` | `FINDINGS_COUNT: 0` 欄（**小**） | 否 | **做**（**立即**；擋斷路器／派工） |

**不受理範圍標註（表內）**：不重寫 B-nn 票號；B3R 詞法設計另輪；latency 維持現狀；命名美觀不計分。

## 出場判準核算

| 條件 | 狀態 |
|---|---|
| 38 張全部有裁定 | 是（上表） |
| 每張實證附可重跑查法 | 是（上表「查法」） |
| 五問已答 | 見下方條列（仍在本節，無子標題） |
| 建議執行順序 | 見下方 |

**Q1 — 幾張應關閉？具名**

建議**關閉**（含維持 DONE/OBSOLETE／獨立票關閉）：

1. B-1、B-2、B-3（OBSOLETE，無現行 agent 價值）
2. B-7、B-10、B-32（DONE）
3. B-8（0 實證 agent 事故，ACK 儀式摩擦）
4. B-12（非 agent 熱路徑）
5. B-18、B-36（MERGE→B-13，關獨立票）
6. B-23（高摩擦、散文形式空間、違低摩擦判準）
7. B-35（0 致害）

共 **13** 張關閉（若 B-18/B-36 算「關獨立、內容併入」仍計關閉獨立追蹤）。

建議**降級**（不做或大延後）：B-4、B-21、B-22、B-24 機械面、B-27 機械面、B-28。

**Q2 — 第 0 批 B0–B7＋B3R 是否仍成立？**

| 批次 | 新判準 | 說明 |
|---|---|---|
| B0 | 保留（已完成） | 差集 oracle 前置；已交付 |
| B1 | 保留（已完成） | 可觀測性；B-15/B-37 硬前置；audit 已見 match_rule/cmd_head |
| B2 | 保留（已完成） | B-32 關閉依據 |
| B3 | 停手正確 | 連續修補引入新洞→斷路器 |
| **B3R** | **必須做、優先** | 直接擋 B-15 類誤擋；無它則每輪 agent 繼續改寫指令 |
| B4 | 保留但 **硬等 B3R** | fail-open 三洞；三家禁 B3 內再補刀 |
| B5 | **保留但定位為過渡** | 即 B-29 手動版；B-29 落地後應刪除並存 |
| B6 | 保留 | B-14/B-30 atomic publish |
| B7 | 保留 | timeout；PROVISIONAL 誠實邊界維持 |

應**砍／延**的不是 B3R，而是：把 **B-23／B-35／B-8／B-12** 類塞進後續批的衝動；以及在 B3R 未過前開 B4。

**Q3 — `###` 誤判優先序**

- 公式：整輪作廢類 ×（本 epic 已連續作廢 **≥2 輪** 三家，brief 自述）÷ 修摩擦（改 completeness 步驟 3 近似比對 **或** brief 白名單＋產出端，**小**）。
- **優先序 = 與 B-38 並列 P0 熱修**（同屬「合法報告無法交件／整輪作廢」）。
- 精準化（本輪探針）：**不是所有 `###` 都 fail**，而是 **id-like 非 canonical heading**（`G-1`、`RECONCILE-STAMP`、`FOO-BAR`）fail；中文小節 `###` 目前 PASS。主委 brief 全面禁 `###` 是**有效工作區繞法**，但根因應修步驟 3／allowlist，而非永久禁 markdown 結構。
- 建議：開 **`票 B-39`（或併 B-31④）**——「heading 僅 canonical／DEGRADE／allowlist 結構標題才進入 finding 通道；近似畸形 hard-fail；其餘 h2–h6 忽略」。Forward-only。

**Q4 — 群集 ID 未登記怎麼處置**

- 空間高頻：每輪收斂都要配號。
- **處置（forward-only，符合「舊釘死」）**：
  1. 在 `docs/GOVERNANCE_ID_NAMESPACES.md` §1 **新增一列**（建議樣式 `CLUST-<EPIC>-<n>` 或 `K-<EPIC>-<n>`，**禁止**再用裸 `C/D/E/F` 當群集——撞 `E-<n>` 禁配與 `F` 未登記流通）。
  2. 掛 **B-26** 配置閘：新建群集 ID 必須落在已登記樣式。
  3. 與 **B-13/B-36**：骨架預列 finding ID；群集列須附**斷言摘句**機械比對（擋歸錯群；HANDOFF 已列待開，建議併 B-13 範圍而非只靠紀律）。
  4. 既有收斂檔 `C1–C6` 等 **不改名**。

**Q5 — 該開而未開？**

| 缺口 | 實證 | 建議 |
|---|---|---|
| id-like／結構 heading 與 finding 通道耦合（含 brief 禁 `###` 工作區） | 本輪探針＋連續作廢輪 | **新票或 B-31④ 升格**（上 Q3） |
| 群集 ID 空間未登記 | namespaces 0 命中「群集」 | **B-26 範圍明文納入**，不另開也可 |
| 收斂「歸錯群」無 body-hash | HANDOFF 9 次；completeness 對群集盲 | **併 B-13**（摘句比對），HANDOFF 待開票 #2 |
| 戳記機檢要三家但 roster 角色閘排除 implementer | 每 review 輪 | **已是 B-34**（勿再開） |
| 主委手寫 brief 誘導格式違規（B2 未覆蓋） | HANDOFF 待開 #5 | **併 B-19**，勿掛回已 DONE 的 B-32 |
| `reconcile_build` 預設 discovery→首次必失敗 | HANDOFF 待開 #4 | **小票或 B-19 子項**（forward） |

**建議執行順序（新判準）**

1. **熱修（天級）**：B-38（FINDINGS_COUNT:0）＋ heading/id-like 規則（B-31④／新票）——解除「合法輪無法銷帳／整輪作廢」。
2. **第 0 批收斂**：B3R → B4 → B5（過渡）→ B6（B-14/B-30）→ B7（timeout）。
3. **每輪固定摩擦**：B-34（roster）→ B-19（brief）→ B-31 便宜 fixup 路徑。
4. **ID／收斂正確性**：B-26（含群集登記，forward）→ B-13（+B-18+B-36+歸錯群摘句）。
5. **判定類共用驗收**：B-29（掛 B-19）。
6. **低成本 fail-open**：B-33 locale；其後 B-5／B-6／B-11。
7. **結構債延後**：B-16 擴充 A/B → B-17 → B-16 本體；B-9→B-28；B-27 規則本體；B-20/B-21/B-37 批後。
8. **不做**：關閉清單 13 張；B-23 全庫標記白名單；裸 B 全庫 lint；B-35。

## GROK-R21-P0-01

**斷言**: 主委 §0「任何 `###` 子標題都會被判 invalid finding ID、整份作廢」在現行 `completeness_check.sh` **過寬**；實際為「id-like 非 canonical」才 hard-fail，中文 `###` 可 PASS。

**碼證**: 探針 `/tmp/govamend-retriage-grok-probe/`：`probe2.md`（`### G-1 extra`）rc=1；`probe3.md`（`### 另外要回答的`）rc=0；`scripts/completeness_check.sh` 四步程序約 :141–200。RECHECK: 重跑上述三檔 `--single`。

**來源摘要**: scripts/completeness_check.sh#12e981972d78

[BLOCKING] 信心度=High。若依錯誤前提去「永久禁止所有 `###`」會把摩擦轉嫁到每位委員／每份 brief，卻不修步驟 3。修法：allowlist 結構標題（Verdict／§0／表名）＋僅 canonical／近似畸形進入 finding 通道；brief 可暫時維持禁 `###` 作工作區，但票面須寫「根因=id-like 規則」。

## GROK-R21-P0-02

**斷言**: 在新判準下 **B-38 應排在幾乎所有「整齊感」票之前**；audit 已有 ≥9 筆具名 B-38 abandon，且會擋住斷路器紀錄／正規銷帳。

**碼證**: `grep -c 'B-38' .claude/gate/audit.log` → 9；樣本 reason 含「合法回報 0 findings」「completeness 判 vacuous」；HANDOFF「票 B-38 應提前」。RECHECK: 同上 grep；讀 `completeness_check.sh` 約 :811 WARN 抽不到 heading ID。

**來源摘要**: handoffs/20260801-GOV-AMEND-BACKLOG.md#76df864efbc5

[BLOCKING] 信心度=High。修法最小：`FINDINGS_COUNT: 0` 明示欄 → completeness PASS；禁把 WARN 無條件改 PASS（與格式錯混淆）。可與 B-35 共用欄位但 **B-35 本體可關閉**。

## GROK-R21-P1-01

**斷言**: 假設「38 張全部都有真實 agent 失誤」為假；至少 13 張應關閉或已無獨立 OPEN 價值。

**碼證**: 本報告逐項表；B-1/2/3 腳本 MISSING 且 OBSOLETE；B-7/10/32 DONE 碼證；B-8/12/35 實證 0 或 0 致害；B-23 高摩擦違判準。RECHECK: 重跑表內查法欄。

**來源摘要**: handoffs/20260806-GOVAMEND-RETRIAGE-BRIEF.md#cd4a38384d0c

[MAJOR] 信心度=High。若仍按 38 張全做，會把 agent 時間耗在非熱路徑，直接違反使用者 2026-08-06 判準。

## GROK-R21-P1-02

**斷言**: 群集 ID 不在 `GOVERNANCE_ID_NAMESPACES.md`，且主委 session 用 `C/D/E/F` 群集編號會撞已登記／禁配空間——此為 **B-26 缺口**，非可讀性問題。

**碼證**: `grep -c 群集 docs/GOVERNANCE_ID_NAMESPACES.md` → 0；該檔 `E-<n>` 明文非 ID；HANDOFF「ID 錯位 9 次」。RECHECK: 同上；讀 namespaces §1。

**來源摘要**: docs/GOVERNANCE_ID_NAMESPACES.md#00b06b45dabc

[MAJOR] 信心度=High。Forward-only 登記新樣式＋B-26 閘；舊收斂不改名。

## GROK-R21-P1-03

**斷言**: B-32 作為「cx_run 無條件 STAMP 注入」**已由 B2 關閉**；HANDOFF 所稱「手寫 brief 仍誘導作廢」屬 **B-19 覆蓋缺口**，不應維持 B-32 OPEN 或重開同名。

**碼證**: `scripts/cx_run.sh:517-521` `stamp|closure` 分支；`tests/governance/test_cxrun_stamp_prompt.py` 存在；HANDOFF:68「B-32 覆蓋缺口…手寫 brief」。RECHECK: 讀 cx_run 該段；對 consult kind 印 prompt 應無 RECONCILE-STAMP 句。

**來源摘要**: scripts/cx_run.sh#b2dff2cf8c0a

[MAJOR] 信心度=High。錯掛票號會讓 DONE 票復活，重演「同一病兩票名」。

## GROK-R21-P2-01

**斷言**: 第 0 批 B5（行為差集報表）在 B-29 落地後若並存，屬短命工；TODO 已自承存活至被 B-29 取代。

**碼證**: `docs/GOVB0_FRICTION_SPEC.md` Task 2.5「票 B-29 實作時取代」；`docs/GOVB0_FRICTION_TODO.md` 同旨。RECHECK: `grep -n 'B-29' docs/GOVB0_FRICTION_TODO.md | head`。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#a1410ec31fcd

[MINOR] 信心度=High。B5 現值高（B-29 未做前）；排程上標記「B-29 DoD 含刪 B5 並存」。

---

ASSUMPTIONS_VERIFIED: completeness heading 四步非「凡###必fail」；B-32 harness 已條件化；B-38 audit≥9；namespaces 無群集；gate waived 兩處仍在；dext=13；B-28 三檔 MISSING；gate_deny reason 分布
TESTS_RUN: completeness --single 三探針（rc 1/0/0）；grep/shasum 如上；未跑全 pytest（唯讀諮詢）
FAILURES_SEEN: 全庫裸 B 掃描逾時已改窄查；主委「###一律作廢」命題被探針修正
SCOPE_CHANGES: none（禁改碼禁改票）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
