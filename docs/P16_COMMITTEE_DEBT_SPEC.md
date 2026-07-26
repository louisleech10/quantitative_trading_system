# P1-6 委員未結案債狀態機 — SPEC

> **版本 v1.2**（R12 三家 21 findings 收口）　|　日期：2026-07-26　|　對應 TODO：`docs/P16_COMMITTEE_DEBT_TODO.md`（待生成）
>
> **事件定義單一真相源**：`scripts/audit_events.json`。**本文件不重列欄位表／枚舉值／常數值**——一律 pointer；事件名可作為 pointer 出現，但 **Task 0.1 的守衛實作後須機械約束**：本文件出現的 P16 命名空間事件名必須 ⊆ registry（改名 registry 而 SPEC 留舊名 → rc≠0）。
> **決策沿革（為什麼這樣設計、推翻過什麼）**：`handoffs/reconcile/p16-*/synth.md`（11 輪，四家共 ~250 findings，每輪 completeness rc=0）。
> **舊版 SPEC**：`handoffs/p16-spec-archive/`（v0.3–v0.8）。

## 一句話

主委每次問完委員，**必須把意見完整收好**才能再問下一輪——由 audit 客觀事件強制，不靠自律。

## §RISK 風險分級
- **大小**：**大**。改動 `gate.sh` / `cx_run.sh` / `committee_run.sh` 三支共用控制流 + 新增 audit 事件 schema + 新閘門；287 個 governance 測試依賴 `gate.sh`。
- **命中高風險原則**：**(b) 跨模組/共用路徑**；**(c) 多 phase/難回退**（audit append-only，schema 選錯無法回收）。**不命中 (a)/(d)**（不碰數值/特徵/ML/回測）。
- RISK-HIT: b,c
- 未命中 (a)/(d) → §G 移 §N；**adversarial review 仍必跑**（大任務鐵律）。

## §A 假設與待使用者確認

### FACT-RECEIPT（逐條附實跑命令與輸出）
- FACT-RECEIPT: `python -m pytest tests/governance -q` → 印出 `287 passed`（Claude 實跑 2026-07-25；codex 獨立複跑 `287 passed in 68.18s`）
- FACT-RECEIPT: `grep -n "audit\|AUDIT" scripts/cx_run.sh` → 印出 `（0 命中）`（Claude 實跑 2026-07-25）
- FACT-RECEIPT: `rg -c 'committee_family_dispatch' .claude/gate/audit.log` → 印出 `0`；五個討論輪在 audit 上皆為 1 筆 `committee_dispatch` + `family=unknown`（grok/codex 實跑 2026-07-25）
- FACT-RECEIPT: audit 全史 `family=grok` → **0 筆**（Claude 實跑 2026-07-25）
- FACT-RECEIPT: 零 canonical ID 的來源跑 `reconcile_build.sh` → `COMPLETENESS FAIL: …vacuous…`、**rc=1**（Claude/grok/codex 各自實跑）→ **零 findings 產出無法走正常清帳，終局出口結構上必要**
- FACT-RECEIPT: `completeness_check.sh` 同一份 sources：`discovery lock rc=0` vs `review argv rc=1（P0/P1 missing digest）`（codex 實跑 2026-07-26）→ **`result_state` 必須綁定 mode**
- FACT-RECEIPT: post-cutoff audit 現存 **181 筆**無 `sequence`，全為 `gate_deny`/`committee_dispatch`/`committee_output`，`committee_round_open` = **0**（codex/composer/grok 各自實跑 2026-07-26）→ **provenance gate 必須按事件類過濾**
- FACT-RECEIPT: `nl -ba scripts/gate_check.sh | sed -n '67,76p'` → fresh token 直接 `exit 0`，**不重讀 audit**（codex 實跑 2026-07-25）
- FACT-RECEIPT: `rg -n 'gate|token|GATE' scripts/reconcile_build.sh` → **0 命中**（composer/grok 實跑 2026-07-26）→ **清帳路徑不經 dispatch 閘，故「有債萬事停」非死鎖**
- FACT-RECEIPT: `rg -l GATE_DIR_OVERRIDE tests/governance` → `14 檔`；`rg 'pop.*GOVERNANCE_TEST_HARNESS' tests/governance` → `6 檔 9 處`（composer 實跑 2026-07-25）

### 已確認結果（使用者裁決，憲法級）
1. **債務範圍（D2）**：委員派工一律開債，**不看有無下游、不看結論採不採用**（「討論完決定不採用也是結論」）。
2. **分類機制**：**不得**用節點類別白名單（不得列舉節點種類）；且經 11 輪實證，**不得**用任何主委可自報的信號當分類器（`task_id` 命名／`round_kind` 宣告／檔案範圍宣告／brief 是否引用範本／家族數，五種全被三家打穿）。
3. **架構（一扇門）**：所有委員派工一律走 `committee_run.sh` → **一律開債（含只派一家）**，**無分類、無豁免、無執行通道**。家族數只決定**清帳嚴格度**。
4. **擋門範圍**：**債未清 → 擋所有新派工，含實作**。誠實成本：債未清期間不能開新輪；**但清帳動作不經 dispatch 閘**（FACT-RECEIPT 已證），且同 round retry 放行 → **永遠有出路**。
5. **TTL**：軟 TTL **7 日**（值見 registry `constants.ttl_days`）；`EXPIRED_OPEN` 仍擋；**嚴禁自動 clear**。
6. **流程**：走完整大任務管線，不跳步。
7. **凡有可用腳本一律套用（2026-07-26 使用者定）**：**不限於「收集 reconcile」這一個節點**。repo 內已存在可用工具者，一律呼叫工具，**不得手搓等效替代**。**工具清單與節點對應一律讀 `scripts/governance_tools.json`（機械盤點，`scripts/*.sh` 全覆蓋），本文件不重列**——初版曾在此手列 7 支，而同日已因憑印象列豁免檔錯過一次（列 3、實際 7），**憑印象列清單是本 epic 反覆出現的病灶**。
   **理由**：手搓的每一次都是一次掉項/引號/PATH 事故的機會（本 epic 已累計多次）；工具存在卻不用，等於把已消滅的錯誤重新引回。
   **⚠️ 範圍限制**：本條的**強制力尚未機械化**——`governance_tools.json` 內 `mandatory` 欄位的判定尚未經委員會裁決，且無任何 hook/CI 呼叫其守衛。**本條目前＝人工紀律**，另立票處理機械強制（屬中任務，須走完整管線）。

### 待使用者確認
**待確認：無**

### 誠實邊界（**不得宣稱機器覆蓋**；三家多輪一致；第 10-13 條為 R12 新增）
1. **純對話綜合**：讀完 N 份直接講結論、不派任何工 → **永遠**攔不到。
2. **`cx_run` 直呼（V-D）**：拿到**合法** `round_id` 即可直呼 `cx_run` 追加派工，不經 `committee_run`。Task 1.2 的 membership 檢查限制其危害（不能換 brief、不能重派 `success` 家族），**但擋不住**。正解需工具 mint 的不可轉移 capability token，本版不做。
3. **拆分成 N 次單家**：**各自都會開債**（不再免債），但機器**不會強制**把 N 份意見合併成一份。
4. **`gate_check.sh` 無 jq → fail-open（V-G）**：既有邊界，範圍外。
5. **`gate.sh artifact` / `register-output` 不在債務閘範圍**：主委仍可在 open 債下創建治理文件。
6. **`clear_format_failure` 是「付費出口」**：條件為全家族 `format_failed` 且 attempt 皆達上限。主委可蓄意寫爛 brief，燒 `5×N` 次派工換一次清帳。**機器擋不住「brief 品質」**。
7. **`clear_all_degraded` 同為高摩擦出口**：主委可選擇 degrade 路徑（接受 `failed` 與 `format_failed`）而非等全族 `format_failed`，摩擦略低於第 6 條。
8. **`approver` / `remediation_owner` 身份不可驗證**：適用第 6、7 條與 `committee_family_degrade`。機器只驗非空與前置條件，**不驗簽核者身份或授權來源**。
9. **FS 信任模型**：有 `.claude/gate/audit.log` 寫權者，可偽造**帶 `sequence` 且 `producer` 填對**的事件（無簽名/HMAC）。Task 1.4 堵的是「無 sequence 隱形」，不是「有號偽造」。
10. **豁免清單的殘餘旁路（R12 3/3 家族）**：守衛 C11 擋「豁免與現實不符」（殭屍豁免／憑空 allow token／豁免真事件名），**但擋不住「先寫硬編、再補一條真實對應的豁免」**。委員建議的「變更豁免清單須第二家族 review」屬流程層，機器擋不住。
11. **片段掃描是啟發式**：C9b 擋字面前綴拼接（含裸賦值），**擋不住 base64／多層變數間接組裝**。
12. **family SoT 竄改**：C6 驗 SoT 的結構自洽（`review`/`executor` ⊆ `families`、無重複），**但整份 SoT 被替換**（codex 實跑：全改 `forged` 仍綠）屬第 9 條 FS 信任模型，非守衛能覆蓋。
13. **Phase 0 只證 registry 自洽**：不證與尚未實作的 Phase 1-4 消費端一致（composer R12-P1-04）。該缺口由 Task 4.4 的「registry 欄位 ↔ 消費端讀取」矩陣測試承接，**Phase 0 通過不等於實作正確**。
- 以上十三項 **§V 全部 mutation 不宣稱覆蓋**。

## §C 約束
- 解耦 7 條照舊（只動 `scripts/` 治理層與 `tests/governance/`）。
- **不得改寫 V-A / V-B / V-C / V-M 內部**（已通過 codex 原提出方 nested PoC 複驗）；只可旁側新增呼叫（grok 已實讀確認可行）。
- **反 bypass 紅線**：任何新增 env override 一律綁 `GOVERNANCE_TEST_HARNESS=1`。
- **家族不得寫死**：一律讀 SoT `scripts/governance_families.json`。
- **事件/欄位/枚舉/常數不得寫死**：一律讀 `scripts/audit_events.json`。
- **工具優先（裁決 7 的機械面）**：本 SPEC 的任何 Task 不得新寫已存在工具的等效邏輯；新腳本若與既有工具功能重疊，須改為呼叫既有工具。**驗收**：實作 diff 內不得出現重造的 completeness/合併/派工邏輯（雙家 code review 逐項確認）。
- 下游消費者 `scripts/review_quorum_check.sh` 解析 `committee_dispatch.task_id`；新事件不得破壞其解析。

## §G Golden / Baseline
移 §N 標 N/A（RISK-HIT 無 a/d）。

## §P Phase 與依賴

> **依賴鏈**：Phase 0（真相源）→ Phase 1（留痕）→ Phase 2（帳本）→ Phase 3（銷帳）→ Phase 4（擋門＋硬化）。**線性，無 forward dependency**。
> **凡涉及事件名／欄位／枚舉／常數，一律讀 `scripts/audit_events.json`，本文件不重列。**

---

### Phase 0 — 事件真相源（依賴：無）

**Task 0.1 — `scripts/audit_events.json` + 一致性守衛**
- 目標：所有事件定義只有**一份**，消滅「新增事件漏同步 N 處」。　檔案：`scripts/audit_events.json`（已建）、新增 `scripts/audit_events_check.sh`
- 改法：①registry v2 為唯一定義來源，**說明文字一律集中於頂層 `docs` 物件，其餘容器不得出現 `_` 前綴鍵或說明字串**（R11：metadata 混進資料容器會讓消費端 iterate 拿到 str）②守衛 `audit_events_check.sh` 實作一致性檢查（**項目清單與數量一律見腳本檔頭，本文件不重列**——寫兩處必漂移，R12 已實際漂移一次）③**任何腳本禁止硬編事件名/欄位/枚舉/常數**，一律讀 registry；legacy 相容的既有硬編須明列於 `hardcode_scan_exemptions`（**警告：憑印象列必不完整——原型階段憑印象列 3 檔，機械掃描實得 7 檔。實作者須以掃描結果建清單，禁憑記憶枚舉**）
- **驗證（可證偽）**：`pytest tests/governance/test_audit_events_registry.py -q` 全綠；`bash scripts/audit_events_check.sh` rc=0；**R12 三家全部攻擊向量須轉紅**（下列 18 類為驗收清單；參考實作見 `handoffs/p16-phase0-reference/`，**該目錄非規格、不得直接複製當交付**）：registry 面＝空清單 vacuous／event 加白名單外鍵／交換 `clear_kind` 映射值／移除必要欄位／旗標互斥／constants 型別／`family_valued_fields` 漏登或清空；檔案面＝`.py` 消費端硬編／裸賦值拼接 `P=committee_`／`"committee_${kind}"` 拼接／SPEC 缺檔／`p16_namespace_prefixes=[]`／audit 含 post-cutoff 未知 P16 事件；**豁免面＝把真事件名塞進任一豁免清單、憑空新增不存在的 allow token（皆須轉紅）**
- **邊界（≥2）**：①registry 缺檔 → 所有消費端 fail-closed ②JSON 壞 → fail-closed ③消費端 iterate 資料容器遇 `_` 前綴鍵 → 守衛先擋（**實建當下即踩過此坑**）④**post-cutoff 出現於 `p16_namespace_prefixes` 但不在 `debt_events` 的事件 → fail-closed 拒認（非告警）**——此為 R10「新增 `all_degraded` 漏列白名單」的根治：告警＝fail-open，等於沒擋 ⑤`AUDIT_EVENTS_REGISTRY_OVERRIDE` 僅在 `GOVERNANCE_TEST_HARNESS=1` 生效，否則 fail-closed
- **存活至**：永久保留（Phase 1-4 全部依賴）
- **覆蓋風險**：無
- 不可做：不得在 SPEC/TODO/腳本任何處重複列舉 registry 內容

---

### Phase 1 — 留痕（依賴：Phase 0）

> Phase 1 內部實作順序＝1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6

**Task 1.1 — `committee_run.sh` mint round 並寫 `committee_round_open`（＝開債）**
- 目標：一輪派工有唯一且主委不可竄改的識別；**寫入即開債，無分類、無豁免**。　檔案：`scripts/committee_run.sh`（60-75 行區塊）　影響面：Claude 直接呼叫；`docs/COMMITTEE_DISPATCH_GUIDE.md`
- 改法：①`round_id` **由本腳本 mint（UUID v4）**；`--round-id <既有>` 只用於繼承 OPEN/PARTIAL round（Task 1.3），**主委不可指定新 id** ②寫入時機＝`gate.sh dispatch` 成功**之後**、啟動 `cx_run.sh` **之前**（防第一輪自咬）③append 失敗 → 立即 `exit≠0`、**不得啟動 `cx_run`**，並 best-effort 寫 `round_open_failed` ④`participants` 含 `advisory_only`（agy）、`quorum_eligible` 不含 ⑤欄位依 registry，缺欄 fail-closed
- **驗證（可證偽）**：`pytest tests/governance/test_debt_emit.py -q` 全綠；派 3 家後 audit 恰 1 筆 `committee_round_open`，`participants` 長度 3、`expected_outputs` 3 鍵；**派 1 家也必須寫**（無豁免）；`--task-id` 缺 → rc≠0；**未給 `--round-id` → 自動 mint（不得要求必填）**；同一 `round_id` 第二筆 → rc≠0；`codex,agy` → `participants` 2、`quorum_eligible` 1
- **邊界（≥2）**：①N=1 → 仍開 round ②繼承既有 round → 不 mint 新 id，改寫 amendment ③只含 agy → 仍開 round，`quorum_eligible` 空 ④gate 拒發 token → 不得寫 `round_open` ⑤append 失敗 → `exit≠0` 且不啟動 `cx_run`
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得讓主委指定新 `round_id`；不得在 gate 前寫；**不得對 N=1 略過開債**

**Task 1.2 — `cx_run.sh` emit per-family 事件 + round membership 與 retry 契約**
- 目標：每家派工/結果各留一筆痕（家族名由 `$1` 直取）；**retry 契約在此層也驗**（不可只掛外層 wrapper）。　檔案：`scripts/cx_run.sh`　影響面：`scripts/committee_run.sh`
- 改法：①派工前寫 `committee_family_dispatch`、CLI 結束寫 `committee_family_result`（欄位依 registry）②`result_state` 三態依 registry `enums.result_state`；**`success` 判定必須呼叫與 Task 3.1 相同的 finding validator（單一函式，禁複製正則），且使用該 round 的 `lock_mode`**（FACT-RECEIPT 已證 discovery/review 行為不同）③**fail-closed 前置（全部成立才派）**：`ROUND_ID` 已設且 audit 有對應 `committee_round_open`；`family ∈ effective_participants`；`$3 == effective_expected_outputs[family]`；`sha256_norm($2) == round_open.brief_sha256_norm`（**演算法定義見 registry `docs.brief_sha256_norm_algo`，實作者禁自行決定 normalize 規則**——各自實作會產生互不相容的 norm）；該 `(round_id,family)` attempt < `constants.attempt_cap`；該 family 最新 `result_state ≠ success`（`failed`/`format_failed` **皆可重派**）④讀取＋attempt 保留＋append＋派工**綁同一 `flock`**
- **驗證（可證偽）**：`pytest tests/governance/test_debt_emit.py -q` 全綠；合法呼叫後 audit 新增 dispatch+result 各 1 筆且 `family == grok`（**非 unknown**）；`ROUND_ID=attacker` → rc≠0 且 audit 零新增；**換 brief 掛既有 round → rc≠0**；重派 `success` 家族 → rc≠0；**兩程序併發 retry → 總 attempt 不超過上限**；**同一產出在 discovery round 與 review round 下 `result_state` 依各自 `lock_mode` 判定且與該 round 的 clear 路徑一致**
- **邊界（≥2）**：①`ROUND_ID` 未設 → 拒派 + audit 零新增 ②家族不在 SoT → 拒派 ③audit 檔不存在 → 建立而非崩潰 ④並發 3 家 → 3 筆完整不交錯 ⑤CLI 失敗（如 503）→ 仍寫 result 帶 `cli_rc`，不得靜默
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得從 `output_path`/`review_role` 推導家族；**不得自創第二套 finding 判定器**

**Task 1.3 — `committee_round_amendment`：補派契約 + effective roster 定義**
- 目標：讓「繼承既有 round」不能變成「把新討論偽裝成 retry」；**並定義 effective roster 供全鏈共用**。　檔案：`scripts/committee_run.sh`
- **effective roster（全鏈唯一定義；ledger/clear/quorum 一律用此，禁止直接讀 `round_open.participants`）**：
  ```
  effective_participants     = round_open.participants ∪ ⋃(amendment.added_families)
  effective_expected_outputs = round_open.expected_outputs ∪ ⋃(amendment.expected_outputs_delta)
  effective_quorum_eligible  = (round_open.quorum_eligible ∪ ⋃(amendment.quorum_eligible_delta))
                               − (advisory_only ∪ ⋃(amendment.advisory_delta))
  ```
- 改法：帶 `--round-id` 時**全部成立才放行**：①狀態 ∈ {OPEN, PARTIAL, PENDING} ②`brief_sha256_norm` 相同 ③既有家族 path 等於 round_open；新家族 path 須在本次 `expected_outputs_delta`；roster **expand-only** ④attempt 未達上限 ⑤最新 `result_state ≠ success` ⑥`task_id` 與 round_open 相同 ⑦**delta 一致性 invariant**：`quorum_eligible_delta ⊆ added_families`、`advisory_delta ⊆ added_families`、`expected_outputs_delta` 的 keys ⊆ `added_families`、兩 delta 互斥、所有 family ∈ SoT、**`effective_quorum_eligible ⊆ effective_participants`**
- **驗證（可證偽）**：`pytest tests/governance/test_debt_retry.py -q` 全綠；**換 brief 帶同一 `--round-id` → rc≠0**；roster 縮減 → rc≠0；超過 attempt 上限 → rc≠0；換 `task_id` → rc≠0；`added=[composer]` 配 `quorum_eligible_delta=[grok]` → **rc≠0**；`expected_outputs_delta` 含 `added_families` 外的 key → **rc≠0**；正常補派 → rc=0
- **邊界（≥2）**：①round 已 CLOSED/ABANDONED → 拒繼承 ②`brief_sha256_norm` 差一 byte → 拒 ③amendment append 失敗 → 同 Task 1.1 邊界⑤ ④`reason` 短於 `constants.reason_min_chars` → 拒
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得允許換 brief 沿用 round；不得無上限 retry

**Task 1.4 — `audit_append.sh`：唯一寫入點 + 唯一性/序號/provenance**
- 目標：讓 append-only 帳本成為可稽核 contract。　檔案：新增 `scripts/audit_append.sh`
- 改法：①`event_id` 重複 → **fail-closed 拒寫** ②`sequence` 由單一 allocator 以 `flock` 保護「讀尾端 → +1 → append」；allocator 起始值 ＝ `max(existing sequence) or 0` ③`producer` 由本腳本**強制填入自身**（呼叫端不得指定）；`origin_script` 由呼叫端提供並驗 ∈ registry 允許值 ④**provenance gate 只作用於 registry `debt_events` 白名單**：白名單事件在 cutoff 後缺 `sequence` 或 `producer != audit_append.sh` → **fail-closed 拒認**；**非白名單事件（registry `non_debt_legacy_events`）pre/post 皆不參與 gap 掃描、不計債、不觸發 fail-closed** ⑤所有 Phase 1-4 新事件**一律經此腳本**，禁各自 `echo >>`
- **驗證（可證偽）**：`pytest tests/governance/test_audit_append.py -q` 全綠；重複 `event_id` → rc≠0；**兩程序併發各寫 100 筆 → sequence 連續無重複無缺口**；白名單事件人工插入 gap → ledger rc≠0；**混合現存 181 筆 legacy（無 sequence）+ 新事件 1..N → `debt_ledger.sh --list` rc=0**（防誤殺真 audit）；呼叫端試圖指定 `producer` → 被覆寫
- **邊界（≥2）**：①audit 檔不存在 → 建立 ②`flock` 逾時 → fail-closed ③registry 缺檔 → fail-closed ④出現在 audit 但不在 registry 的 P16 命名空間事件 → **fail-closed 拒認**（見 Task 0.1 邊界④）
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得讓任何 Task 繞過本腳本；不得硬編事件名

**Task 1.5 — 封住 `impl`/`stamp` brief 跳過 P1-1 範本閘**
- 目標：消滅「標 `impl` 即跳過範本+前提檢查」（與紅隊 V-E 同構）。　檔案：`scripts/cx_run.sh:41-61`
- 改法：brief 若**引用**任一委員範本（`SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT` / `COMMITTEE_SEMANTIC_REVIEW_TEMPLATE` / `COMMITTEE_FINDING_TEMPLATE`）→ **機械覆寫為 findings 類**，強制走 P1-1 兩項檢查，**不看 `brief-kind` 宣告值**。
- **⚠️ 誠實邊界**：反向（討論 brief 標 `impl` 且**不引用**範本）擋不住——但一扇門下該輪**仍會開債**，且產出若無合格 finding 會判 `format_failed` → 須重派至上限才能走終局出口。**摩擦本身即為防線。**
- **驗證（可證偽）**：brief 標 `brief-kind: impl` 但引用 adversarial 範本 → 仍執行 P1-1；缺前提宣告 → rc≠0；`pytest tests/governance/test_brief_conformance.py -q` 全綠
- **邊界（≥2）**：①真 impl brief（不引用任何範本）→ **行為不變，不誤擋**（codex 實跑 `1 passed` 佐證此測試須保持綠）②brief 僅在註解提及範本名 → 仍覆寫（取嚴）
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得放寬既有 `review|consult|closure` 分支檢查；**不得用產出 marker 掃描當分類器**（三家一致：誤殺 + 可繞）

**Task 1.6 — 更新派工規範文件**
- 目標：把「一扇門、一律開債」寫進規範。　檔案：`docs/COMMITTEE_DISPATCH_GUIDE.md`
- 改法：①範例補 `--task-id` ②新增「一扇門」一節：所有委員派工一律走 `committee_run.sh`、一律開債，**含只派一家** ③新增「輪次與債務」語意（開債／清帳嚴格度／retry／TTL）④**誠實邊界以 §A 為唯一真相源，pointer 過去，不重列**
- **驗證（可證偽）**：`grep -c '\-\-task-id' docs/COMMITTEE_DISPATCH_GUIDE.md` ≥ 1（現況 0）；`grep -c '一扇門\|一律開債' …` ≥ 1
- **邊界（≥2）**：①文件與腳本不一致 → 由腳本 fail-closed 兜底 ②條數/枚舉一律 pointer，不重列
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得只改文件不改腳本

---

### Phase 2 — 債務帳本（依賴：Phase 1）

**Task 2.1 — `debt_ledger.sh`：只讀 audit 算未結案債**
- 目標：由客觀事件算出哪些 round 欠收集整理。　檔案：新增 `scripts/debt_ledger.sh`（**不另存狀態檔**）
- 改法：①只認 `startswith("{")` 的 JSON 行 ②cutoff 依 registry `cutoff_ts`；**禁 CLI/env 自由指定**，僅 `GOVERNANCE_TEST_HARNESS=1` 可覆寫 ③每個 `committee_round_open` 即一筆債；狀態依 registry `enums.round_state`：無合法 clear → OPEN；有家族最新 `result_state ∈ {failed, format_failed}` 且未補派未 degrade → PARTIAL；逾 `expires_at` → EXPIRED_OPEN；有合法 clear（含三種 `closes_debt` 事件）→ CLOSED；有 `debt_abandon` → ABANDONED（終結）；有 `round_open_failed` → **不計債** ④**roster 一律用 effective roster**（Task 1.3），禁止直接讀 `round_open.participants` ⑤有 `supersedes` 者取最新；白名單事件的 `sequence` gap/duplicate → fail-closed
- **驗證（可證偽）**：`pytest tests/governance/test_debt_ledger.py -q` 全綠；派 3 家 → `--list` 印 1 筆 OPEN；**派 1 家 → 也印 1 筆 OPEN**；clear 後 → 0 筆；cutoff 前事件 → 0 筆；**N=1 經 amendment 補成 2 家 → 清帳分流依 effective roster（長度 2）**
- **邊界（≥2）**：①**audit 檔缺失** → fail-closed ②**audit 存在但零 JSON 事件** → **無債，rc=0 放行**（14 檔測試用隔離空 audit；不分三態會整批真回歸）③**ledger 腳本缺失/崩潰** → fail-closed ④同一 `round_id` 兩筆 `round_open` → fail-closed
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得另存 JSON 狀態檔；不得靜默自動過期

---

### Phase 3 — 銷帳（依賴：Phase 2）

**Task 3.1 — 完整清帳：completeness PASS 綁 round + effective roster**
- 目標：跑完機械合併且 0 掉項才算還債。　檔案：`scripts/reconcile_build.sh`（completeness PASS 後）+ 新增 `scripts/debt_clear.sh`
- 改法：寫 `committee_debt_clear`（欄位依 registry），**全部成立才寫**：①該 round 存在 OPEN/PARTIAL 債 ②`set(lock.expected_roster)` ⊇ **`set(effective_participants)`**（少一家即拒）③`completeness_rc == 0` ④時間戳晚於 `round_open` ⑤`lock_sha256` 相符。**本 Task 的 finding validator 必須與 Task 1.2 為同一函式。**
- **驗證（可證偽）**：`pytest tests/governance/test_debt_clear.py -q` 全綠；拿 A 輪 lock 銷 B 輪債 → rc≠0；**roster 少一家（含 amendment 新增的）→ rc≠0**；正常 → rc=0 且 ledger 轉 CLOSED
- **邊界（≥2）**：①重複銷帳 → 冪等 no-op ②`completeness rc=3`（DEGRADED_PENDING）→ 不得整輪銷帳；合法 degrade 可 `clear_kind=family_degrade` 結**單一家族**帳 ③`round_open` 不存在 → 拒 ④lock 被竄改 → sha256 比對失敗即拒 ⑤PARTIAL → 缺席家族須補派成功或合法 degrade
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得接受 `waived:` 當銷帳；不得讓 `--force` 繞過本 Task 五項綁定

**Task 3.2 — 清帳嚴格度 + 終局出口**
- 目標：家族數決定「清帳要多嚴」；並為「委員交不出合格 finding」提供**高摩擦終局**。　檔案：`scripts/debt_clear.sh`
- 改法：
  1. **`len(effective_participants) ≥ 2` → 必須走 Task 3.1**，禁走「**非 `attempts_exhausted`**」的簡化出口。
  2. **`== 1` 亦不得以 prose-only 清帳**；單家 round 合法出路同多家。
  3. **`committee_debt_clear_format_failure`（適用所有家族數，含 ≥2）**：全部成立才寫——①**所有** effective 家族的最新 `result_state == format_failed`（**直接讀 audit 既有值，禁止第二套掃描規則**）②每家族 attempt 均達上限 ③`reason` ≥ `constants.reason_min_chars` ④`approver` 非空
  4. **`committee_debt_clear_all_degraded`（終局出口 B）**：全部成立才寫——①**所有** effective 家族皆有**有效（未逾期）**的 `committee_family_degrade` ②每家族 attempt 均達上限 ③`reason` ≥ 下限 ④`approver` 非空 ⑤`degrade_event_ids` 與 effective 家族**精確一一對應**（跨 round／重複／過期 ID → 拒）。**不要求 `completeness_rc == 0`**（該 round 結構上不可能有合格 finding）。
- **⚠️ 誠實邊界**：見 §A 第 6/7/8 條（付費出口、身份不可驗證）。
- **驗證（可證偽）**：`pytest tests/governance/test_debt_clear.py -q` 全綠；**≥2 走「非 attempts_exhausted」的簡化出口 → rc≠0**；**≥2 且全 `format_failed` 且 attempt 全達上限 → rc=0（終局出口必須開）**；`degrade_event_ids` 缺一家/含跨 round/含過期 → rc≠0；`reason` 過短 → rc≠0；**產出「帶 `^Verdict:` 但零合格 finding」→ `result_state=format_failed` 且終局出口可用**（不得因舊掃描規則判 False）
- **邊界（≥2）**：①產出檔缺失 → 依 audit 既有 `result_state`；若連 `committee_family_result` 都缺 → **fail-closed 拒清** ②同 round 已有 clear → no-op ③`result_state` 事件重複 → 取 `sequence` 最大者 ④`output_sha256` 與現檔不符 → **fail-closed**（防 stale 狀態當清帳證據）
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得接受 `waived:` 字串；不得在 `attempts_exhausted` 未成立時開放簡化出口

**Task 3.3 — `committee_debt_supersede`：可稽核的更正路徑**
- 目標：錯誤寫入的 clear 有 append-only 更正路徑。　檔案：`scripts/debt_clear.sh`（`--supersede <event_id>`）
- 改法：`direction` 依 registry `enums.supersede_direction`（**僅 `tighten`**）：CLOSED → OPEN。**不得放寬**。ledger 對同一 round **取嚴**。
- **驗證（可證偽）**：`pytest tests/governance/test_debt_supersede.py -q` 全綠；用 supersede 把 OPEN 變 CLOSED → rc≠0；正常收緊 → ledger 回 OPEN
- **邊界（≥2）**：①`supersedes` 指向不存在 event_id → 拒 ②指向非 clear 類 → 拒 ③已 ABANDONED → 拒
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得允許放寬向 supersede

**Task 3.4 — `committee_family_degrade`：單家族退出清帳要求**
- 目標：讓「某家族反覆交不出合格產出」有可稽核的退出機制。　檔案：`scripts/debt_clear.sh`（`--degrade`）
- 改法：①**前置**：該家族最新 `result_state ∈ {failed, format_failed}` **且** attempt 已達上限 ②欄位依 registry（含 `expiry`、`remediation_owner`）③**ledger 轉移**：該家族退出 `effective_participants` 的**清帳要求**（audit 紀錄保留）④**`expiry` 逾期 → 該 degrade 失效，round 回 PARTIAL** ⑤**每 `(round_id, family)` 最多一個 degrade 事件**——逾期後**不得再 degrade**
- **⚠️ 逾期後的可達終局（v1.0 明列，防死鎖）**：逾期且 attempt 已達上限的家族，其 round 仍可走：**(a)** 全族 `format_failed` → `format_failure`；**(b)** 全族有**有效** degrade → `all_degraded`；**(c)** 逾 TTL → `debt_abandon`。**若該家族 `result_state == failed`（非 `format_failed`）且其 degrade 已逾期，(a) 與 (b) 皆不可達** → 此時**允許以 `--degrade --renew-once` 重開一次**（附 `supersedes` 指向**同 round 同 family 且已逾期**的 degrade 事件，配額為**每 (round_id, family) 至多一次**）。**配額不得是「每 round 全域一次」**——≥2 家族同時卡在此狀態時只能救 1 家，其餘仍死鎖（R11 實例）。否則只能等 TTL。此為**明列成本**，非隱含死鎖。
- **驗證（可證偽）**：`pytest tests/governance/test_debt_degrade.py -q` 全綠；`result_state == success` 的家族走 degrade → rc≠0；attempt 未達上限 → rc≠0；六欄缺一 → rc≠0；正常 degrade 後 ledger 顯示該家族不再阻擋清帳；`expiry` 逾期 → round 回 PARTIAL；**同 (round,family) 第二次 degrade（無 `--renew-once`）→ rc≠0**；**同 (round,family) 第二次 `--renew-once` → rc≠0**；**但同 round 不同 family 各用一次 → 皆 rc=0**（證偽「全域一次」誤設計）；**`supersedes` 指向他 round／他 family／未逾期的 degrade → rc≠0**；**`failed` + 逾期 + `--renew-once` → rc=0 且四條終局至少一條可達**
- **邊界（≥2）**：①全部家族都 degrade → 仍須 `all_degraded` 的 approver+reason，**不得一鍵清** ②degrade 後該家族成功交付 → degrade 自動失效 ③`expiry` 缺 → 拒 ④`--renew-once` 未附 `supersedes` → 拒
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得讓 degrade 繞過 attempt 上限；不得對 `success` 家族使用；不得無限續期

---

### Phase 4 — 擋門與硬化（依賴：Phase 3）

**Task 4.1 — `gate.sh` 債務閘**
- 目標：有未清債 → 拒發**開新 round 的 token**；同 round retry 放行。　檔案：`scripts/gate.sh`（dispatch 分支）
- 改法：①新增 `_check_open_debt()`，**旁側呼叫**，不改 V-A/V-B/V-C/V-M 內部 ②**判定極簡**：會開新 round（未帶 `--round-id`）且存在任一 OPEN/PARTIAL/EXPIRED_OPEN 債 → **拒發**；帶合法 `--round-id`（通過 Task 1.3 全部條件）→ 放行 ③**不分討論/實作**（使用者裁決 4）④**順序寫死**：`必填欄位檢查 → 債務閘 → _run_completeness_gate → V-C/V-M → high-risk adversarial → review-quorum → template_check → emit → 寫 token` ⑤**必須掛 `gate.sh` 本體**（`gate_check.sh` 有 jq fail-open 與 fresh-token 兩個旁路）
- **驗證（可證偽）**：`pytest tests/governance/test_debt_gate.py -q` 全綠；有 OPEN 債時開新 round → rc≠0 無 token；同狀態帶合法 `--round-id` → rc=0；**有 OPEN 債時實作 dispatch（`--spec`）→ 也 rc≠0**（使用者裁決 4 的具名 oracle）；債清後 → rc=0
- **邊界（≥2）**：①`GATE_DIR_OVERRIDE` 指向空 audit → 綁 `GOVERNANCE_TEST_HARNESS=1`，且**空 audit ＝無債放行** ②`debt_ledger.sh` 缺失/崩潰 → fail-closed ③多筆 open 債 → 全部列出，任一未清即拒 ④本 epic 自身派工同樣受管 ⑤`EXPIRED_OPEN` → 仍擋，訊息升級為要求 `debt_abandon`
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得新增 `--debt-waived:` 逃生口；不得改寫 V-A/V-B/V-C/V-M

**Task 4.2 — token ↔ round handoff 與 `debt_epoch`**
- 目標：①消滅「token 綁 round 但 round_open 在 gate 之後才寫」的時序矛盾 ②讓 fresh token 在開債後失效。　檔案：`scripts/gate.sh`（token 寫入）、`scripts/gate_check.sh:67-76`
- 改法：①`committee_run.sh` 先 mint `round_id`，以 `--pending-round-id` 傳給 `gate.sh` ②token 附 `pending_round_id` 與 `debt_epoch`；**此時不要求 audit 已有 `round_open`** ③token 內寫**不可變** `pending_deadline_ts = mint_ts + N`（N 依 registry `constants`，見下）；判定用 `now > pending_deadline_ts`，**不得用 token 檔 mtime**（`touch` 不得延長；`flock` 等待期間不延長）④出現與本 token `pending_round_id` 相符的 `round_open_failed` → token **即刻失效** ⑤`debt_epoch` 計入事件 ＝ registry 中 `in_debt_epoch:true` 者 ⑥**epoch 自污豁免**：計算「當前 epoch」時**排除與本 token `pending_round_id` 同一 round 的所有事件**（`round_open` 與 `amendment` 皆排除）⑦`gate_check.sh` 對 fresh token 不再直接 `exit 0`：`debt_epoch` ≠ 當前 epoch（已扣除自身 round）**且**有 OPEN 債 → 擋
- **N 的決定（Phase 1 進場 gate）**：量測 workload ＝ `committee_run.sh` 派 3 家 × 20 次的 admission→append latency，取 **p99**；`N = clamp(ceil(p99 × 3), 5, 60)`；**若 `ceil(p99×3) > 60` → 不得部署固定時間窗，改用原子 handoff（gate 與 `round_open` 同一交易）**。量測結果寫入 TODO 驗收 receipt；registry 現值為暫定。
- **驗證（可證偽）**：`pytest tests/governance/test_debt_token_epoch.py -q` 全綠；**預 mint → 寫本輪 `round_open` → 同 token 窗內 check → 必須放行**；**同 round 補派寫 amendment → 同 token 仍放行**；**另開第二筆債 → 必須擋**；取得 token → 另開 OPEN 債 → 用該 token 開新 round → 被擋；逾 deadline 無 `round_open` → token 失效；出現 `round_open_failed` → **立即**失效；`touch` token → 不得延長
- **邊界（≥2）**：①`debt_epoch` 相同 → 放行，零額外摩擦 ②audit 不可讀 → fail-closed ③既有 287 測試的 token fixture → 依 §V 矩陣補欄 ④`gate_check` 總耗時上限 100ms（實測全檔 JSON scan 0.007-0.038s，直接全掃可接受）
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得用 mtime 判 pending 期限

**Task 4.3 — `debt_abandon`：逾期債的高摩擦出口**
- 目標：TTL 逾期不自動清，改由人工留痕放棄。　檔案：`scripts/debt_clear.sh`（`--abandon`）
- 改法：欄位依 registry；僅 `EXPIRED_OPEN`（TTL 依 `constants.ttl_days`）可用。
- **驗證（可證偽）**：`pytest tests/governance/test_debt_ttl.py -q` 全綠；未逾期的 OPEN → rc≠0；缺 `approver`/`remediation_owner` → rc≠0；逾期且欄位齊 → rc=0 轉 ABANDONED
- **邊界（≥2）**：①未逾期 → 拒 ②欄位缺 → 拒 ③harness 可用短 TTL 但不得成 production override ④ABANDONED 不得再 clear（**且不可逆**，見 §N）
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：**嚴禁**任何形式的自動 clear

**Task 4.4 — mutation 探針 + 287 既有測試回歸**
- 目標：證明閘門非假綠。　檔案：新增 `tests/governance/test_debt_*.py` + `tests/governance/mutation_red/`
- 改法：實作 §V 全部 mutation，每類一常駐探針（沿用 `scripts/mutation_probe_check.sh` 規則 1）；依 §V 矩陣處理既有測試。
- **驗證（可證偽）**：每類 mutation 改壞 → 對應具名測試轉紅；復原 → 轉綠；`pytest tests/governance -q` 全綠（基線 287 + 新增）
- **邊界（≥2）**：①探針自身失效 → 由 `mutation_probe_check.sh` 抓 ②既有測試轉紅 → 依 §V 矩陣逐檔判「真回歸」vs「fixture 契約更新」，**禁 skip/waiver**
- **存活至**：永久保留　**覆蓋風險**：無
- 不可做：不得為求測試通過而放寬既有斷言

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：本 SPEC 的測試明確宣稱「驗證閘門正確性」→ 依 `docs/TEST_DESIGN_CHARTER.md` 必附可證偽 mutation。**共 40 類**：

| ID | 變異（改壞哪裡） | 必轉紅的測試 |
|---|---|---|
| M1 | 債檢查函式永遠 return 0 | `test_debt_open_blocks_new_round` |
| M2 | `committee_run`/`cx_run` 不寫 per-family 事件 | `test_round_emits_n_family_dispatches` |
| M3 | 銷帳不校驗 `round_id` | `test_reject_foreign_round_clear` |
| M4 | 銷帳允許 roster ⊂ `effective_participants` | `test_roster_must_cover_effective_participants` |
| M5 | `waived:*` 被誤當 clear | `test_waive_does_not_clear_debt` |
| M6 | `ROUND_ID` 只驗非空、不驗 `round_open` 存在 | `test_cx_run_rejects_forged_round_id` |
| M7 | 新 env override 未綁 `GOVERNANCE_TEST_HARNESS` | 沿用既有反 bypass 測試 |
| M8 | 只掛 `gate_check` hook 不掛 `gate.sh` 本體 | `test_gate_sh_enforces_debt_without_hook` |
| M9 | N=1 被略過開債 | `test_single_family_still_opens_debt` |
| M10 | `impl`/`stamp` brief 引用範本仍跳過 P1-1 | `test_impl_kind_cannot_skip_template_gate` |
| M11 | 刪除 `cx_run` 顯式 family 傳遞 | `test_explicit_family_grok` |
| M12 | `cx_run` 未驗 `brief_sha256_norm`（換 brief 掛屍 round） | `test_cx_run_rejects_brief_swap` |
| M13 | fresh token 在開債後仍放行 | `test_stale_token_blocked_after_new_debt` |
| M14 | `supersede` 允許放寬向 | `test_supersede_tighten_only` |
| M15 | `effective_participants` ≥2 走「非 `attempts_exhausted`」的簡化出口 | `test_multi_family_cannot_use_non_exhausted_clear` |
| M16 | retry 條件非原子（併發都通過 attempt 上限） | `test_concurrent_retry_respects_attempt_cap` |
| M17 | `format_failed` 被誤判為 `success`（不准重派）→ 死鎖 | `test_format_failed_allows_redispatch` |
| M18 | `debt_epoch` 未排除自身 round 的 `round_open` | `test_own_round_open_does_not_stale_token` |
| M19 | amendment 加家族後仍讀 `round_open.participants` | `test_effective_roster_after_amendment` |
| M20 | 白名單事件的 legacy（無 sequence）被當 gap | `test_legacy_events_excluded_from_gap_scan` |
| M21 | OPEN 債時實作 dispatch 未被擋 | `test_open_debt_blocks_impl_dispatch` |
| M22 | `result_state` 判定未綁該 round 的 `lock_mode` | `test_result_state_mode_bound_to_round` |
| M23 | Task 3.1 full clear 讀 `round_open.participants` 而非 effective | `test_full_clear_requires_effective_roster` |
| M24 | `format_failure` 對 ≥2 被禁（終局出口消失） | `test_format_failure_allowed_for_multi_family` |
| M25 | cutoff 後缺 `sequence` 的直接 append 被當 legacy 忽略 | `test_post_cutoff_missing_sequence_fail_closed` |
| M26 | `debt_epoch` 未排除同 round `amendment` | `test_own_amendment_does_not_stale_token` |
| M27 | degrade 繞過 attempt 上限／對 `success` 家族生效／逾期未回 PARTIAL | `test_family_degrade_lifecycle` |
| M28 | Task 3.2 複驗做第二次掃描（而非讀 audit 既有 `result_state`） | `test_format_failure_reads_stored_state` |
| M29 | provenance gate 未限定 registry 白名單（對舊事件也 fail-closed） | `test_provenance_gate_scoped_to_debt_events` |
| M30 | `producer` 由呼叫端指定而非管線強制 | `test_producer_forced_by_pipeline` |
| M31 | 全家族 degrade 後無終局出口（要求 `completeness_rc==0`） | `test_all_degraded_terminal_clear` |
| M32 | degrade 可無限續期（`--renew-once` 未限一次） | `test_degrade_renew_once_only` |
| M34 | `renew_once` 配額寫成「每 round 全域一次」→ ≥2 家族卡死時只能救 1 家 | `test_renew_once_quota_is_per_family` |
| M35 | 未知 P16 命名空間事件只告警不拒認（fail-open）→ 重演漏列白名單 | `test_unknown_p16_event_fail_closed` |
| M36 | 守衛硬編掃描漏消費端（`.py`／子目錄／字串拼接） | `test_hardcode_scan_covers_all_consumers` |
| M37 | 豁免清單可被濫用（塞真事件名／憑空 allow token／殭屍豁免） | `test_exemption_lists_self_guarded` |
| M38 | 任一 registry 清單清空後檢查 vacuously pass | `test_empty_list_fails_closed` |
| M39 | `clear_kind` 映射值交換後集合仍相等而放行 | `test_clear_kind_map_semantic` |
| M40 | audit 含 post-cutoff 未知 P16 事件而守衛不知 | `test_unknown_audit_event_fail_closed` |
| M33 | amendment delta 落在 `added_families` 外（quorum 或 expected_outputs） | `test_amendment_delta_invariants` |

- **registry 一致性**（Task 0.1）：新增 `closes_debt` 事件但未同步 `enums.clear_kind` → `audit_events_check.sh` rc≠0。**此檢查取代人工同步，是本版消除「改一處漏一處」的機制。**
- **測試層級**：單元（ledger／registry／schema）／整合（真跑一輪派工看 audit）／邊界／併發／mutation。可獨立 `pytest tests/governance/ -q`。
- **防假綠**：diff 既有 287 測試斷言，不得放寬/刪除換綠。
- **⛔ 禁止的驗收寫法**：不得用不可測百分比；改為**列舉具體反例逐條跑 `pytest`**（各 Task 可證偽欄已列）。
- **⛔ 禁止的分類器**：不得用「產出含 canonical ID / `Verdict:`」當**分類器**（三家一致：誤殺 + 可繞）。

### 287 既有測試逐檔回歸矩陣（禁 skip/waiver）

| 測試檔 | Phase 4 後預期 | 性質 | 處置 |
|---|---|---|---|
| `test_family_registry.py` | **紅** | **既有假綠**（走 gate 直呼非 `cx_run` 正式路徑） | Task 1.2 重寫走 cx_run + fixture 故意讓 `review_role` 不含家族名、gate 級 `--output` 為空 |
| `test_brief_conformance.py` | **紅** | **真回歸（契約變嚴）** | ①`cx_run` 呼叫注入合法 `ROUND_ID` ②`test_impl_kind_not_required_to_have_finding_clauses` **保持綠**（真 impl 不引用範本，Task 1.5 行為不變）③**另新增**含範本的 impl brief negative test；禁 xfail |
| `test_dispatch_wrapper.py` | 綠 | 隔離空 audit | 確保「空 audit ＝無債放行」 |
| `test_gate_impl_dispatch.py` | 綠 | V-C 路徑 | 2 處 `pop GOVERNANCE_TEST_HARNESS` 須確認不觸發 fail-closed |
| `test_low_risk_impl_requires_reconcile.py` | 綠 | 同上（2 處 pop） | V-C 斷言全保留 |
| `test_reconcile_target_bound_to_synth.py` | 綠 | pop harness（1 處） | 空 tmp audit 須為「無債」非「崩潰」 |
| `test_waived_adversarial_still_stamps.py` | 綠 | 1 處 pop | 無預置 open 債則不擋 |
| `test_reconcile_completeness_enforced.py` | 綠 | 多數已設 harness | 保留 classic/double-waiver 拒絕斷言 |
| `test_stamp_no_task_rejected.py` | 綠 | V-A provenance | no-debt fixture |
| `test_completeness_lock.py` / `_semantic.py` | 綠 | 不經債閘（4 處 pop） | lock schema **不加** `round_id` |
| `test_completeness_{degrade,oracles,selfcheck,id}.py`、`mutation_red/*` | 綠 | 不經債閘 | 維持 |
| `test_verify_gate{,_b3,_b4,_b5,_o3,_o3ext,_r7ext,_redteam,_overstrict}.py` | 綠 | 隔離 audit／手造舊事件 | 標 legacy-read fixture（registry `non_debt_legacy_events`）；保留 provenance 斷言 |
| `test_gate_deny_audit.py`、`test_sync_check.py`、`test_precommit_autofix.py` | 綠 | 契約 | 確認新 hook 不改既有語意 |

- **邊界目錄**：空 audit／只有非 JSON 舊格式／並發 3 家同時寫（sequence 唯一性）／`round_open` 重複／`round_open` 寫入失敗／pending 逾時／檔案不存在／只含 advisory_only／部分家族失敗／cutoff 邊界／TTL 邊界／attempt 上限邊界／併發 retry／token epoch 邊界／單家 vs 多家清帳路徑／degrade 逾期 + `failed` 家族／registry 缺檔或壞檔。

## §R 回退
- **Phase 4（擋門）**：`revert` 該 commit 或註解 `_check_open_debt` 單一呼叫點即可移除擋門（`gate.sh` token 寫入為單一區塊）。**Task 4.2 須與 Phase 4 同 commit 一併回退。**
- **⚠️ 明確不回退**：Phase 1 的 `ROUND_ID` 必填契約、Task 1.5 的 brief 範本覆寫行為、**已寫入 audit 的事件**（append-only）。回退後系統**留痕但不擋**（向後相容）。
- 每 Phase 獨立 commit，可單獨 revert。任一 Phase 導致既有測試轉紅且非 §V 矩陣所列 → 不 merge。
- **audit 事件 schema 不可回退** → 故 Phase 0/1 的 registry 與 schema 必須先過 adversarial 審才實作；此為本 SPEC 走完整管線的主要理由。

## §N N/A 登記
- **§G Golden / Baseline：N/A** — RISK-HIT 為 `b,c`，未命中 (a)/(d)。僅動 `scripts/` 治理層與 `tests/governance/`，不碰 `momentum/`、`api/`、`data_cache/`，無數值輸出可對照。**替代保證**：§V 的 40 類 mutation + registry 一致性守衛 + 287 逐檔矩陣 + 各 Task 具體反例。
- **誤開 round / 誤 `abandon` 的未逾期撤銷路徑：N/A（接受為成本）** — 誤開者只能正常清帳或等 TTL；誤 `abandon` **不可逆**。理由：任何「立即撤銷」機制都是新的清債旁路（四家一致警示），其風險高於等待成本。
