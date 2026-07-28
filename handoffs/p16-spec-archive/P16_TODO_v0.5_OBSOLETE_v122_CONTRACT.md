# P1-6 委員未結案債狀態機 — TODO

> **版本 v0.5 — DRAFT(R1 29 + R2 23 + Q-11 R3 12 + R4 19 = 83 findings 全收口;對應 SPEC v1.2.2;**未經三家重戳前不得派實作**)**
> **R1 reconcile**：`handoffs/reconcile/p16-todoadv-r1/synth.md`（29 findings → 19 群集，`completeness_check --lock` rc=0）
> **來源 SPEC**：`docs/P16_COMMITTEE_DEBT_SPEC.md` **v1.2.2**（2026-07-27；v1.2.1 修 Q-8／Q-9／Q-10／Q-11 四項，v1.2.2 再收 R4 的 19 項）。
> **⚠️ v1.2 的三家 RECONCILE-STAMP 不延續到 v1.2.1——v1.2.1 須重審 + 重戳，未重戳前不得派實作。**
> 歷史存查：v1.2 的定版依據＝已 APPROVED 的 reconcile `handoffs/reconcile/p16-v11rev-r12/synth.md`，**該 synth 的 body hash＝`31fc2c1e…6875`**。**注意該 hash 是 reconcile synth 的 body hash，不是 SPEC 檔案本身的 sha256**（R2 codex 指出此處易誤讀）。
> **事件/欄位/枚舉/常數單一真相源**：`scripts/audit_events.json`。**本文件與 SPEC 一樣不重列 registry 內容**——一律 pointer。
> **家族單一真相源**：`scripts/governance_families.json`（經 `scripts/governance_families.sh` 讀取）。
> **執行端合約**：`AGENTS.md`。冷啟動執行端讀本檔 + SPEC §A/§C 即可逐 Task 開寫。

---

## §S SPEC 覆蓋追溯（防漏核心；階段 1 交付物）

### S-1 Task 覆蓋（SPEC 16 個 → TODO 16 個，合計數必須相等）

| SPEC Task | SPEC 原文節錄（≤30 字） | TODO 位置 | 批次 |
|---|---|---|---|
| 0.1 | `audit_events.json` + 一致性守衛 | Phase 0 / Task 0.1 | B1 |
| 1.1 | `committee_run.sh` mint round 並寫 `committee_round_open` | Phase 1 / Task 1.1 | B2 |
| 1.2 | `cx_run.sh` emit per-family 事件 + round membership 與 retry 契約 | Phase 1 / Task 1.2 | B2 |
| 1.3 | `committee_round_amendment`：補派契約 + effective roster 定義 | Phase 1 / Task 1.3 | B2 |
| 1.4 | `audit_append.sh`：唯一寫入點 + 唯一性/序號/provenance | Phase 1 / Task 1.4 | B2 |
| 1.5 | 封住 `impl`/`stamp` brief 跳過 P1-1 範本閘 | Phase 1 / Task 1.5 | B3 |
| 1.6 | 更新派工規範文件 | Phase 1 / Task 1.6 | B3 |
| 2.1 | `debt_ledger.sh`：只讀 audit 算未結案債 | Phase 2 / Task 2.1 | B4 |
| 3.1 | 完整清帳：completeness PASS 綁 round + effective roster | Phase 3 / Task 3.1 | B5 |
| 3.2 | 清帳嚴格度 + 終局出口 | Phase 3 / Task 3.2 | B5 |
| 3.3 | `committee_debt_supersede`：可稽核的更正路徑 | Phase 3 / Task 3.3 | B5 |
| 3.4 | `committee_family_degrade`：單家族退出清帳要求 | Phase 3 / Task 3.4 | B5 |
| 4.1 | `gate.sh` 債務閘 | Phase 4 / Task 4.1 | B6 |
| 4.2 | token ↔ round handoff 與 `debt_epoch` | Phase 4 / Task 4.2 | B6 |
| 4.3 | `debt_abandon`：逾期債的高摩擦出口 | Phase 4 / Task 4.3 | B6 |
| 4.4 | mutation 探針 + 287 既有測試回歸 | Phase 4 / Task 4.4 | B6′ |

**合計：SPEC 16 → TODO 16，無合併、無遺漏。**

### S-2 §V mutation 覆蓋（SPEC 40 類 + R1 新增 M41 = 41 類 → 逐類指派批次；B6′ 驗收全表）

| M-ID | 落在批次 | M-ID | 落在批次 | M-ID | 落在批次 | M-ID | 落在批次 |
|---|---|---|---|---|---|---|---|
| M1 | B6 | M11 | B2 | M21 | B6 | M31 | B5 |
| M2 | B2 | M12 | B2 | M22 | B2 | M32 | B5 |
| M3 | B5 | M13 | B6 | M23 | B5 | M33 | B2 |
| M4 | B5 | M14 | B5 | M24 | B5 | M34 | B5 |
| M5 | B5 | M15 | B5 | M25 | B2 | M35 | B1 |
| M6 | B2 | M16 | B2 | M26 | B6 | M36 | B1 |
| M7 | B1–B6′ 各批 | M17 | B2 | M27 | B5 | M37 | B1 |
| M8 | B6 | M18 | B6 | M28 | B5 | M38 | B1 |
| M9 | B2 | M19 | B4 | M29 | B2 | M39 | B1 |
| M10 | B3 | M20 | **B4** | M30 | B2 | M40 | B1 |

**M41（R1 新增，隨 §Q-7 裁決納入）**：`gate_check.sh` 無 jq 時 fail-open → `test_gate_check_no_jq_fail_closed`；落在 **B6′**。合計 **41 類**。
> R1 更正（C10）：M20（legacy 事件不被當 gap）**由 B2 改列 B4** —— 該類必須有 `debt_ledger.sh` 才證得出，B2 結構上無法閉合（composer P1-01／grok P1-01 一致）。

**上表 40 類逐類有主，加 M41 共 41 類（B6′ 驗收以 41 為分母）。** M7（新增 env override 未綁 `GOVERNANCE_TEST_HARNESS`）為橫切項：**每批只要新增 env override 就必須當批補一條探針**，B6′ 統一清點。

### S-3 §A 誠實邊界 14 條（**不得宣稱機器覆蓋**；TODO 對應處置）

| # | 邊界 | TODO 處置 |
|---|---|---|
| 1 | 純對話綜合永遠攔不到 | §0 明列；不寫任何宣稱覆蓋的驗證 |
| 2 | `cx_run` 直呼（V-D） | Task 1.2 只做 membership 限制其危害，驗證不宣稱阻擋 |
| 3 | 拆成 N 次單家：各自開債但不強制合併 | Task 1.1 邊界①；不寫合併強制 |
| 4 | `gate_check.sh` 無 jq → fail-open | **已閉合**：§Q-7 裁定納入 **Task 4.2 改法⑧ + M41 探針**；SPEC v1.2.1 §A 第 4 條**已同步改標已閉合**，SPEC §V 亦已補 M41 列 |
| 5 | `gate.sh artifact`/`register-output` 不在債務閘範圍 | Task 4.1 改法②只掛 dispatch 分支 |
| 6 | `clear_format_failure` 是付費出口 | Task 3.2 驗證只驗前置條件，不驗 brief 品質 |
| 7 | `clear_all_degraded` 同為高摩擦出口 | Task 3.2 同上 |
| 8 | `approver`/`remediation_owner` 身份不可驗證 | Task 3.2/3.4/4.3 只驗非空 |
| 9 | FS 信任模型（有寫權可偽造帶號事件） | Task 1.4 只堵「無 sequence 隱形」 |
| 10 | 豁免清單殘餘旁路（先寫硬編再補豁免） | Task 0.1 守衛只擋殭屍/憑空/真事件名 |
| 11 | 片段掃描是啟發式（擋不住 base64/多層間接） | Task 0.1 C9b 只擋字面前綴拼接 |
| 12 | family SoT 整份被替換屬第 9 條 | Task 0.1 C6 只驗結構自洽 |
| 13 | Phase 0 只證 registry 自洽 | Task 4.4 承接「registry 欄位 ↔ 消費端」矩陣 |
| **14** | **（SPEC v1.2.1 新增）Task 1.5 反向缺口未閉合**：brief 標 `impl` 且**不引用**任何範本者仍不被追加 P1-1 義務（＝R5 C2 主洞） | Task 1.5 ⚠️ 誠實邊界段明列；**禁宣稱 Q-11 把它關了**；靠一扇門開債 + `format_failed` 摩擦兜底 |

> **共 14 條**（SPEC v1.2.1 同步）。§V 全部 mutation **不宣稱覆蓋**這 14 條。

### S-4 §A 憲法級裁決 7 條（不得擅改）

| # | 裁決 | 本 TODO 落點 |
|---|---|---|
| 1 | D2：委員派工一律開債，不看下游、不看採不採用 | Task 1.1 改法①、Task 1.1 邊界① |
| 2 | 不得用任何主委可自報的信號當分類器 | §0 紅線 R-4；Task 1.5 不可做 |
| 3 | 一扇門：全走 `committee_run.sh`，無分類/豁免/執行通道 | Task 1.1、Task 1.6 |
| 4 | 債未清 → 擋所有新派工，含實作 | Task 4.1 改法③ + 具名 oracle |
| 5 | 軟 TTL 7 日，`EXPIRED_OPEN` 仍擋，嚴禁自動 clear | Task 4.3；Task 2.1 不可做 |
| 6 | 走完整大任務管線，不跳步 | 本 TODO 本身 + §B 各批 review quorum |
| 7 | 凡有可用腳本一律套用（強制力尚未機械化＝人工紀律） | §0 紅線 R-6；§Q-3 標明不得當機檢來源 |

### S-5 §V 287 既有測試回歸矩陣（SPEC 13 列 → 逐列指派）

| 測試檔 | SPEC 預期 | 處置批次 |
|---|---|---|
| `test_family_registry.py` | 紅（既有假綠） | B2（Task 1.2 重寫走 cx_run） |
| `test_brief_conformance.py` | 紅（真回歸，契約變嚴） | B3（Task 1.5） |
| `test_dispatch_wrapper.py` | 綠（隔離空 audit） | B6（Task 4.1 邊界①） |
| `test_gate_impl_dispatch.py` | 綠（V-C 路徑，2 處 pop harness） | B6 |
| `test_low_risk_impl_requires_reconcile.py` | 綠（2 處 pop） | B6 |
| `test_reconcile_target_bound_to_synth.py` | 綠（1 處 pop） | B6 |
| `test_waived_adversarial_still_stamps.py` | 綠（1 處 pop） | B6 |
| `test_reconcile_completeness_enforced.py` | 綠 | B6 |
| `test_stamp_no_task_rejected.py` | 綠（V-A provenance） | B6 |
| `test_completeness_lock.py` / `_semantic.py` | 綠（lock schema 不加 `round_id`） | B5 |
| `test_completeness_{degrade,oracles,selfcheck,id}.py`、`mutation_red/*` | 綠（不經債閘） | B6′ 清點 |
| `test_verify_gate{,_b3,_b4,_b5,_o3,_o3ext,_r7ext,_redteam,_overstrict}.py` | 綠（legacy-read fixture） | B2（Task 1.4 provenance 白名單範圍） |
| `test_gate_deny_audit.py`、`test_sync_check.py`、`test_precommit_autofix.py` | 綠（契約） | B6′ |

### S-6 環境變數 / flag 索引（新增者一律綁 `GOVERNANCE_TEST_HARNESS=1`）

| 名稱 | 新增/既有 | 綁 harness | 出處 |
|---|---|---|---|
| `AUDIT_EVENTS_REGISTRY_OVERRIDE` | 新增 | 是 | SPEC Task 0.1 邊界⑤ |
| `ROUND_ID` | 新增（env，非 override） | 否（是契約值，非旁路） | SPEC Task 1.2 改法③ |
| `CX_RUN_BIN_OVERRIDE` | 新增（提案，見 §Q-2） | 是 | 本 TODO Task 1.2 latency probe |
| `DEBT_LEDGER_OVERRIDE` | 新增 | 是 | 本 TODO Task 4.1 改法⑤ |
| `DEBT_AUDIT_OVERRIDE` | **新增（R1／C1）** | **是** | 債務閘 audit 來源的**唯一**測試隔離途徑（取代原本靠 `GATE_DIR_OVERRIDE`） |
| `AUDIT_APPEND_EVENT_ID_OVERRIDE` | **新增（R1／C13）** | **是** | Task 1.4 的重複 `event_id` 注入 seam（R2 補列；grok R2-P2-02 指出漏表會讓 M7 清點漏網） |
| `GATE_DIR_OVERRIDE` | 既有（**未綁 harness**） | 否（現況） | 既有；**R1 裁定：債務閘不得讀它**，見 Task 4.1 改法⑤與 §Q-6 |

> **R1 更正（C19／grok P2-02）**：`scripts/finding_validator.sh` 與 `scripts/debt_roster.sh` **SPEC 未點名檔名**，是 SPEC「單一 finding validator」（Task 1.2 改法②）與「effective roster 全鏈共用」（Task 1.3）的必要抽出，**非過度工程**（三家一致認定）。
| `GOVERNANCE_TEST_HARNESS` | 既有 | 本體 | 既有反 bypass 紅線 |
| `COMPLETENESS_CHECK_OVERRIDE` | 既有 | 是 | `gate.sh:47-50` |
| `RECONCILE_STAMPS_CHECK_OVERRIDE` | 既有 | 是 | `gate.sh:43-46` |

### S-7 SPEC FACT-RECEIPT 11 條（原 10 條 + v1.2.1 拆出的 #10b）（實作前必須仍成立；B1 開工第一件事重跑）

| # | 命令 | 期望 |
|---|---|---|
| 1 | `python -m pytest tests/governance -q` | **`301 passed`**（2026-07-27 實跑 `301 passed in 76.28s`，rc=0）。**基線變動說明**：SPEC 記的 287 是 v1.2 當時值；本 session 新增 `tests/governance/test_doc_consistency.py`（14 測試）後為 **301 = 287 + 14**。SPEC §V「287 逐檔矩陣」的 **287 指的是 P1-6 開工前的既有測試數**，該矩陣範圍不變 |
| 2 | `grep -n "audit\|AUDIT" scripts/cx_run.sh` | 0 命中（`cx_run.sh` 現況 85 行無 audit） |
| 3 | `rg -c 'committee_family_dispatch' .claude/gate/audit.log` | 0 |
| 4 | audit 全史 `family=grok` | 0 筆 |
| 5 | 零 canonical ID 來源跑 `reconcile_build.sh` | `COMPLETENESS FAIL: …vacuous…`、rc=1 |
| 6 | `completeness_check.sh` 同 sources：discovery lock vs review argv | rc=0 vs rc=1 |
| 7 | post-cutoff audit 無 `sequence` | 181 筆，`committee_round_open`=0 |
| 8 | `nl -ba scripts/gate_check.sh \| sed -n '67,76p'` | fresh token 直接 `exit 0` |
| 9 | `rg -n 'gate\|token\|GATE' scripts/reconcile_build.sh` | 0 命中（清帳不經 dispatch 閘） |
| 10 | `grep -rln GATE_DIR_OVERRIDE tests/governance` | 14 檔（三家與 Claude 實跑一致） |
| 10b | `grep -rn "pop.*GOVERNANCE_TEST_HARNESS" tests/governance` | **6 檔 10 處**（逐檔：lock 3／semantic 1／gate_impl 2／low_risk 2／target 1／waived 1）。**SPEC v1.2.1 已同步更正為此值**（v1.2 原記「6 檔 9 處」已作廢）。歷史誤報存查：codex R1 報「7 檔」檔數錯、composer R1 報「9 處」處數錯——**兩家各錯一半，Claude 2026-07-27 機械清點為準**（§Q-10） |

---

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

### R-1 解耦
- 只動 `scripts/` 治理層、`tests/governance/`、`docs/COMMITTEE_DISPATCH_GUIDE.md`。**不得** touch `momentum/`、`api/`、`frontend/`、`data_cache/`。7 條解耦規則本任務不受影響（不跨 `momentum`↔`api` 邊界）。
- bash 3.2 相容（macOS 預設）：**禁 `declare -A`**（`gate.sh:3` 已立此規矩）。

### R-2 單一真相源（違反即 BLOCKING）
- 事件名／欄位／枚舉／常數 → 讀 `scripts/audit_events.json`。**任何腳本、測試、文件皆不得硬編**；legacy 例外須進 registry `hardcode_scan_exemptions`，且**以掃描結果建清單，禁憑記憶枚舉**（SPEC Task 0.1：憑印象列 3 檔、機械掃描實得 7 檔）。
- 家族名 → 讀 `scripts/governance_families.json`（用 `. scripts/governance_families.sh` 後 `families_get families ' '`）。

### R-3 反 bypass 紅線
- 任何**新增** env override 一律 `[ "${GOVERNANCE_TEST_HARNESS:-}" = "1" ]` 才認，否則 fail-closed 並印明確訊息（照抄 `gate.sh:43-50` 的形狀）。
- 每新增一個 override，**當批**補一條 mutation 探針證明「拿掉 harness 綁定會轉紅」（M7）。

### R-4 分類器紀律（憲法級裁決 2，**v1.2.1 拆為 2a／2b**）
- **R-4a 債務／路由層（全禁）**：**不得**用**任何主委可自報訊號**決定 **①是否開債 ②是否免債 ③走哪個入口／通道 ④清帳嚴格度是否降級**。分類固定在 wrapper——走哪支腳本就是哪一類。
  **SPEC v1.2.1 裁決 2a 明列的五種**：`task_id` 命名／`round_kind` 宣告／檔案範圍宣告／brief 是否引用範本／家族數。
  **本 TODO 另列的等價訊號**（同屬「主委可自報」，不是 SPEC 之外的新增禁令）：「產出含 canonical ID」「產出含 `Verdict:`」——出處＝SPEC §V「⛔ 禁止的分類器」節，三家一致。
- **R-4b 檢查契約層（允許單向加嚴）**：brief 內容**得**用於**追加**檢查義務，但須同時滿足三條：**單向加嚴**（只能增加義務）／**未命中不減檢**（未命中的檢查集合不得低於引入前基準）／**未命中不賦免債**（禁止把「未命中」解釋成「真 impl／可免債／可走簡化清帳出口」）。
- **⚠️「方向取嚴」單獨不構成豁免**——合憲性一律由上列三條**可操作條件**判定，禁以「反正是變嚴」帶過（Q-11 三家一致；codex 形式論成立）。
- 家族數**只**決定清帳嚴格度（Task 3.2），不決定開不開債。
> **v0.4 更正**：v0.3 的 R-4 寫成「不得決定要不要開債／**要不要檢查**」，比 SPEC 更寬，會直接自撞 Task 1.5（grok R3-P1-02、codex R3-P1-04 均指出）。已依 SPEC v1.2.1 的 2a／2b 重寫。

### R-5 fail-closed 預設
- registry 缺檔／JSON 壞／`flock` 逾時／ledger 腳本缺失或崩潰 → **一律拒**，不得 fallback、不得只告警。
- **告警＝fail-open**（R10 事故：`all_degraded` 漏列白名單只告警，等於沒擋）。

### R-6 凡有可用腳本一律套用（憲法級裁決 7；目前＝人工紀律）
- 收集 reconcile → `scripts/reconcile_build.sh`；驗 0 掉項 → `scripts/completeness_check.sh --lock`；戳記 → `scripts/reconcile_stamps_check.sh`；派委員 → `scripts/committee_run.sh` / `scripts/cx_run.sh`；brief 骨架 → `scripts/new_brief.sh`；探針機檢 → `scripts/mutation_probe_check.sh`；範本機檢 → `scripts/template_check.sh`。
- **不得**在本 epic 任一 Task 重寫上述工具的等效邏輯（SPEC §C「工具優先」，雙家 code review 逐項確認）。
- ⚠️ `scripts/governance_tools.json` 的 `mandatory` 欄位**未經委員裁決**（SPEC §A 裁決 7 自承），本 TODO 只引用其 `cmd` 欄當查詢用，**不得**當機檢來源（見 §Q-3）。

### R-7 防假綠
- **不得**放寬／刪除既有 287 個測試的斷言換綠。既有測試轉紅 → 依 §S-5 矩陣逐檔判「真回歸」vs「fixture 契約更新」，**禁 skip／xfail／waiver**。
- 每個宣稱「驗證閘門正確性」的測試檔須有 `def test_mutation_*` 常駐探針（`scripts/mutation_probe_check.sh` 規則 1），且探針真跑真紅真綠。

### R-8 Logging / Error 分類
- 治理腳本一律 `echo ... >&2` 輸出錯誤 + 非零 rc；**不得**吞 rc。
- rc **一律直接取**，禁 `cmd | tail; echo rc=$?`（讀到的是 tail 的 rc；本 epic 已犯 2 次）。

### R-9 誠實邊界不得被驗證宣稱覆蓋
- §S-3 十四條，**任一 Task 的「驗證」欄不得寫成宣稱擋住它們**。寫了即 BLOCKING。

---

## §B 批次執行策略（依賴拓撲 → 7 批；每批＝一次派工 prompt）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 | commit 邊界 |
|---|---|---|---|---|---|
| B1 | 0.1 | 無 | 單一 registry + 單一守衛，其餘全部依賴它 | 中 | 獨立 commit |
| B2 | **1.4 → 1.3 → 1.1 → 1.2** | B1 | 四者共用同一 audit 寫入契約與 effective roster 定義，拆開會來回改同幾行 | 大 | 獨立 commit |
| B3 | 1.5、1.6 | B2 | brief 閘與文件，與留痕核心無共用程式碼，可獨立審 | 小 | 獨立 commit |
| B4 | 2.1 | B2 | 帳本純唯讀，須先有真事件才測得出 | 中 | 獨立 commit |
| B5 | 3.1、3.2、3.3、3.4 | B4 | 四者同一支 `debt_clear.sh` 的四個子命令，共用前置驗證函式 | 大 | 獨立 commit |
| **B6′** | 4.1、4.2、4.3、**4.4** | B5 | SPEC §R 硬要求 Task 4.2 與 Phase 4 同 commit 一併回退；且 4.4 會回頭改前三者的測試，拆成兩個 review-gated 批會讓「前批 quorum 通過」的驗收邊界失效 | 大 | Phase 4 單一 commit |

> **R1 更正（C3／composer P0-01）**：B2 次序由 `1.4→1.1→1.2→1.3` 改為 **`1.4→1.3→1.1→1.2`**。原因：Task 1.2 的成員檢查要 source `debt_roster.sh`，而該檔是 Task 1.3 的產出；照原次序執行端只能 inline 第二套 roster 算法（違 §0 R-2「禁第二套」）或停擺。1.3 只出 roster 函式庫＋amendment 契約，不依賴任何已發事件，故可前移。
> **R1 更正（C17／codex P1-10）**：原「B2+B3 同 commit、B6+B7 同 commit」與「每批完成後 2 家非實作者 review 才派下一批」的驗收邊界不一致（B7 會修改 B6 已通過 review 的測試）。改為**每批獨立 commit**；B6/B7 合併為單一批 **B6′**。

### 批次間 Gate（每批完成才可派下一批）

| 完成批 | Gate 命令（rc 直接取，禁經 pipe） | 通過條件 |
|---|---|---|
| B1 | `bash scripts/audit_events_check.sh`；`python -m pytest tests/governance/test_audit_events_registry.py -q` | 兩者 rc=0；18 類攻擊向量逐條轉紅 |
| B2 | `python -m pytest tests/governance/test_audit_append.py tests/governance/test_debt_emit.py tests/governance/test_debt_retry.py -q`；`bash scripts/p16_latency_probe.sh --verify <receipt>` | 兩者 rc=0（**不是「receipt 檔存在」——手工放置的檔會被 `--verify` 擋下**）。**不含任何 `debt_ledger.sh` 斷言**（C10） |
| B3 | `python -m pytest tests/governance/test_brief_conformance.py -q` | rc=0 且 `test_impl_kind_not_required_to_have_finding_clauses` 仍綠 |
| B4 | `python -m pytest tests/governance/test_debt_ledger.py -q` | rc=0；含 M19、**M20**（legacy 混合不被當 gap） |
| B5 | `python -m pytest tests/governance/test_debt_clear.py tests/governance/test_debt_supersede.py tests/governance/test_debt_degrade.py -q` | rc=0 |
| B6′ | `python -m pytest tests/governance -q`；`bash scripts/mutation_probe_check.sh tests/governance/test_debt_*.py tests/governance/test_audit_*.py`；`bash scripts/gov_check.sh` | 第一項 passed ≥ 287 且 failed == 0；後兩項 rc=0；41 類 mutation 逐條 receipt |

### 每批派工 prompt 骨架（照抄，填入批號）

```
brief-kind: impl
前置狀態：B<N-1> 已 commit，pytest tests/governance -q rc=0。
本批 Task：<S-1 表對應列>
必讀：docs/P16_COMMITTEE_DEBT_TODO.md §0 + 本批 Task 全文；docs/P16_COMMITTEE_DEBT_SPEC.md §A/§C；AGENTS.md
禁止：改 registry 內容以外的硬編事件名；放寬既有測試斷言；新增未綁 GOVERNANCE_TEST_HARNESS 的 env override
驗證命令：<批次間 Gate 表對應列>
兩輪解不了 → 停手回報，交委員會（不得 solo 硬幹）
```

**派工用 `bash scripts/new_brief.sh impl <路徑> "<標題>"` 產骨架，禁手寫**（手寫必被 P1-1 閘擋，本 epic 已被擋兩次）。

### review quorum
每批實作完成 → **2 個非實作者家族** code review（`scripts/review_quorum_check.sh` 機器強制，`gate.sh` 派下一批時驗前批 quorum，不足即拒發 token）。

---

## Phase 0 — 事件真相源（依賴：無）

**完成後系統狀態**：`scripts/audit_events.json` 為唯一事件定義來源；守衛可機械證明 SPEC／腳本／audit 三者與 registry 一致；任何漏同步即 rc≠0。

### Task 0.1 — `scripts/audit_events.json` + 一致性守衛

- **SPEC ref**：Task 0.1　**目標**：所有事件定義只有一份，消滅「新增事件漏同步 N 處」。
- **輸入**：`scripts/audit_events.json`（已建，registry_version=2，v1.2 定版時凍結）、`handoffs/p16-phase0-reference/audit_events_check.sh`（**參考實作，非規格，不得直接複製當交付**）。
- **輸出**：`scripts/audit_events_check.sh`（新增，可執行）、`tests/governance/test_audit_events_registry.py`（新增，含 `test_mutation_*` 探針）。
- **實作要點**（≥3）：
  1. **守衛檢查項清單一律寫在腳本檔頭註解**（C1–C12），**本 TODO 與 SPEC 皆不重列**——寫兩處必漂移（R12 已實際漂移一次）。腳本骨架：
     ```bash
     # audit_events_check.sh
     # 檢查項（canonical，唯一來源）：C1 …  C12 …
     REG="${AUDIT_EVENTS_REGISTRY_OVERRIDE:-scripts/audit_events.json}"
     if [ -n "${AUDIT_EVENTS_REGISTRY_OVERRIDE:-}" ] && [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
       echo "ERROR: AUDIT_EVENTS_REGISTRY_OVERRIDE 僅允許 GOVERNANCE_TEST_HARNESS=1" >&2; exit 1
     fi
     [ -f "${REG}" ] || { echo "ERROR: registry 缺檔（fail-closed）: ${REG}" >&2; exit 1; }
     "${VENV_PY}" -c 'import json,sys; json.load(open(sys.argv[1]))' "${REG}" \
       || { echo "ERROR: registry JSON 壞（fail-closed）" >&2; exit 1; }
     _run_check C1_docs_only_metadata ; _run_check C2_event_object_allowed_keys ; …
     ```
  2. **反 vacuous**：每個「集合比對」型檢查，先驗待比對清單**非空**再比對；清單空 → rc≠0（M38）。偽碼：
     ```
     assert len(registry["family_valued_fields"]) > 0        # 否則 C6 vacuously pass
     assert len(registry["debt_events"]) > 0
     assert set(field for ev in debt_events for field in ev["fields"]
                if any(p in field for p in family_field_name_patterns)) == set(family_valued_fields)
     ```
  3. **語義而非集合相等**（M39）：`clear_kind_event_map` 檢查須逐 kind 判定——`kind ∈ generic_clear_kinds` → 值必須 == `generic_clear_event`；否則值必須以該 kind 結尾。交換 `full` ↔ `all_degraded` 的映射值時集合仍相等，故**禁用集合比對**。
  4. **硬編掃描（C9/C9b）**：掃 `scripts/**/*.sh`、`scripts/**/*.py`、`tests/governance/**/*.py`；以 `fragment_scan_prefixes` 抓片段拼接（含裸賦值 `P=committee_`、`"committee_${kind}"`）；`fragment_scan_allow_tokens` 為誤判豁免。豁免清單本身受 C11 守衛：allow token 必須真的出現在 `scripts/` 內（擋憑空新增），且**任一豁免值不得等於任一真事件名**（M37）。
  5. **audit 實讀（C12）**：讀 registry `audit_log_path`，逐行 `startswith("{")` 解析；post-cutoff 事件名命中 `p16_namespace_prefixes` 但不在 `debt_events` → **rc≠0 拒認**（非告警；M35/M40）。
  6. **SPEC 反向檢查（C10）**：`docs/P16_COMMITTEE_DEBT_SPEC.md` 內出現的 P16 命名空間 token ⊆ `debt_events` ∪ `spec_non_event_tokens`；SPEC 缺檔 → rc≠0。
- **修改檔案**（到函式名）：
  - 新增 `scripts/audit_events_check.sh` — `_run_check()`、`_load_registry()`、`_scan_hardcode()`、`_scan_audit_unknown()`、`_check_clear_kind_map()`
  - 新增 `tests/governance/test_audit_events_registry.py` — 18 個攻擊向量各一 test + `test_mutation_registry_guard_has_teeth`
  - `scripts/audit_events.json` — **事件 schema／結構凍結**（不得新增/刪除 event、欄位、枚舉；要改須回頭改 SPEC）。**例外**：`constants` 內由量測決定的 `pending_deadline_seconds` 依 §Q-4／§Q-8 裁決路徑寫入，非本 Task 動作。
    > **R1 更正（C5／composer P0-03＋grok P1-03）**：v0.1 寫「不改 registry 內容」與 B2 出場 gate「把量測 N 寫回 registry」互斥，執行端必違其一。現改為**結構凍結、常數量測值另有路徑**。
- **既有 caller**：目前 0 處（`grep -rn 'audit_events_check' scripts/ tests/` → 0）。本批後 caller = `scripts/gov_check.sh` + CI `governance.yml`。
- **不可做**：不得在 SPEC/TODO/腳本任何處重複列舉 registry 內容；不得直接複製 `handoffs/p16-phase0-reference/` 的參考實作當交付（未經雙家 code review，且作者＝編排者）；不得把未知事件降級為告警。
- **邊界**（≥2）：
  1. registry 缺檔 → 所有消費端 fail-closed（rc≠0，訊息含檔路徑）
  2. JSON 壞（截斷/非法逗號）→ fail-closed
  3. 消費端 iterate 資料容器遇 `_` 前綴鍵 → 守衛先擋（實建當下即踩過）
  4. post-cutoff 出現於 `p16_namespace_prefixes` 但不在 `debt_events` 的事件 → fail-closed 拒認
  5. `AUDIT_EVENTS_REGISTRY_OVERRIDE` 未帶 `GOVERNANCE_TEST_HARNESS=1` → fail-closed
- **風險緩解**：M35／M36／M37／M38／M39／M40 六類 mutation 全在本批落地。
- **驗證**（可證偽）：`bash scripts/audit_events_check.sh` → rc=0；`python -m pytest tests/governance/test_audit_events_registry.py -q` → rc=0；SPEC §V 列的 **18 類攻擊向量**逐條注入後對應具名測試轉紅、復原後轉綠（registry 面 7 類：空清單 vacuous／event 加白名單外鍵／交換 `clear_kind` 映射值／移除必要欄位／旗標互斥／constants 型別／`family_valued_fields` 漏登或清空；檔案面 6 類：`.py` 消費端硬編／裸賦值拼接 `P=committee_`／`"committee_${kind}"` 拼接／SPEC 缺檔／`p16_namespace_prefixes=[]`／audit 含 post-cutoff 未知 P16 事件；豁免面 2 類：真事件名塞進豁免清單／憑空新增不存在的 allow token）。
- **存活至**：永久保留（Phase 1–4 全部依賴）。
- **覆蓋風險**：無。後續 Phase 只**新增** registry 消費端，不刪改本 Task 產出。

---

## Phase 1 — 留痕（依賴：Phase 0）

**完成後系統狀態**：每一輪委員派工在 audit 留下 `committee_round_open` + 每家 `dispatch`/`result`；所有寫入經單一 allocator，序號連續、可稽核；`impl` brief 無法跳過範本閘。

> **⚠️ 實作次序與 SPEC §P 字面不同（已於 R1 裁決，見 §Q-1）**：SPEC 寫「Phase 1 內部實作順序＝1.1→1.2→1.3→1.4→1.5→1.6」，但 ①Task 1.4 的 `audit_append.sh` 是 1.1/1.2/1.3 的**唯一寫入點**（SPEC Task 1.4 改法⑤：「所有 Phase 1-4 新事件一律經此腳本，禁各自 `echo >>`」）②Task 1.2 的成員檢查必須 source Task 1.3 產出的 `debt_roster.sh`。**本 TODO 的 B2 實作次序＝1.4 → 1.3 → 1.1 → 1.2**（與 §B 表一致）；Task 編號不動。

### Task 1.4 — `audit_append.sh`：唯一寫入點 + 唯一性/序號/provenance

- **SPEC ref**：Task 1.4　**目標**：讓 append-only 帳本成為可稽核 contract。
- **輸入**：`scripts/audit_events.json`（`debt_event_required_fields`、`allowed_origin_scripts`、`non_debt_legacy_events`、`cutoff_ts`）、目標 audit 路徑（呼叫端傳入或 registry `audit_log_path`）。
- **輸出**：`scripts/audit_append.sh`（新增）、`tests/governance/test_audit_append.py`（新增）。
- **實作要點**（≥3）：
  1. **介面**：`bash scripts/audit_append.sh --event <name> --origin-script <script> --audit <path> --field k=v [--field k=v …]`。偽碼：
     ```
     validate: event ∈ registry.debt_events            (否則 rc≠0)
     validate: origin_script ∈ registry.allowed_origin_scripts
     validate: origin_script == registry.debt_events[event].origin_script
     validate: set(required_fields_per_event[event]) ⊆ set(給定 field keys)
     force    : producer = "audit_append.sh"  # 呼叫端若傳 --field producer=X → **忽略並覆寫**，不 rc≠0
     ```
     > **R1 更正（C9／grok P1-02）**：v0.1 同時寫「呼叫端給了 `producer` → rc≠0」與驗證「指定 `producer` → 被覆寫」，執行端無法同時滿足。依 SPEC Task 1.4 驗證原文（「呼叫端試圖指定 `producer` → 被覆寫」）統一為**忽略／覆寫**；M30 斷言改為「落地值恆為 `audit_append.sh`」。
  1b. **`event_id` / `actor` / 複合值編碼契約**（C13／codex P1-09）：
     - `event_id` 預設由腳本 `uuid4()` 產生；**唯一性測試需要可注入的重複值** → 提供 harness-only seam `AUDIT_APPEND_EVENT_ID_OVERRIDE`（**綁 `GOVERNANCE_TEST_HARNESS=1`**，M7 適用），正式路徑一律自產。
     - `actor`：由呼叫端以 `--field actor=<字串>` 提供，缺 → rc≠0（registry `debt_event_required_fields` 含 `actor`）。**內容不可驗證**（§S-3 第 8 條）。
     - 陣列／物件型欄位（`participants`、`expected_outputs`、`degrade_event_ids` 等）：`--field k=@<json>` 形式傳入合法 JSON 字面，腳本原樣嵌入；非法 JSON → rc≠0。純量欄位一律 JSON 字串。
  2. **序號 allocator 綁 `flock`**（讀尾端 → +1 → append 為單一臨界區）：
     ```
     exec 9>"${audit}.lock"
     flock -w ${FLOCK_TIMEOUT} 9 || { echo "ERROR: flock 逾時（fail-closed）" >&2; exit 1; }
     seq = max(existing sequence in audit) or 0
     seq = seq + 1
     event_id = uuid4()
     if event_id 已存在於 audit: exit≠0            # 唯一性
     printf '%s\n' "$(json_line)" >> "${audit}"
     flock -u 9
     ```
     macOS 無 `flock(1)` 時以 `mkdir` 原子鎖 fallback（**仍須 fail-closed 逾時**），實作者擇一並在檔頭註明。
  3. **provenance gate 按事件類過濾**（M29）：只有 registry `debt_events` 白名單事件才受「cutoff 後缺 `sequence` 或 `producer != audit_append.sh` → fail-closed」約束；`non_debt_legacy_events`（`committee_dispatch`/`committee_output`/`gate_deny`）**pre/post 皆不參與 gap 掃描、不計債、不觸發 fail-closed**。現存 181 筆無 `sequence` 的 legacy 必須不被誤殺。
  4. **JSON 行格式**：單行 JSON，鍵序固定（`event`,`schema_version`,`event_id`,`sequence`,`producer`,`origin_script`,`actor`,`ts`,…業務欄位），避免 diff 噪音。
- **修改檔案**（到函式名）：新增 `scripts/audit_append.sh` — `_load_registry()`、`_validate_event()`、`_alloc_sequence()`、`_emit_json_line()`、`_assert_unique_event_id()`；新增 `tests/governance/test_audit_append.py`。
- **既有 caller**：本 Task 落地時 0 個；B2 後續 Task 1.1/1.2、B5 的 `debt_clear.sh` 全部改為呼叫它。**既有 `gate.sh:_append_committee_json_event()` 不改**（寫的是 legacy 事件，不在白名單）。
- **不可做**：不得讓任何 Task 繞過本腳本；不得硬編事件名；不得讓呼叫端指定 `producer`；不得對 legacy 事件做 gap 掃描。
- **邊界**（≥2）：
  1. audit 檔不存在 → **建立**而非崩潰
  2. `flock` 逾時 → fail-closed（rc≠0）
  3. registry 缺檔 → fail-closed
  4. 出現在 audit 但不在 registry 的 P16 命名空間事件 → fail-closed 拒認
- **風險緩解**：M25（post-cutoff 缺 sequence 被當 legacy 忽略）、M29、M30、M20（legacy 被當 gap）。
- **驗證**（可證偽，**B2 批內可獨立閉合，不得引用 B4 才存在的 `debt_ledger.sh`**）：`python -m pytest tests/governance/test_audit_append.py -q` → rc=0；以 `AUDIT_APPEND_EVENT_ID_OVERRIDE` 注入重複 `event_id` → rc≠0；**兩程序併發各寫 100 筆 → sequence 連續無重複無缺口**（斷言 `sorted(seqs) == list(range(1,201))`）；呼叫端傳 `--field producer=fake` → 落地值 == `audit_append.sh`；缺 `actor` → rc≠0；`--field participants=@'[bad json'` → rc≠0；`--field participants=@'["codex"]'` → 落地為 JSON 陣列非字串。
  > **R1 更正（C10／composer P1-01＋grok P1-01）**：v0.1 此欄要求 `debt_ledger.sh --list rc=0` 與「gap → ledger rc≠0」，但 ledger 屬 B4／Task 2.1，B2 結構上跑不了。兩條斷言（含 M20）**移至 Task 2.1 驗證欄**。
- **存活至**：永久保留。
- **覆蓋風險**：無。Phase 2–4 只讀它寫的事件，不改本腳本。

### Task 1.1 — `committee_run.sh` mint round 並寫 `committee_round_open`（＝開債）

- **SPEC ref**：Task 1.1　**目標**：一輪派工有唯一且主委不可竄改的識別；寫入即開債，無分類、無豁免。
- **輸入**：`scripts/committee_run.sh` 現況 104 行（家族驗證 L38-56、gate 呼叫 L60-63、平行派工 L65-75）、`scripts/audit_append.sh`（Task 1.4）。
- **輸出**：改寫後的 `scripts/committee_run.sh`、`tests/governance/test_debt_emit.py`（新增）。
- **實作要點**（≥3）：
  1. **mint 與 append 是兩個不同時機，拆開看**（R1 C6 + R2 收口）：
     - **`round_id` mint ＝ 呼叫 `gate.sh` 之前**（pre-gate），並以 `--pending-round-id` 隨透傳 argv 交給 gate
     - **`committee_round_open` append ＝ `gate.sh dispatch`（現 L62）成功之後、啟動 `cx_run.sh`（現 L72）之前**（SPEC 改法②硬性，不變）
     ```
     # --- 段 A：pre-gate（L60 之前） ---
     round_id="${ROUND_ID_INHERITED:-$(uuidgen | tr 'A-Z' 'a-z')}"   # 只有 --round-id 才繼承
     brief_sha256_norm="$(_brief_sha256_norm "${brief}")"
     # 把 --pending-round-id "${round_id}" 併入傳給 gate.sh 的 argv

     # --- 段 B：post-gate、pre-cx_run（現 L63 與 L65 之間） ---
     bash scripts/audit_append.sh --event committee_round_open \
       --origin-script committee_run.sh --audit "${AUDIT}" \
       --field actor="${GOVERNANCE_ACTOR:-claude}" \
       --field round_id="${round_id}" --field task_id="${task_id}" \
       --field brief_path="${brief}" --field brief_sha256="…" \
       --field brief_sha256_norm="${brief_sha256_norm}" --field lock_mode="${lock_mode}" \
       --field participants=@"${participants_json}" --field quorum_eligible=@"${qe_json}" \
       --field expected_outputs=@"${eo_json}" --field expires_at="${expires_at}" \
       || { bash scripts/audit_append.sh --event round_open_failed … ; exit 1; }   # best-effort
     ```
     > **R2 更正（grok R2-P0-01）**：v0.2 的要點①（gate 後才 mint）與要點⑥（gate 前預 mint）同屏互斥，執行端無所適從。現拆成段 A／段 B 明示：**mint 在前、append 在後**，「不可做」的「不得在 gate 前寫 round_open」指的是 **append**，不是 mint。
     > **R2 更正（codex R2-P1-06）**：v0.2 的 caller 偽碼未帶 `--field actor=`（registry 必填欄），且三個陣列/物件欄位未用 Task 1.4 自訂的 `@<json>` 標記 → 依 Task 1.4 契約會被拒寫。已補齊。
  2. **`brief_sha256_norm` 演算法禁自創**：一律照 registry `docs.brief_sha256_norm_algo` — `sha256( unify_newline(content) 後，逐行 strip 行尾空白，再以 \n 連接 )`；`unify_newline`：CRLF/CR → LF。實作為單一函式 `_brief_sha256_norm()`，Task 1.2/1.3 共用同一函式（禁各自實作）。
  3. **participants 與 quorum_eligible**：`participants` 含 `advisory_only`（agy）；`quorum_eligible` **不含**。沿用現有 SoT 讀法（L41-42 的 `families_get families` / `families_get advisory_only`），**禁新寫死**。
  4. **append 失敗即中止**：`exit≠0` 且**不得**啟動 `cx_run`（現 L72 的 for 迴圈整段在 round_open 成功後才進入）。
  5. **CLI 參數**：`--round-id <既有>`（選填，只用於繼承 OPEN/PARTIAL round，見 Task 1.3）、`--lock-mode discovery|review`（值域見 registry `enums.lock_mode`）。**`task_id` 不另發明同名旗標**——一律**從 `--` 之後的透傳 argv 解析 gate 的 `--task-id`**，缺則 rc≠0。
     > **R1 更正（C12／grok P1-06）**：`gate.sh:189` 已有 `--task-id`，v0.1 又要 `committee_run` 新增同名旗標 → 執行端不知該在 `--` 前或後傳，易雙源或漏傳。
  6. **預 mint 與 `--pending-round-id`（R1 新增，C6）**：`round_id` 在**呼叫 `gate.sh` 之前**先 mint，並以 `--pending-round-id <id>` 隨透傳 argv 交給 gate（gate 端於本批只需**能解析該旗標且寫進 token**，`debt_epoch` 欄位留 B6′ 補）。`committee_round_open` **仍在 gate 成功之後、`cx_run` 之前**寫入（SPEC 改法②不變）。
     > **R1 更正（C6／codex P0-03＋grok P1-04）**：v0.1 讓 Task 1.1 在 gate 後才 mint，而 Task 4.2 要求 gate 前預 mint → B2 產出的控制流會被 B6 整段改寫＝短命工，且 B2 的 latency 量測（admission→append）在舊架構下量的不是最終路徑。改為 B2 一次到位。
- **修改檔案**（到函式名）：`scripts/committee_run.sh` — 新增 `_brief_sha256_norm()`、`_mint_round_id()`、`_emit_round_open()`；改動 L29-33 參數解析、L60-75 之間插入 emit；`ROUND_ID` 以 env 傳給 `cx_run.sh`（L72 呼叫改為 `ROUND_ID="${round_id}" bash "${SCRIPT_DIR}/cx_run.sh" …`）。
- **既有 caller**：Claude 直接呼叫（無腳本 caller，`grep -rn 'committee_run.sh' scripts/` → 僅文件）；文件 caller = `docs/COMMITTEE_DISPATCH_GUIDE.md`（Task 1.6 同步）。
- **不可做**：不得讓主委指定**新** `round_id`；不得在 gate 前寫 round_open；**不得對 N=1 略過開債**（憲法級裁決 1/3）。
- **邊界**（≥2）：
  1. N=1 → 仍開 round（無豁免）
  2. 繼承既有 round → 不 mint 新 id，改寫 amendment（Task 1.3）
  3. 只含 agy（advisory_only）→ 仍開 round，`quorum_eligible` 為空陣列
  4. gate 拒發 token → **不得**寫 `round_open`
  5. append 失敗 → `exit≠0` 且不啟動 `cx_run`，best-effort 寫 `round_open_failed`
- **風險緩解**：M2（不寫 per-family 事件）、M9（N=1 被略過開債）。
- **驗證**（可證偽）：`python -m pytest tests/governance/test_debt_emit.py -q` → rc=0；派 3 家後 audit 恰 **1** 筆 `committee_round_open`，`participants` 長度 == 3、`expected_outputs` 3 鍵；派 1 家也必須寫（斷言 count == 1）；`--task-id` 缺 → rc≠0；**未給 `--round-id` → 自動 mint**（不得要求必填）；同一 `round_id` 第二筆 → rc≠0；`codex,agy` → `participants` 長度 == 2、`quorum_eligible` 長度 == 1。
- **存活至**：永久保留。
- **覆蓋風險**：**有（R1 更正）**——B6′ 的 Task 4.2 會在本 Task 已寫入 token 的 `pending_round_id` 之外**追加** `debt_epoch` 與 `pending_deadline_ts` 兩欄。**控制流（預 mint→gate→round_open）在 B2 即定案，B6′ 不再改**，故非短命工；但 token schema 會擴充，B2 的 token 斷言**不得鎖死欄位總數**（只斷言必要欄存在）。

### Task 1.2 — `cx_run.sh` emit per-family 事件 + round membership 與 retry 契約

- **SPEC ref**：Task 1.2　**目標**：每家派工/結果各留一筆痕（家族名由 `$1` 直取）；retry 契約在此層也驗。
- **輸入**：`scripts/cx_run.sh` 現況 85 行（P1-1 brief 閘 L22-62、CLI 分派 L71-84）、`ROUND_ID` env（Task 1.1 傳入）、`scripts/audit_append.sh`。
- **輸出**：改寫後的 `scripts/cx_run.sh`、`tests/governance/test_debt_emit.py` 擴充。
- **實作要點**（≥3）：
  1. **fail-closed 前置（全部成立才派）**，插在現 L63（output 路徑檢查）之後、L65（CLI 路徑）之前：
     ```
     [ -n "${ROUND_ID:-}" ]                                  || exit≠0   # 且 audit 零新增
     audit 有 committee_round_open(round_id=$ROUND_ID)        || exit≠0
     fam ∈ effective_participants(round)                      || exit≠0
     out == effective_expected_outputs[fam]                   || exit≠0
     _brief_sha256_norm(brief) == round_open.brief_sha256_norm || exit≠0
     attempts(round,fam) < registry.constants.attempt_cap      || exit≠0
     latest_result_state(round,fam) != "success"               || exit≠0
     ```
  2. **家族名由 `$1` 直取**（現 L17 的 `fam`），**不得**從 `output_path`/`review_role` 推導（gate.sh 的 `_append_committee_dispatch_any()` 那套推導只適用 legacy 事件，本 Task 禁用）。
  3. **`result_state` 三態判定**：`success` = 產出含至少一條 `completeness_check.sh` 可接受的合格 finding，**判定用該 round 的 `lock_mode`**；`failed` = `cli_rc != 0` 或 output 空；`format_failed` = 其餘。**判定必須呼叫與 Task 3.1 相同的單一 validator 函式**——新增 `scripts/finding_validator.sh`，`cx_run.sh` 與 `debt_clear.sh` 同時 source 它。**禁複製正則、禁自創第二套判定器。**
     **介面契約（R1 補；C16／composer P1-04）**：
     ```
     finding_validator_has_valid_finding <output_path> <lock_mode>
       前置: lock_mode ∈ registry.enums.lock_mode，否則 rc=2（fail-closed）
       實作: **只**包裝 scripts/completeness_check.sh（或直接共用其 Python 模組）
             —— 禁在本函式內自寫任何 canonical-ID 正則
       rc 映射:  0 → 至少一條合格 finding
                 1 → 零合格 finding（呼叫端據此判 format_failed）
                 2 → 無法判定（檔缺/lock_mode 非法）→ 呼叫端 fail-closed
     呼叫端（cx_run）組合:
       cli_rc != 0 或 output 空                       → failed
       finding_validator rc == 0                      → success
       finding_validator rc == 1                      → format_failed
       finding_validator rc == 2                      → 拒寫 result，exit≠0
     ```
  4. **讀取＋attempt 保留＋append＋派工綁同一 `flock`**（防併發 retry 超過上限，M16）：臨界區涵蓋「算 attempt → 寫 `committee_family_dispatch` → 放鎖 → 跑 CLI → 寫 `committee_family_result`」；**CLI 執行本身不在鎖內**（否則平行派 N 家會退化成序列）。
  5. **CLI 失敗仍寫 result**：現 L85 的 `echo "[cx_run] ${fam} done rc=$?"` 之前插入 `committee_family_result` emit，帶 `cli_rc`，**不得靜默**。
- **修改檔案**（到函式名）：`scripts/cx_run.sh` — 新增 `_assert_round_membership()`、`_alloc_attempt_id()`、`_emit_family_dispatch()`、`_emit_family_result()`、`_classify_result_state()`；新增 `scripts/finding_validator.sh` — `finding_validator_has_valid_finding()`。
- **既有 caller**：`scripts/committee_run.sh:72`（唯一腳本 caller，Task 1.1 已改為傳 `ROUND_ID`）。**誠實邊界**：Claude 仍可直呼 `cx_run.sh`（V-D，§S-3 第 2 條），本 Task 只限制其危害（不能換 brief、不能重派 `success` 家族），**不宣稱阻擋**。
- **不可做**：不得從 `output_path`/`review_role` 推導家族；不得自創第二套 finding 判定器；不得把 CLI 執行放進 `flock` 臨界區。
- **邊界**（≥2）：
  1. `ROUND_ID` 未設 → 拒派 + audit **零新增**
  2. 家族不在 SoT → 拒派
  3. audit 檔不存在 → 建立而非崩潰
  4. 併發 3 家 → 3 筆完整不交錯（每筆為合法單行 JSON）
  5. CLI 失敗（如 503）→ 仍寫 result 帶 `cli_rc`，不得靜默
- **風險緩解**：M6、M11、M12、M16、M17、M22。
- **驗證**（可證偽）：`python -m pytest tests/governance/test_debt_emit.py -q` → rc=0；合法呼叫後 audit 新增 dispatch + result 各 1 筆且 `family == "grok"`（**非 `unknown`**）；`ROUND_ID=attacker` → rc≠0 且 audit 新增 0 筆；換 brief 掛既有 round → rc≠0；重派 `success` 家族 → rc≠0；兩程序併發 retry → 總 attempt ≤ `attempt_cap`（斷言 `max(attempt_id) <= 5`）；同一產出在 discovery round 與 review round 下 `result_state` 依各自 `lock_mode` 判定（FACT-RECEIPT 6：同 sources discovery rc=0 / review rc=1）。
- **存活至**：永久保留。
- **覆蓋風險**：無。
- **既有測試連動**：`tests/governance/test_family_registry.py` 依 §S-5 由**綠轉紅**（既有假綠：走 gate 直呼而非 `cx_run` 正式路徑）→ 本批**重寫**該檔走 `cx_run`，fixture 故意讓 `review_role` 不含家族名、gate 級 `--output` 為空，斷言 `family == "grok"`。**禁 xfail/skip**。

### Task 1.3 — `committee_round_amendment`：補派契約 + effective roster 定義

- **SPEC ref**：Task 1.3　**目標**：讓「繼承既有 round」不能變成「把新討論偽裝成 retry」；並定義 effective roster 供全鏈共用。
- **輸入**：`scripts/committee_run.sh`（Task 1.1 後版本）、registry。
- **輸出**：`committee_run.sh` 的 `--round-id` 分支、`scripts/debt_roster.sh`（effective roster 共用函式庫）、`tests/governance/test_debt_retry.py`（新增）。
- **effective roster（全鏈唯一定義；ledger/clear/quorum 一律用此，禁止直接讀 `round_open.participants`）**：
  ```
  effective_participants     = round_open.participants ∪ ⋃(amendment.added_families)
  effective_expected_outputs = round_open.expected_outputs ∪ ⋃(amendment.expected_outputs_delta)
  effective_quorum_eligible  = (round_open.quorum_eligible ∪ ⋃(amendment.quorum_eligible_delta))
                               − (advisory_only ∪ ⋃(amendment.advisory_delta))
  ```
- **實作要點**（≥3）：
  1. **共用函式庫**：新增 `scripts/debt_roster.sh`，導出 `roster_effective_participants <audit> <round_id>`、`roster_effective_expected_outputs`、`roster_effective_quorum_eligible`。`cx_run.sh`（1.2）、`debt_ledger.sh`（2.1）、`debt_clear.sh`（3.1/3.2）**一律 source 此檔**，禁各自重算。
  2. **帶 `--round-id` 時七項全成立才放行**：
     ```
     state ∈ {OPEN, PARTIAL}          # R2 移除 PENDING（codex R2-P1-07：無 round_open 可比對）
     brief_sha256_norm == round_open.brief_sha256_norm
     既有家族 path == round_open.expected_outputs[fam]；新家族 path 須在本次 expected_outputs_delta
     roster expand-only（不得縮減）
     attempts(round,fam) < attempt_cap
     latest_result_state(round,fam) != success
     task_id == round_open.task_id
     ```
  3. **delta 一致性 invariant**（M33）：
     ```
     quorum_eligible_delta ⊆ added_families
     advisory_delta        ⊆ added_families
     keys(expected_outputs_delta) ⊆ added_families
     quorum_eligible_delta ∩ advisory_delta == ∅
     所有 family ∈ SoT families
     effective_quorum_eligible ⊆ effective_participants
     ```
  4. **`reason` 長度下限**：`< registry.constants.reason_min_chars`（== 20）→ 拒。
  5. **amendment CLI 契約（R1 補；C13／codex P1-08）**：
     ```
     bash scripts/committee_run.sh <brief> <out前綴> <fams_csv> \
        --round-id <既有id> --reason "<≥20 字>" \
        [--advisory-add <fam,fam>] [--quorum-add <fam,fam>] -- <gate flags...>
     推導: added_families        = fams_csv − effective_participants(round)
           expected_outputs_delta= {fam: "<out前綴>-<fam>.md" for fam in added_families}
           quorum_eligible_delta = --quorum-add（預設 = added_families − advisory_only）
           advisory_delta        = --advisory-add（預設 = added_families ∩ advisory_only）
     ```
  6. **`PENDING` 的語義（R1 補；C11／grok P1-05。R2 收緊；codex R2-P1-07）**：`registry.enums.round_state` 含 `PENDING`，定義為「已預 mint `round_id`／已發帶 `pending_round_id` 的 token，但 audit 尚無對應 `committee_round_open`」。**`PENDING` 不計債**（與 `round_open_failed` 同），逾 `pending_deadline_ts` 後該 id 作廢。狀態產生點在 Task 2.1。
     **⚠️ `PENDING` 一律不得進 amendment**：本 Task 的七項前置全部要讀 `round_open.brief_sha256_norm` / `round_open.expected_outputs` / `round_open.task_id`，而 `PENDING` 依定義**沒有** `round_open`，無 canonical parent 可比對 → 允許繼承等於讓執行端自行發明「token 內要不要存 brief/task/roster」。故 Task 1.3 合法狀態集合修正為 **{OPEN, PARTIAL}**（**移除 `PENDING`**）。`PENDING` 期間要改組成，正確作法是讓該 id 作廢後重開一輪。
- **修改檔案**（到函式名）：`scripts/committee_run.sh` — `_handle_round_inherit()`、`_emit_amendment()`、`_assert_amendment_invariants()`；新增 `scripts/debt_roster.sh` — 三個 `roster_*()` 函式。
- **既有 caller**：`scripts/debt_roster.sh` 的 caller 於 B2/B4/B5 陸續接上（Task 1.2、2.1、3.1、3.2）。
- **不可做**：不得允許換 brief 沿用 round；不得無上限 retry；不得允許 roster 縮減。
- **邊界**（≥2）：
  1. round 已 CLOSED/ABANDONED → 拒繼承
  2. `brief_sha256_norm` 差一 byte → 拒
  3. amendment append 失敗 → 同 Task 1.1 邊界⑤（`exit≠0` 且不啟動 `cx_run`）
  4. `reason` 短於 `constants.reason_min_chars` → 拒
- **風險緩解**：M33（delta 落在 `added_families` 外）、M19（加家族後仍讀 `round_open.participants`，B4 驗收）。
- **驗證**（可證偽）：`python -m pytest tests/governance/test_debt_retry.py -q` → rc=0；換 brief 帶同一 `--round-id` → rc≠0；roster 縮減 → rc≠0；超過 `attempt_cap`（== 5）→ rc≠0；換 `task_id` → rc≠0；`added=[composer]` 配 `quorum_eligible_delta=[grok]` → rc≠0；`expected_outputs_delta` 含 `added_families` 外的 key → rc≠0；正常補派 → rc=0。
- **存活至**：永久保留。
- **覆蓋風險**：無。

### 【B2 出場 gate】Task 4.2 的 N 值量測（Phase 1 進場 gate 的實體）

> SPEC Task 4.2 規定 `pending_deadline` 的 N **必須由量測決定**，量測 workload ＝ `committee_run.sh` 派 3 家 × 20 次的 admission→append latency，取 p99；`N = clamp(ceil(p99 × 3), 5, 60)`（值域見 registry `constants.pending_deadline_{min,max}_seconds`）；**若 `ceil(p99×3) > 60` → 不得部署固定時間窗，改用原子 handoff**。

- **執行方式**：60 次真實 CLI 派工不可行（成本與時間皆不合理，且量測目標是 admission→append 這段本地延遲，與 CLI 回應無關）。以 `CX_RUN_BIN_OVERRIDE`（**綁 `GOVERNANCE_TEST_HARNESS=1`**）把 `cx_run.sh` 的 **CLI binary** 換成 no-op stub。**stub 只替換 binary，不得跳過任何治理路徑**（R1／C15）。
- **量測區間定義（精確；codex P1-06 要求）**：
  - **start**＝`committee_run.sh` 內 `gate.sh dispatch` 回傳 rc=0 的時刻
  - **end**＝`audit_append.sh` 寫入該 round 的 `committee_round_open` 並釋放 `flock` 的時刻
  - 每次迴圈**必須**真的啟動 3 個背景 `cx_run` job（stub 版），以量到平行啟動與 flock 競爭；跳過此步的量測作廢
- **probe driver（R2 補；codex R2-P1-08——receipt 可被手工放置就不算可證偽）**：
  ```
  新增 scripts/p16_latency_probe.sh（B2 交付物之一）
    用法: bash scripts/p16_latency_probe.sh --runs 20 --families codex,composer,grok \
             --out handoffs/run_receipts/<UTC>-p16-latency-probe.log
    前置: GOVERNANCE_TEST_HARNESS=1 且 CX_RUN_BIN_OVERRIDE 指向 stub，否則 rc≠0
  stub 契約（CX_RUN_BIN_OVERRIDE 指向的可執行檔）:
    argv 與真實 CLI 同形: <stub> <family> <brief> <out> [effort]
    行為: 立即 touch "<out>" 寫入一行合格 finding 骨架後 exit 0（不呼叫任何網路服務）
    exit: 0=成功 / 非 0=模擬 CLI 失敗（供 result_state=failed 的路徑測試）
  receipt producer: 由本腳本寫入，首行含 producer=p16_latency_probe.sh 與 stub sha256
  B2 gate 驗證命令（非「檔案存在」而已）:
    bash scripts/p16_latency_probe.sh --verify <receipt>  → rc=0 才算通過
      （檢查 producer 行、20 筆樣本數、p99 欄、公式欄、sanity sample 差異 < 2×）
  ```
- **產物**：`handoffs/run_receipts/<UTC>-p16-latency-probe.log`，**須含**：①stub 開啟條件與 binary 路徑 ②20 次迴圈各自 3 個背景 job 的啟動證據 ③20 筆原始 admission→append 耗時 ④p99 ⑤`ceil(p99×3)` 與 `clamp(…,5,60)` 的算式 ⑥是否觸發 atomic-handoff 分支 ⑦**另抽 3 次真實 codex/composer/grok 任一家 sanity sample**，與 stub p99 差異須 < 2×（composer P1-02 要求；差異過大代表 stub 量錯區間）。
- **`ceil(p99×3) > 60` 的分支（R1 補；codex P1-06 指出原本無 Task）**：改用**原子 handoff**——`gate.sh` 發 token 與 `audit_append` 寫 `round_open` 在同一 `flock` 臨界區內完成，token 不帶 `pending_deadline_ts`（無時間窗可逾期）。此分支若觸發，**須回頭補 SPEC**（屬架構變更），並在本 TODO 新增具名 Task 4.2b；不得由執行端臨場發明。
- **落地**：見 §Q-4／§Q-8——**N 的寫入路徑須先裁決**，B2 不得逕自改 registry。

### Task 1.5 — 封住 `impl`/`stamp` brief 跳過 P1-1 範本閘

- **SPEC ref**：Task 1.5　**目標**：消滅「標 `impl` 即跳過範本＋前提檢查」（與紅隊 V-E 同構）。
- **輸入**：`scripts/cx_run.sh:35-62`（`_bk` 解析 + `case` 分支）。**錨點以 repo 現況為準**（SPEC 寫 `:41-61` 為概略；實檔 `brief-kind` 解析自 L35，已實查，R1／C18）。
- **輸出**：改寫後的 `case` 分支、`tests/governance/test_brief_conformance.py` 擴充。
- **實作要點**（≥3）：
  0. **Q-11 已裁決（使用者交委員會，三家憲法解釋輪；v0.4 依裁決重寫本 Task）**：v0.3 用「命中範本 → 覆寫 `_bk="review"`」的**類別覆寫**寫法**作廢**。裁決＝裁決 2 拆為 2a／2b（見 §0 R-4），且 Task 1.5 改採 **單一 validator + 加法義務**——這樣**根本沒有分類器**，不必為「這個分類器是合法分類器」發明豁免。**行為與測試不變**。
     > v0.3 曾用三個理由主張「部分不採納 codex」，其中**兩個已被三家推翻**：①「SPEC 已戳記」＝戳記不洗錯設計 ②「grok §4 判定合規」＝引用過寬，grok 從未背書。第三個「方向取嚴」單獨也不成立，須改寫成 R-4b 的三條可操作條件。
  1. **移除依 `brief-kind` 分岔的兩條路**：現況 `scripts/cx_run.sh:60` 的 `impl|stamp) : ;;` 直接放行，是兩條檢查路徑的根源。改為**所有 brief 一律進同一個共同 validator**：
     ```
     _TPL_RE='SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT|COMMITTEE_SEMANTIC_REVIEW_TEMPLATE|COMMITTEE_FINDING_TEMPLATE'

     _brief_validate() {                     # 單一入口，無分支、無類別覆寫
       local brief="$1" bk="$2"
       # ── 基準義務（所有 brief 一律套用）──
       [ -n "${bk}" ] || fail "brief 缺 'brief-kind:' 宣告"
       case "${bk}" in review|consult|closure|impl|stamp) : ;; *) fail "未知 brief-kind: ${bk}" ;; esac
       # ── 加法義務（偵測到範本引用才追加，不改變 bk、不改變入口）──
       if grep -qE "${_TPL_RE}" "${brief}"; then
         [ "$(grep -cE 'fact-verified:' "${brief}")" -ge 1 ] || fail "須含 fact-verified: 前提宣告"
         [ "$(grep -cE 'assumed:'       "${brief}")" -ge 1 ] || fail "須含 assumed: 前提宣告"
       fi
       # ── 既有 review|consult|closure 的兩項義務維持不變 ──
       # ── 既有 review|consult|closure 兩項義務（照現況 cx_run.sh:42-59 搬過來，一字不改）──
       case "${bk}" in
         review|consult|closure)
           # ①範本引用（現況 L44-47）
           grep -qE "${_TPL_RE}" "${brief}" \
             || fail "brief-kind=${bk} 須引用委員範本(templates/<範本>.md)"
           # ②前提宣告（現況 L51-58）；grep -c 未命中時 stdout=0 但 rc=1，須 || true 吞 rc
           _n_fact="$(grep -cE 'fact-verified:' "${brief}" 2>/dev/null || true)"
           _n_assumed="$(grep -cE 'assumed:' "${brief}" 2>/dev/null || true)"
           [ "${_n_fact}" -ge 1 ] && [ "${_n_assumed}" -ge 1 ] \
             || fail "brief-kind=${bk} 須含前提宣告(fact-verified/assumed 各≥1)，現況 fact=${_n_fact} assumed=${_n_assumed}"
           ;;
       esac
     }
     ```
     **`_TPL_RE` 是單一真相源**，禁複製成第二處（現況 L44 那份 grep 併入此變數）。
  2. **不得重新歸類**：validator **不得**修改 `bk` 的值、不得把 brief 導向另一個入口或債務種類——那會落入 R-4a 的禁令（SPEC v1.2.1 Task 1.5 改法⑤）。
  3. **取嚴**：brief 僅在註解提及範本名 → 仍追加義務（不做上下文判別，避免變成可繞的啟發式）。
  4. **不放寬既有分支**：`review|consult|closure` 的兩項檢查（範本引用 + `fact-verified:`／`assumed:` 前提宣告）一字不改。
- **⚠️ 誠實邊界**（不得宣稱覆蓋）：反向（討論 brief 標 `impl` 且**不引用**範本）擋不住——但一扇門下該輪仍會開債，且產出若無合格 finding 會判 `format_failed` → 須重派至上限才能走終局出口。**摩擦本身即為防線。**
- **修改檔案**（到函式名）：`scripts/cx_run.sh` — L35-62 區塊改寫，新增 `_TPL_RE` 常數與 `_brief_validate()`（**單一 validator，取代原 `case` 兩條路**）。**不得**新增任何改寫 `_bk` 值的函式（原提案的 `_coerce_brief_kind()` 已因 Q-11 裁決作廢）。
- **既有 caller**：`scripts/committee_run.sh:72`；Claude 直呼。
- **不可做**：不得放寬既有 `review|consult|closure` 分支檢查；**不得用產出 marker 掃描當分類器**（三家一致：誤殺 + 可繞）。
- **邊界**（≥2）：
  1. 真 impl brief（不引用任何範本）→ **行為不變，不誤擋**（既有 `test_impl_kind_not_required_to_have_finding_clauses` 須保持綠）
  2. brief 僅在註解提及範本名 → **仍追加義務**（取嚴；v1.2.1 起無「覆寫類別」動作）
- **風險緩解**：M10（`impl`/`stamp` brief 引用範本仍跳過 P1-1）。
- **驗證**（可證偽）：brief 標 `brief-kind: impl` 但引用 adversarial 範本 → 仍執行 P1-1 兩項檢查（缺前提宣告 → rc≠0，且訊息含 `fact-verified=0`）；`python -m pytest tests/governance/test_brief_conformance.py -q` → rc=0；新增含範本的 impl brief negative test；`test_impl_kind_not_required_to_have_finding_clauses` **保持綠**。
- **存活至**：永久保留。
- **覆蓋風險**：無。

### Task 1.6 — 更新派工規範文件

- **SPEC ref**：Task 1.6　**目標**：把「一扇門、一律開債」寫進規範。
- **輸入**：`docs/COMMITTEE_DISPATCH_GUIDE.md` 現況。
- **輸出**：更新後的同檔。
- **實作要點**（≥3）：
  1. 所有 `gate.sh dispatch` / `committee_run.sh` 範例補 `--task-id`（現況 `grep -c '\-\-task-id'` == 0）。
  2. 新增「一扇門」一節：所有委員派工一律走 `committee_run.sh`、**一律開債，含只派一家**；無分類、無豁免、無執行通道。
  3. 新增「輪次與債務」語意小節：開債時機／清帳嚴格度依家族數／retry 契約／TTL 7 日且禁自動 clear。條數與枚舉一律 pointer 至 `scripts/audit_events.json`，**不重列**。
  4. **誠實邊界以 SPEC §A 為唯一真相源**，本文件 pointer 過去，不重列十四條。
- **修改檔案**：`docs/COMMITTEE_DISPATCH_GUIDE.md`（新增兩節 + 範例補旗標）。
- **既有 caller**：無程式 caller；`CLAUDE.md`／`HANDOFF.md` 引用本檔。
- **不可做**：不得只改文件不改腳本；不得在文件重列 registry 內容或誠實邊界條文。
- **邊界**（≥2）：
  1. 文件與腳本不一致 → 由腳本 fail-closed 兜底（文件非強制來源）
  2. 條數/枚舉一律 pointer，不重列（避免與 registry 漂移）
- **風險緩解**：無新增 mutation（文件層）；由 grep 驗收。
- **驗證**（可證偽）：`grep -c '\-\-task-id' docs/COMMITTEE_DISPATCH_GUIDE.md` ≥ 1（現況 0）；`grep -cE '一扇門|一律開債' docs/COMMITTEE_DISPATCH_GUIDE.md` ≥ 1；`bash scripts/check_doc_anchors.sh` rc=0。
- **存活至**：永久保留。
- **覆蓋風險**：無。

---

## Phase 2 — 債務帳本（依賴：Phase 1）

**完成後系統狀態**：有一支只讀 audit 的腳本，能列出所有未結案債與其狀態，不另存狀態檔。

### Task 2.1 — `debt_ledger.sh`：只讀 audit 算未結案債

- **SPEC ref**：Task 2.1　**目標**：由客觀事件算出哪些 round 欠收集整理。
- **輸入**：audit log（路徑由 `--audit` 傳入，預設 registry `audit_log_path`）、registry、`scripts/debt_roster.sh`。
- **輸出**：`scripts/debt_ledger.sh`（新增，**不另存狀態檔**）、`tests/governance/test_debt_ledger.py`（新增）。
- **實作要點**（≥3）：
  1. **介面**：`bash scripts/debt_ledger.sh --list [--audit <path>] [--round-id <id>]`；rc=0 表示查詢成功（**不是**表示無債），未結案債以 stdout 逐行列出並以 `--has-open` 子命令回傳 rc（`0`=無債／`1`=有債／`2`=fail-closed）。介面語意須在檔頭寫死，供 Task 4.1 消費。
  2. **解析與 cutoff**：只認 `startswith("{")` 的行（現存 audit 混有 `=== ts | kind ===` 區塊文字，見 `gate.sh:588`）；cutoff 依 registry `cutoff_ts`，**禁 CLI/env 自由指定**，僅 `GOVERNANCE_TEST_HARNESS=1` 可覆寫。
  3. **狀態機**（值域見 registry `enums.round_state`）：
     ```
     已發 pending token 但無 round_open → PENDING（**不計債**；逾 pending_deadline_ts 作廢）
     每個 committee_round_open      → 一筆債
     有 round_open_failed            → 不計債
     有合法 clear（三種 closes_debt 事件）→ CLOSED
     有 debt_abandon                 → ABANDONED（終結）
     now > expires_at                → EXPIRED_OPEN
     任一 effective 家族最新 result_state ∈ {failed, format_failed}
        且未補派、未 degrade         → PARTIAL
     其餘                            → OPEN
     有 supersedes 者取最新；同 round 取嚴
     ```
  4. **roster 一律用 effective roster**（source `scripts/debt_roster.sh`），**禁止直接讀 `round_open.participants`**（M19）。
  5. **白名單事件的 `sequence` gap/duplicate → fail-closed**；legacy 事件不參與 gap 掃描（Task 1.4 契約）。
- **修改檔案**（到函式名）：新增 `scripts/debt_ledger.sh` — `_parse_audit()`、`_round_state()`、`_latest_result_state()`、`_has_valid_clear()`、`_cmd_list()`、`_cmd_has_open()`。
- **既有 caller**：本 Task 落地時 0 個；Task 4.1（`gate.sh:_check_open_debt()`）與 Task 4.2（`gate_check.sh`）為消費端。
- **不可做**：不得另存 JSON 狀態檔（唯一真相＝audit）；不得靜默自動過期；不得直接讀 `round_open.participants`。
- **邊界**（≥2）：
  1. **audit 檔缺失** → fail-closed（rc=2）
  2. **audit 存在但零 JSON 事件** → **無債，rc=0 放行**（14 檔測試用隔離空 audit；不分三態會整批真回歸）
  3. **ledger 腳本缺失/崩潰** → 由消費端 fail-closed（Task 4.1 邊界②）
  4. 同一 `round_id` 兩筆 `round_open` → fail-closed
- **風險緩解**：M19（amendment 後仍讀 `round_open.participants`）、**M20**（legacy 被當 gap；R1 由 B2 移入本批）。
- **驗證**（可證偽）：`python -m pytest tests/governance/test_debt_ledger.py -q` → rc=0；派 3 家 → `--list` 印 1 筆 `OPEN`；**派 1 家 → 也印 1 筆 `OPEN`**；clear 後 → 0 筆；cutoff 前事件 → 0 筆；N=1 經 amendment 補成 2 家 → 清帳分流依 effective roster（斷言 `len(effective_participants) == 2`）；**混合現存 181 筆 legacy（無 sequence）+ 新事件 1..N → `--list` rc=0**（M20，防誤殺真 audit）；**白名單事件人工插入 sequence gap → rc≠0**；只有 pending token 無 `round_open` → 該 round 顯示 `PENDING` 且 `--has-open` rc=0（不計債）。
- **存活至**：永久保留。
- **覆蓋風險**：無。Phase 3/4 只消費本腳本，不改其狀態機。

---

## Phase 3 — 銷帳（依賴：Phase 2）

**完成後系統狀態**：有唯一一支 `debt_clear.sh` 提供四條銷帳路徑（完整清帳／format 終局／全 degrade 終局／更正 supersede）與單家族 degrade，全部 append-only、全部有前置條件檢查（見 Task 3.1 的五項綁定）。

### Task 3.1 — 完整清帳：completeness PASS 綁 round + effective roster

- **SPEC ref**：Task 3.1　**目標**：跑完機械合併且 0 掉項才算還債。
- **輸入**：`handoffs/reconcile/<session>/sources.lock`、`synth.md`、`scripts/completeness_check.sh` 的 rc、`scripts/debt_roster.sh`。
- **輸出**：`scripts/debt_clear.sh`（新增，本 Task 建立骨架）、`tests/governance/test_debt_clear.py`（新增）；`scripts/reconcile_build.sh` 於 completeness PASS 後**提示**可銷帳（不自動銷）。
- **實作要點**（≥3）：
  1. **介面**：`bash scripts/debt_clear.sh --round-id <id> --session <handoffs/reconcile/<name>> [--audit <path>]`，預設 `clear_kind=full`。
  1b. **`clear_kind` 四值各有落點（R1 補；C7／codex P0-02）**——registry `clear_kind_event_map` 已定映射，本 epic 的子命令對應如下，缺一即執行端無法安全實作：

     | `clear_kind` | 子命令 | 寫入事件 | 定義於 |
     |---|---|---|---|
     | `full` | `debt_clear.sh --round-id … --session …`（預設） | `committee_debt_clear` | Task 3.1 |
     | `family_degrade` | `debt_clear.sh --round-id … --clear-kind family_degrade --family <fam> --session …`（**canonical 唯一入口**；Task 3.4 的 `--degrade` 是**寫 degrade 事件**，兩者不是 alias） | `committee_debt_clear`（**同一事件型別，靠 `clear_kind` 區分**） | Task 3.1（本 Task）＋前置條件見 Task 3.4 |

     **`roster` 欄語義（R2 補；codex R2-P1-09）**：registry `committee_debt_clear.fields` 只有 `roster`、沒有 `family`／`absent_family`，故 `roster` 一律填「**本次清帳所涵蓋的家族集合**」——`full` 時 ＝ `effective_participants`；`family_degrade` 時 ＝ **僅該單一家族**（`[<fam>]`）。ledger 據此識別單家族清帳：某 round 的 `family_degrade` clear 事件 `roster` 之聯集 ∪ `full` clear 的 `roster` ⊇ `effective_participants` 才算全清。**冪等**：同 `(round_id, clear_kind, roster)` 重複寫 → no-op。
     > 兩支旗標的分工，一句話：`--degrade` 是「**記錄**某家交不出來」（Task 3.4，`closes_debt=false`），`--clear-kind family_degrade` 是「**據此結掉那一家的帳**」（本 Task）。缺任一環，PARTIAL 都沒有出口。
     | `format_failure` | `debt_clear.sh --round-id … --format-failure --reason … --approver …` | `committee_debt_clear_format_failure` | Task 3.2 |
     | `all_degraded` | `debt_clear.sh --round-id … --all-degraded --reason … --approver … --degrade-ids …` | `committee_debt_clear_all_degraded` | Task 3.2 |

     **`family_degrade` 的語義**：結**單一家族**的清帳要求（該家族退出 effective clear roster），**不結整輪債**——round 仍為 `PARTIAL` 直到其餘家族各自有出路。前置＝該家族有**有效**的 `committee_family_degrade`（Task 3.4）。**注意 registry `committee_family_degrade.closes_debt == false`**：degrade 事件本身不清帳，清帳一律經 `debt_clear.sh`。
  2. **五項全成立才寫 `committee_debt_clear`**（`clear_kind=full` 時）：
     ```
     ① ledger(round) ∈ {OPEN, PARTIAL}
     ② set(lock.expected_roster) ⊇ set(effective_participants(round))     # 少一家即拒
     ③ completeness_rc == 0                                              # 由本腳本實跑 completeness_check.sh --lock
     ④ clear.ts > round_open.ts
     ⑤ lock_sha256 == sha256(<session>/sources.lock)
     ```
  3. **finding validator 同一函式**：本 Task 對「合格 finding」的判定必須呼叫 Task 1.2 建立的 `finding_validator_has_valid_finding()`（`scripts/finding_validator.sh`），**禁第二套**。
  4. **工具優先**：completeness 一律呼叫 `scripts/completeness_check.sh --lock`，**不得**重寫合併/比對邏輯（SPEC §C「工具優先」，雙家 code review 逐項確認）。
- **修改檔案**（到函式名）：新增 `scripts/debt_clear.sh` — `_cmd_full_clear()`、`_assert_roster_covers()`、`_run_completeness()`、`_emit_clear()`；`scripts/reconcile_build.sh` 尾端新增一行提示（**不自動銷帳**，維持 FACT-RECEIPT 9「清帳路徑不經 dispatch 閘」的性質）。
- **既有 caller**：Claude 手動呼叫；`scripts/reconcile_build.sh` 只提示不呼叫。
- **不可做**：不得接受 `waived:` 當銷帳；不得讓 `--force` 繞過本 Task 五項綁定；不得在 `reconcile_build.sh` 內自動銷帳。
- **邊界**（≥2）：
  1. 重複銷帳 → 冪等 no-op（rc=0，不重複 append）
  2. `completeness rc == 3`（DEGRADED_PENDING）→ **不得整輪銷帳**；合法 degrade 可 `clear_kind=family_degrade` 結**單一家族**帳
  3. `round_open` 不存在 → 拒
  4. lock 被竄改 → sha256 比對失敗即拒
  5. PARTIAL → 缺席家族須補派成功或合法 degrade
- **風險緩解**：M3、M4、M5、M23。
- **驗證**（可證偽）：`python -m pytest tests/governance/test_debt_clear.py -q` → rc=0；拿 A 輪 lock 銷 B 輪債 → rc≠0；roster 少一家（含 amendment 新增的）→ rc≠0；`--reconcile waived:理由` 型輸入 → rc≠0；正常 → rc=0 且 `debt_ledger.sh --list` 該 round 轉 `CLOSED`。
- **存活至**：永久保留。
- **覆蓋風險**：無。Task 3.2/3.3/3.4 為同檔**新增**子命令，不改本 Task 五項綁定。

### Task 3.2 — 清帳嚴格度 + 終局出口

- **SPEC ref**：Task 3.2　**目標**：家族數決定「清帳要多嚴」；並為「委員交不出合格 finding」提供高摩擦終局。
- **輸入**：`scripts/debt_clear.sh`（Task 3.1 骨架）、audit 既有 `result_state`、registry `constants.reason_min_chars`。
- **輸出**：`debt_clear.sh` 的 `--format-failure` 與 `--all-degraded` 子命令、`test_debt_clear.py` 擴充。
- **實作要點**（≥3）：
  1. **嚴格度規則**：
     ```
     len(effective_participants) >= 2 → 必須走 Task 3.1，禁走「非 attempts_exhausted」的簡化出口
     len(effective_participants) == 1 → 亦不得以 prose-only 清帳；合法出路同多家
     ```
  2. **`committee_debt_clear_format_failure`（適用所有家族數，含 ≥2）**，四項全成立才寫：
     ```
     ① 所有 effective 家族的最新 result_state == "format_failed"
        （**直接讀 audit 既有值，禁止第二套掃描規則** — M28）
     ② 每家族 attempt 均達 registry.constants.attempt_cap
     ③ len(reason) >= registry.constants.reason_min_chars
     ④ approver 非空
     ```
  3. **`committee_debt_clear_all_degraded`（終局出口 B）**，五項全成立才寫：
     ```
     ① 所有 effective 家族皆有【有效（未逾期）】的 committee_family_degrade
     ② 每家族 attempt 均達上限
     ③ len(reason) >= reason_min_chars
     ④ approver 非空
     ⑤ degrade_event_ids 與 effective 家族【精確一一對應】（跨 round／重複／過期 ID → 拒）
     不要求 completeness_rc == 0（該 round 結構上不可能有合格 finding）
     ```
  4. **`output_sha256` 校驗**：清帳前比對 `committee_family_result.output_sha256` 與現檔 sha256，不符 → fail-closed（防 stale 狀態當清帳證據）。
- **⚠️ 誠實邊界**（不得宣稱覆蓋）：§S-3 第 6/7/8 條——付費出口（主委可蓄意寫爛 brief 燒 `5×N` 次派工換一次清帳）、`approver` 身份不可驗證。**機器擋不住 brief 品質。**
- **修改檔案**（到函式名）：`scripts/debt_clear.sh` — `_cmd_format_failure()`、`_cmd_all_degraded()`、`_assert_attempts_exhausted()`、`_assert_degrade_ids_bijective()`、`_assert_output_sha_fresh()`。
- **既有 caller**：Claude 手動呼叫。
- **不可做**：不得接受 `waived:` 字串；不得在 `attempts_exhausted` 未成立時開放簡化出口；不得對 ≥2 家族禁用 `format_failure`（終局出口必須開，否則死鎖）。
- **邊界**（≥2）：
  1. 產出檔缺失 → 依 audit 既有 `result_state`；若連 `committee_family_result` 都缺 → **fail-closed 拒清**
  2. 同 round 已有 clear → no-op
  3. `result_state` 事件重複 → 取 `sequence` 最大者
  4. `output_sha256` 與現檔不符 → fail-closed
- **風險緩解**：M15、M24、M28、M31。
- **驗證**（可證偽）：`python -m pytest tests/governance/test_debt_clear.py -q` → rc=0；≥2 家族走「非 `attempts_exhausted`」的簡化出口 → rc≠0；≥2 家族且全 `format_failed` 且 attempt 全達上限（== 5）→ rc=0（**終局出口必須開**）；`degrade_event_ids` 缺一家/含跨 round/含過期 → rc≠0；`reason` 長度 < 20 → rc≠0；產出「帶 `^Verdict:` 但零合格 finding」→ `result_state == "format_failed"` 且終局出口可用（不得因舊掃描規則判 `success`）。
- **存活至**：永久保留。
- **覆蓋風險**：無。

### Task 3.3 — `committee_debt_supersede`：可稽核的更正路徑

- **SPEC ref**：Task 3.3　**目標**：錯誤寫入的 clear 有 append-only 更正路徑。
- **輸入**：`scripts/debt_clear.sh`、registry `enums.supersede_direction`（**僅 `tighten`**）。
- **輸出**：`debt_clear.sh --supersede <event_id>` 子命令、`tests/governance/test_debt_supersede.py`（新增）。
- **實作要點**（≥3）：
  0. **CLI 契約（R2 補；codex R2-P1-10）**：
     ```
     bash scripts/debt_clear.sh --supersede <target_event_id> --round-id <id> \
        --direction tighten --reason "<≥20 字>" --approver "<非空>"
     --direction 值域讀 registry enums.supersede_direction（現唯一合法值 tighten）；
       非法值或缺 → rc≠0（不得預設帶入）
     四欄（round_id/supersedes/reason/approver/direction）對應 registry
       required_fields_per_event.committee_debt_supersede，缺一 → rc≠0
     成功 → stdout 印新 event_id，rc=0；ledger 該 round 回 OPEN
     ```
  1. `direction` 值域一律讀 registry `enums.supersede_direction`；目前唯一合法值 `tighten`（CLOSED → OPEN）。**不得放寬**（OPEN → CLOSED 必須走完整 clear 條件）。此處的 `supersedes` 欄**專指 clear 更正**，與 Task 3.4 degrade 續期的 `renew_of` 是**兩個不同語意**，禁混名（Q-9）。
  2. ledger 對同一 round **取嚴**：存在 supersede 時，round 狀態取「較嚴」者（OPEN 嚴於 CLOSED）。此規則實作在 `debt_ledger.sh:_round_state()`（Task 2.1 已預留 `有 supersedes 者取最新；同 round 取嚴`）。
  3. 前置驗證：`supersedes` 指向的 `event_id` 必須存在、必須是 clear 類事件、該 round 不得已 ABANDONED。
- **修改檔案**（到函式名）：`scripts/debt_clear.sh` — `_cmd_supersede()`、`_assert_supersede_target()`；`scripts/debt_ledger.sh` — `_round_state()` 補取嚴邏輯。
- **既有 caller**：Claude 手動呼叫。
- **不可做**：不得允許放寬向 supersede（`direction=loosen` 一律 rc≠0，即使 registry 未來新增該值也須 SPEC 先改）。
- **邊界**（≥2）：
  1. `supersedes` 指向不存在的 `event_id` → 拒
  2. 指向非 clear 類事件 → 拒
  3. 該 round 已 ABANDONED → 拒
- **風險緩解**：M14（supersede 允許放寬向）。
- **驗證**（可證偽）：`python -m pytest tests/governance/test_debt_supersede.py -q` → rc=0；用 supersede 把 OPEN 變 CLOSED → rc≠0；正常收緊 → `debt_ledger.sh --list` 該 round 回 `OPEN`；指向不存在 `event_id` → rc≠0。
- **存活至**：永久保留。
- **覆蓋風險**：無。

### Task 3.4 — `committee_family_degrade`：單家族退出清帳要求

- **SPEC ref**：Task 3.4　**目標**：讓「某家族反覆交不出合格產出」有可稽核的退出機制。
- **輸入**：`scripts/debt_clear.sh`、registry（`committee_family_degrade` 欄位含 `expiry`、`remediation_owner`、`renew_of`）。
- **輸出**：`debt_clear.sh --degrade` 子命令、`tests/governance/test_debt_degrade.py`（新增）。
- **實作要點**（≥3）：
  1. **前置**：該家族最新 `result_state ∈ {failed, format_failed}` **且** attempt 已達 `attempt_cap`。對 `success` 家族使用 → rc≠0。
  2. **ledger 轉移**：該家族退出 `effective_participants` 的**清帳要求**（audit 紀錄保留，不刪事件）。實作在 `debt_ledger.sh` 與 `debt_roster.sh` 的消費側，非改寫 roster 本身。
  3. **`expiry` 生命週期**：逾期 → 該 degrade 失效，round 回 `PARTIAL`；**每 `(round_id, family)` 最多一個 degrade 事件**，逾期後不得再 degrade。
  4. **`--renew-once` 配額＝每 `(round_id, family)` 至多一次**（registry `constants.renew_once_per_round_family` == 1）。**配額不得寫成「每 round 全域一次」**（M34：≥2 家族同時卡住時只能救 1 家，其餘仍死鎖）。須附續期指標，指向**同 round 同 family 且已逾期**的 degrade 事件。
     **續期指標＝`renew_of`（§Q-9 已裁決，三家一致，SPEC v1.2.1 + registry 均已落地）**：`committee_family_degrade.fields` 的 `renew_of` 是唯一 SoT；`docs.renew_once` 原誤寫 `supersedes` 已更正；`renew_of` 已加入 `debt_event_optional_fields`。**`supersedes` 專屬 Task 3.3 的 `committee_debt_supersede`（clear 更正事件），兩者語意不同，禁混名。**
  5. **degrade CLI 契約（R1 補；C13／codex P1-08）**：
     ```
     bash scripts/debt_clear.sh --degrade --round-id <id> --family <fam> \
        --reason "<≥20 字>" --approver "<非空>" --expiry <ISO8601> \
        --remediation-owner "<非空>" [--renew-once --renew-of <event_id>]
     六必填欄缺一 → rc≠0（對應 registry required_fields_per_event.committee_family_degrade）
     ```
- **⚠️ 逾期後的可達終局（防死鎖，v1.0 明列）**：逾期且 attempt 已達上限的家族，其 round 仍可走：**(a)** 全族 `format_failed` → `format_failure`；**(b)** 全族有**有效** degrade → `all_degraded`；**(c)** 逾 TTL → `debt_abandon`。若該家族 `result_state == failed`（非 `format_failed`）且其 degrade 已逾期，(a) 與 (b) 皆不可達 → 此時**允許 `--degrade --renew-once`** 重開一次。此為明列成本，非隱含死鎖。
- **修改檔案**（到函式名）：`scripts/debt_clear.sh` — `_cmd_degrade()`、`_assert_degrade_preconditions()`、`_assert_renew_quota()`；`scripts/debt_ledger.sh` — `_effective_clear_roster()`（扣除有效 degrade 家族）。
- **既有 caller**：Task 3.2 的 `_cmd_all_degraded()` 消費 degrade 事件。
- **不可做**：不得讓 degrade 繞過 attempt 上限；不得對 `success` 家族使用；不得無限續期；不得把 `renew_once` 配額寫成每 round 全域一次。
- **邊界**（≥2）：
  1. 全部家族都 degrade → 仍須 `all_degraded` 的 `approver`+`reason`，**不得一鍵清**
  2. degrade 後該家族成功交付 → degrade 自動失效
  3. `expiry` 缺 → 拒
  4. `--renew-once` 未附 `--renew-of` → 拒
- **風險緩解**：M27、M32、M34。
- **驗證**（可證偽）：`python -m pytest tests/governance/test_debt_degrade.py -q` → rc=0；`result_state == "success"` 的家族走 degrade → rc≠0；attempt 未達上限（< 5）→ rc≠0；六欄缺一 → rc≠0；正常 degrade 後 ledger 顯示該家族不再阻擋清帳；`expiry` 逾期 → round 回 `PARTIAL`；同 `(round, family)` 第二次 degrade（無 `--renew-once`）→ rc≠0；同 `(round, family)` 第二次 `--renew-once` → rc≠0；**同 round 不同 family 各用一次 → 皆 rc=0**（證偽「全域一次」誤設計）；`renew_of` 指向他 round／他 family／未逾期的 degrade → rc≠0；`failed` + 逾期 + `--renew-once` → rc=0 且四條終局至少一條可達。
- **存活至**：永久保留。
- **覆蓋風險**：無。

---

## Phase 4 — 擋門與硬化（依賴：Phase 3）

**完成後系統狀態**：有未清債即拒發開新 round 的 token（含實作派工）；fresh token 在開債後失效；逾期債只能人工留痕放棄；41 類 mutation 全部有常駐探針。

### Task 4.1 — `gate.sh` 債務閘

- **SPEC ref**：Task 4.1　**目標**：有未清債 → 拒發**開新 round 的 token**；同 round retry 放行。
- **輸入**：`scripts/gate.sh` dispatch 分支（現 L435-563）、`scripts/debt_ledger.sh`。
- **輸出**：`gate.sh` 新增 `_check_open_debt()`、`tests/governance/test_debt_gate.py`（新增）。
- **實作要點**（≥3）：
  1. **旁側呼叫，不改既有守衛內部**：新增 `_check_open_debt()`，**不得**改寫 V-A/V-B/V-C/V-M 的內部（已通過 codex 原提出方 nested PoC 複驗）。
  2. **判定極簡**：
     ```
     會開新 round（未帶 --round-id）且 debt_ledger 回報存在任一 OPEN/PARTIAL/EXPIRED_OPEN 債 → 拒發
     帶合法 --round-id（通過 Task 1.3 全部條件）                                    → 放行
     不分討論/實作（憲法級裁決 4）
     ```
  3. **順序寫死**（SPEC 改法④）：`必填欄位檢查 → 債務閘 → _run_completeness_gate → V-C/V-M → high-risk adversarial → review-quorum → template_check → emit → 寫 token`。**落點＝現 `gate.sh:441` 之後、`:452`（`_comp_ran=0`）之前**。
  4. **必須掛 `gate.sh` 本體**（M8）：`gate_check.sh` 有 jq fail-open（L30）與 fresh-token 直接 `exit 0`（L75-77）兩個旁路，只掛 hook 等於沒擋。
  5. **audit 來源＝registry `audit_log_path`，不得讀 `GATE_DIR_OVERRIDE`**（R1 裁定，採 grok／composer 偏好的案 B）：
     ```
     debt_audit = "${DEBT_AUDIT_OVERRIDE}"  if GOVERNANCE_TEST_HARNESS == "1" and 該變數非空
                  else registry.audit_log_path        # 固定 .claude/gate/audit.log
     # 正式路徑不看 GATE_DIR_OVERRIDE —— 它只決定 token 目錄，不得決定債判定
     if [ -n "${DEBT_AUDIT_OVERRIDE:-}" ] && [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
       echo "ERROR: DEBT_AUDIT_OVERRIDE 僅允許 GOVERNANCE_TEST_HARNESS=1" >&2; exit 1
     fi
     ```
     `DEBT_LEDGER_OVERRIDE`（換 ledger 腳本路徑）同樣綁 `GOVERNANCE_TEST_HARNESS=1`。
     **`gate_check.sh` 必須同步**（Task 4.2）——只修 `gate.sh` 不夠，hook 路徑 `gate_check.sh:15-16` 同樣無條件吃 `GATE_DIR_OVERRIDE`。
     **14 檔既有隔離測試的處置**：改為設 `GOVERNANCE_TEST_HARNESS=1` + `DEBT_AUDIT_OVERRIDE=<tmp 空 audit>`，或預置「無債」fixture；**不得**靠「指到空目錄」這條旁路取得放行。
     > **R1 更正（C1／三家全抓：codex P0-05、composer P1-03、grok P0-01）**：v0.1 讓債務閘讀未綁 harness 的 `GATE_DIR_OVERRIDE`，等於正式路徑 `GATE_DIR_OVERRIDE=/tmp/empty` 即可掏空憲法級裁決 4。且 v0.1 §Q-6 稱「SPEC 未涵蓋」為**不實陳述**——SPEC L217 Task 4.1 邊界①原文已寫「`GATE_DIR_OVERRIDE` 指向空 audit → 綁 `GOVERNANCE_TEST_HARNESS=1`」。是 TODO 寫反了 SPEC，不是 SPEC 有洞。
- **修改檔案**（到函式名）：`scripts/gate.sh` — 新增 `_check_open_debt()`；**唯一呼叫點**＝dispatch 分支，必填欄位 `miss` 累加完成（`gate.sh:440` 之後）、`_comp_ran=0`（`gate.sh:452`）之前。新增 `--round-id` 與 `--pending-round-id` 到 `gate.sh:180-199` 的 `while` 解析（**注意 `gate.sh:197` 的 `*) echo "ERROR: 未預期參數"` fail-closed，不加會讓 `committee_run.sh` 透傳直接炸**）。
  > **R1 更正（C4／composer P0-02）**：v0.1 在「修改檔案」寫「置於 `_run_completeness_gate()` 之後」（指函式**定義**位置），在「順序寫死」又寫 L441 後（指**呼叫**位置在 completeness **之前**），兩句字面互斥。現統一：函式定義位置不拘，**呼叫點只有一處且在 completeness 之前**。
- **既有 caller**：`scripts/committee_run.sh:62`、`scripts/dispatch.sh`、Claude 直呼、14 個 governance 測試檔。
- **不可做**：不得新增 `--debt-waived:` 逃生口；不得改寫 V-A/V-B/V-C/V-M；不得只掛 `gate_check.sh`。
- **邊界**（≥2）：
  1. **`DEBT_AUDIT_OVERRIDE` 指向空 audit 且 `GOVERNANCE_TEST_HARNESS=1`** → 空 audit ＝無債放行（**照 SPEC 邊界①的「綁 harness」要求**）；未帶 harness 而設該變數 → fail-closed；設 `GATE_DIR_OVERRIDE` **對債判定完全無效**
  2. `debt_ledger.sh` 缺失/崩潰（rc=2）→ fail-closed 拒發
  3. 多筆 open 債 → 全部列出，任一未清即拒
  4. 本 epic 自身派工同樣受管（無自我豁免）
  5. `EXPIRED_OPEN` → 仍擋，訊息升級為要求 `debt_abandon`
- **風險緩解**：M1、M8、M21。
- **驗證**（可證偽）：`python -m pytest tests/governance/test_debt_gate.py -q` → rc=0；有 OPEN 債時開新 round → rc≠0 且 `.claude/gate/dispatch.token` 未更新（比對 mtime）；同狀態帶合法 `--round-id` → rc=0；**有 OPEN 債時實作 dispatch（帶 `--spec`）→ 也 rc≠0**（憲法級裁決 4 的具名 oracle）；債清後 → rc=0；`debt_ledger.sh` 改名後跑 gate → rc≠0（fail-closed，非放行）；**`GATE_DIR_OVERRIDE=<空目錄>` 而真 audit 有 OPEN 債 → 仍 rc≠0**（C1 的具名反例，證明旁路已封）；`DEBT_AUDIT_OVERRIDE=<空 audit>` 但未設 `GOVERNANCE_TEST_HARNESS=1` → rc≠0。
- **存活至**：永久保留。
- **覆蓋風險**：無。
- **既有測試連動**：§S-5 中 8 個標「綠」的 gate 相關測試檔須在本批逐檔實跑確認（尤其 §S-7 #10b 機械清點的 6 檔 10 處 `pop GOVERNANCE_TEST_HARNESS`），**禁 skip/xfail**。

### Task 4.2 — token ↔ round handoff 與 `debt_epoch`

- **SPEC ref**：Task 4.2　**目標**：①消滅「token 綁 round 但 `round_open` 在 gate 之後才寫」的時序矛盾 ②讓 fresh token 在開債後失效。
- **輸入**：`scripts/gate.sh` token 寫入區塊（L579-587）、`scripts/gate_check.sh:67-79`、B2 出場 gate 量得的 N。
- **輸出**：token 新欄位、`gate_check.sh` 新判定、`tests/governance/test_debt_token_epoch.py`（新增）。
- **實作要點**（≥3）：
  1. **預 mint 交接**：`committee_run.sh` 先 mint `round_id`，以 `--pending-round-id` 傳給 `gate.sh`；token 附 `pending_round_id` 與 `debt_epoch`。**此時不要求 audit 已有 `round_open`**（否則時序死結）。
  2. **不可變 deadline**：token 內寫 `pending_deadline_ts = mint_ts + N`（N 見 B2 出場 gate 量測結果）；判定用 `now > pending_deadline_ts`，**不得用 token 檔 mtime**（`touch` 不得延長；`flock` 等待期間不延長）。此處直接修掉既有 `gate_check.sh:73-77` 的 mtime 判定對本 token 的適用面。
  3. **即刻失效**：出現與本 token `pending_round_id` 相符的 `round_open_failed` → token 立刻失效。
  4. **`debt_epoch` 定義與自污豁免**：計入事件 ＝ registry 中 `in_debt_epoch: true` 者；計算「當前 epoch」時**排除與本 token `pending_round_id` 同一 round 的所有事件**（`round_open` 與 `amendment` **皆**排除，M18/M26）。偽碼：
     ```
     def current_epoch(audit, exclude_round):
         evs = [e for e in parse(audit)
                if registry.debt_events[e.event].in_debt_epoch
                and e.round_id != exclude_round]
         return sha256("|".join(sorted(e.event_id for e in evs)))
     ```
  5. **`gate_check.sh` fresh token 不再直接 `exit 0`**（現況 `gate_check.sh:67-76`）：改為 `debt_epoch != current_epoch(排除自身 round)` **且** 有 OPEN 債 → 擋。總耗時上限 100ms（實測全檔 JSON scan 0.007–0.038s，直接全掃可接受）。
  6. **缺新欄的 legacy token → fail-closed**（R1 裁定，推翻 v0.1 §Q-5）：token 缺 `pending_round_id` / `debt_epoch` / `pending_deadline_ts` 任一 → **擋並提示重跑 `gate.sh`**。僅 `GOVERNANCE_TEST_HARNESS=1` **且** fixture 明示 legacy-read 時放行。既有測試的 token fixture 一律補三欄（**禁 skip 換綠**）。
     > **R1 更正（C2／codex P0-04＋grok P0-02）**：v0.1 提案「缺欄放行、只記 audit」＝永久 fail-open——缺欄若先短路放行，第 5 點的新判定**永遠不會執行**，任何舊格式或手搓 token 在 TTL 窗內都能繼續派工，Task 4.2 目標②直接失效。
  7. **`gate_check.sh` 同步封 `GATE_DIR_OVERRIDE` 旁路**（承 Task 4.1／C1）：債判定的 audit 來源與 `gate.sh` 一致（registry `audit_log_path`，隔離走綁 harness 的 `DEBT_AUDIT_OVERRIDE`）。只修 `gate.sh` 不夠。
  8. **jq fail-open 改 fail-closed**（R1 §Q-7，2:1 多數同意＋吸收 codex 條件）：`gate_check.sh:30` 現為 `command -v jq >/dev/null 2>&1 || exit 0`（無 jq 直接放行），改為 `|| { _append_gate_deny_audit no_jq "$tool_name" unknown; exit 2; }`。**條件（codex 反對票的吸收）**：必須同批新增 **M41** 常駐探針 + 更新 §S-2／§S-3，不得無測收編；SPEC §A 誠實邊界第 4 條同步改為「已閉合」，見 §Q-10。
- **修改檔案**（到函式名）：`scripts/gate.sh` — token 寫入區塊新增三行欄位、新增 `_compute_debt_epoch()`；`scripts/gate_check.sh` — L67-79 改寫為 `_token_fresh_and_epoch_ok()`；`scripts/committee_run.sh` — 傳 `--pending-round-id`。
- **既有 caller**：`gate_check.sh` 由 PreToolUse hook 呼叫（`.claude/settings.json`）；token 由 `gate.sh` 寫、`gate_check.sh` 讀。
- **不可做**：不得用 mtime 判 pending 期限；不得在 `debt_epoch` 計算中納入自身 round 的事件；不得為過測試放寬 100ms 上限而改用抽樣。
- **邊界**（≥2）：
  1. `debt_epoch` 相同 → 放行，零額外摩擦
  2. audit 不可讀 → fail-closed
  3. 既有 287 測試的 token fixture → 依 §S-5 矩陣**補齊三新欄**；缺欄 token 在正式路徑 **fail-closed**（§Q-5 已裁定）
  4. `gate_check` 總耗時 > 100ms → 視為回歸，須優化而非放寬
  5. 執行環境無 `jq` → **fail-closed 擋下並寫 `gate_deny` audit**（改法⑧；原為靜默放行）
- **風險緩解**：M13、M18、M26。
- **驗證**（可證偽）：`python -m pytest tests/governance/test_debt_token_epoch.py -q` → rc=0；預 mint → 寫本輪 `round_open` → 同 token 窗內 check → **必須放行**；同 round 補派寫 amendment → 同 token 仍放行；另開第二筆債 → 必須擋；取得 token → 另開 OPEN 債 → 用該 token 開新 round → 被擋；逾 deadline 無 `round_open` → token 失效；出現 `round_open_failed` → **立即**失效；`touch` token → 不得延長（斷言 `touch` 後仍擋）；`gate_check.sh` 單次耗時 < 0.1s；**只含 `ts=`／`kind=` 的舊格式 token ＋ 另有 OPEN 債 → rc=2**（C2 具名反例）；**PATH 移除 `jq` → rc=2 且 audit 新增一筆 `gate_deny`**（M41）。
- **存活至**：永久保留。
- **覆蓋風險**：無。**但 SPEC §R 硬要求：本 Task 須與 Phase 4 同 commit 一併回退。**

### Task 4.3 — `debt_abandon`：逾期債的高摩擦出口

- **SPEC ref**：Task 4.3　**目標**：TTL 逾期不自動清，改由人工留痕放棄。
- **輸入**：`scripts/debt_clear.sh`、registry `constants.ttl_days`（== 7）。
- **輸出**：`debt_clear.sh --abandon` 子命令、`tests/governance/test_debt_ttl.py`（新增）。
- **實作要點**（≥3）：
  0. **CLI 契約（R2 補；codex R2-P1-10）**：
     ```
     bash scripts/debt_clear.sh --abandon --round-id <id> \
        --reason "<≥20 字>" --approver "<非空>" --remediation-owner "<非空>"
     四欄對應 registry required_fields_per_event.debt_abandon，缺一 → rc≠0
     成功 → stdout 印新 event_id，rc=0；ledger 該 round 轉 ABANDONED（不可逆）
     ```
  1. 欄位依 registry `debt_events.debt_abandon.fields`（`round_id`/`reason`/`approver`/`remediation_owner`）；四欄缺一即拒。
  2. **僅 `EXPIRED_OPEN` 可用**（TTL 依 `constants.ttl_days`）；`OPEN`/`PARTIAL` 未逾期 → rc≠0。
  3. **嚴禁任何形式的自動 clear**：不得有 cron、不得有「ledger 讀到逾期就自動轉 ABANDONED」；ledger 只把狀態標為 `EXPIRED_OPEN`（仍擋），轉 `ABANDONED` 一律要人工事件。
  4. harness 可用短 TTL（`GOVERNANCE_TEST_HARNESS=1` 才認）但**不得**成為 production override。
- **修改檔案**（到函式名）：`scripts/debt_clear.sh` — `_cmd_abandon()`、`_assert_expired()`。
- **既有 caller**：Claude 手動呼叫；`debt_ledger.sh:_round_state()` 消費 `debt_abandon` 事件轉 `ABANDONED`。
- **不可做**：**嚴禁**任何形式的自動 clear；不得讓 `ABANDONED` 再被 clear（不可逆，見 SPEC §N）。
- **邊界**（≥2）：
  1. 未逾期 → 拒
  2. 欄位缺 → 拒
  3. harness 短 TTL 不得成 production override
  4. `ABANDONED` 不得再 clear（且不可逆）
- **風險緩解**：憲法級裁決 5（TTL 7 日、`EXPIRED_OPEN` 仍擋、禁自動 clear）。
- **驗證**（可證偽）：`python -m pytest tests/governance/test_debt_ttl.py -q` → rc=0；未逾期的 OPEN 走 abandon → rc≠0；缺 `approver`/`remediation_owner` → rc≠0；逾期（`now - round_open.ts > 7` 天）且欄位齊 → rc=0 且 ledger 轉 `ABANDONED`；`ABANDONED` 後再 clear → rc≠0。
- **存活至**：永久保留。
- **覆蓋風險**：無。

### Task 4.4 — mutation 探針 + 287 既有測試回歸

- **SPEC ref**：Task 4.4　**目標**：證明閘門非假綠。
- **輸入**：B1–B5 各批已落地的測試檔、SPEC §V 40 類 mutation 表 + R1 新增 M41（共 41 類，見 §S-2）、§S-5 回歸矩陣。
- **輸出**：`tests/governance/test_debt_*.py` 探針補齊、`tests/governance/mutation_red/` 新增案例、全套回歸 receipt。
- **實作要點**（≥3）：
  1. **逐類對表清點**：以 §S-2 的 40 列為 checklist，逐 M-ID 確認「已有一個具名測試會因該變異轉紅」。缺者當批補。**禁憑印象宣稱已覆蓋**——須以「注入變異 → 跑 pytest → 貼具名測試 FAILED 行 → 復原 → 貼 PASSED 行」的 receipt 逐條佐證。
  2. **探針規則**：沿用 `scripts/mutation_probe_check.sh` 規則 1（每個含 `def test_` 的檔案須有 ≥1 `def test_mutation_*`，或行首 `# MUTATION-PROBE: n/a — <非空理由>`）。規則 2（AST 非空心）與規則 3（真跑過）由該腳本機檢。
  3. **287 逐檔矩陣處置**：依 §S-5 十三列逐檔判「真回歸」vs「fixture 契約更新」，**禁 skip/xfail/waiver**。兩個預期轉紅者（`test_family_registry.py`、`test_brief_conformance.py`）已在 B2/B3 處理，本批只複核其斷言未被放寬（`git diff` 逐條檢視斷言行）。
  4. **M7 橫切清點**：`grep -rnE '_OVERRIDE' scripts/*.sh` 列出本 epic 新增的每個 env override（`AUDIT_EVENTS_REGISTRY_OVERRIDE`／`CX_RUN_BIN_OVERRIDE`／`DEBT_LEDGER_OVERRIDE`／`DEBT_AUDIT_OVERRIDE`／`AUDIT_APPEND_EVENT_ID_OVERRIDE`），逐一確認有 `GOVERNANCE_TEST_HARNESS` 綁定 + 有對應探針。
  5. **registry 欄位 ↔ 消費端矩陣（R1 補；C14／codex P1-07，承接 SPEC §A 誠實邊界第 13 條）**：產出一張表，registry 每個 `debt_events.*.fields` 欄位 → 讀取它的腳本與函式 → 對應測試。**任一欄位無消費端 或 任一消費端讀 registry 沒有的欄位 → 紅**。這是 SPEC 說「Phase 0 通過不等於實作正確」的承接點，v0.1 只映射到本 Task 卻沒定義矩陣內容。
  6. **M-ID → 具名測試 → receipt 路徑對照表（R1 補；C13／codex P1-08）**：本 Task 交付一張 41 列的表（M-ID／注入位置／具名測試／`handoffs/run_receipts/<UTC>-p16-m<NN>.log`），**逐列附紅→綠 receipt**，禁以「已覆蓋」一句帶過。
- **修改檔案**：`tests/governance/test_debt_{emit,retry,ledger,clear,supersede,degrade,gate,token_epoch,ttl}.py`、`tests/governance/test_audit_{append,events_registry}.py`、`tests/governance/mutation_red/`。
- **既有 caller**：`scripts/gov_check.sh`、CI `.github/workflows/governance.yml`。
- **不可做**：不得為求測試通過而放寬既有斷言；不得用不可測百分比當驗收（一律列舉具體反例逐條跑）；不得把「未覆蓋」寫成 `# MUTATION-PROBE: n/a` 混過。
- **邊界**（≥2）：
  1. 探針自身失效（空心/偽自證）→ 由 `scripts/mutation_probe_check.sh` 抓（rc≠0）
  2. 既有測試轉紅 → 依 §S-5 矩陣逐檔判定，禁 skip/waiver
  3. 新增 env override 漏綁 harness → M7 探針轉紅
- **風險緩解**：全部 41 類的最終驗收關卡。
- **驗證**（可證偽）：每類 mutation 改壞 → 對應具名測試轉紅；復原 → 轉綠（40 條 receipt）；`python -m pytest tests/governance -q` → rc=0 且 passed ≥ 287（基線 287 + 新增，failed == 0）；`bash scripts/mutation_probe_check.sh tests/governance/test_debt_*.py tests/governance/test_audit_*.py` → rc=0；`bash scripts/gov_check.sh` → rc=0；跑完 `bash scripts/restore_golden_inventory.sh` 還原 golden inventory 副作用。
- **存活至**：永久保留。
- **覆蓋風險**：無。

---

## §Q 待委員裁決的公開問題

### 已於 R1 裁決（三家意見 → 收口，供 R2 複核是否落地正確）

| # | 問題 | R1 裁決結果 | 依據 |
|---|---|---|---|
| Q-1 | SPEC §P 的 Phase 1 內部順序 vs `audit_append.sh` 是唯一寫入點 | **1.4 先做**；且因 1.2 依賴 1.3 的 `debt_roster.sh`，最終次序＝**1.4 → 1.3 → 1.1 → 1.2** | 三家同意 1.4 先；composer P0-01 補正 1.2↔1.3 |
| Q-2 | N 值量測不能跑 60 次真實 CLI | **同意 stub**，但 stub 只換 binary，且 receipt 須含 7 項（含 3 次真實 sanity sample 對照 < 2×） | composer/grok 同意附條件；codex 要求精確定義區間，已收 |
| Q-3 | `governance_tools.json` 的 `mandatory` 欄位 | **只引用 `cmd` 欄，`mandatory` 不當機檢來源** | 三家一致 |
| Q-4 | 量測出的 N 如何落地 | **只留一個 canonical key `pending_deadline_seconds`**，廢 `_provisional` 的消費路徑；守衛加「兩者不得同時被消費端讀取」。**但寫入時機受 Q-8 約束** | codex 反對留兩個常數；composer/grok 同意須升格 SPEC 修訂 |
| Q-5 | 缺三新欄的 legacy token 該擋還放行 | **推翻我的提案 → production fail-closed**；僅 harness + 明示 legacy-read fixture 放行；既有 fixture 補三欄 | 三家一致反對放行（codex P0-04、grok P0-02、composer 部分反對） |
| Q-6 | 債務閘的 audit 來源與 `GATE_DIR_OVERRIDE` | **採案 B**：固定讀 registry `audit_log_path`，隔離走綁 harness 的 `DEBT_AUDIT_OVERRIDE`；`gate.sh` 與 `gate_check.sh` **兩端同步**。**本 epic 修，不另立票**。⚠️ 並更正 v0.1 的不實陳述：**SPEC L217 邊界①早已裁定要綁 harness，非 SPEC 空白** | 三家一致；grok 明確指出我誤稱 SPEC 未涵蓋 |
| Q-7 | 順手修 `gate_check.sh` 無 jq 的 fail-open（V-G） | **納入 Task 4.2**（2:1 多數），但**吸收 codex 的反對條件**：須同批新增 M41 探針並同步 §S-2／§S-3，不得無測收編 | composer/grok 同意；codex 反對無測收編 |

### 歷史裁決紀錄（**全部已閉合**；保留供追溯，勿當未決事項）

> **⚠️ 冷啟動執行端注意**：下表四題**皆已裁決並落地 SPEC v1.2.1／v1.2.2**（見每列「裁決結果」欄）。
> 本表**不是**待辦清單。R5 codex P1-09 指出原標題「仍待裁決」會讓執行端以為 Q-9 未決而重新選擇 `supersedes` 或停工，故改標題並逐列加註落地位置。

| # | 問題 | 我的提案 | 為何要委員裁 |
|---|---|---|---|
| Q-8 | Q-4 要寫入 `constants.pending_deadline_seconds`，但那是**已定版 v1.2＋三家戳記**的 SPEC 所指的 registry。是否須先走 **SPEC v1.2.1 微修 + 三家重戳**才可派 B2？ | 走 v1.2.1 微修（同批把 Q-9／Q-10 一起改），重戳後才派 B2 | 動已戳記的產物屬流程層，不可由起草者自決 |
| Q-9 | **registry 自身矛盾**：`committee_family_degrade.fields` 用 `renew_of`（`audit_events.json:160`），而 `docs.renew_once` 說明文字與 `debt_event_optional_fields` 用 `supersedes`（`:20`、`:56`）。續期指標以何者為準？ | 以**欄位定義 `renew_of`** 為準（守衛 C8 以欄位表為準），並修 `docs.renew_once` 文字 | 兩者皆在已戳記的 registry 內，擇一即改 SoT |
| Q-10 | SPEC 的 §A FACT-RECEIPT 與 §V 矩陣**原文寫「6 檔 9 處」pop harness**，Claude 與三家 R2 實跑均為 **6 檔 10 處**；且 Q-7 若納入，SPEC §A 誠實邊界第 4 條（jq fail-open 範圍外）也不再成立。SPEC 是否同批更正？ | 併入 Q-8 的 v1.2.1 一起改 | SPEC 內含已被實測推翻的事實陳述，留著會誤導後續輪次 |
| **Q-11** | **🔴 SPEC 自相矛盾**：SPEC L35 裁決 2 明列五種禁用主委自報分類訊號（含「brief 是否引用範本」），SPEC L140 Task 1.5 改法正是用它 | **已裁決**：拆 **2a 債務／路由層（全禁）** ＋ **2b 檢查契約層（只准單向加嚴，三條可操作條件）**；Task 1.5 改為**單一 validator + 加法義務**（無分類器 → 無需豁免），行為與測試不變 | **使用者交委員會單獨解釋輪（R3）**；三家考古一致：被禁訊號的 harm model 是「**省略**字串逃債逃檢」，11 輪中不存在「引用以逃檢」。落地＝SPEC v1.2.1 + 本 TODO §0 R-4 + Task 1.5 改法 0/1。reconcile＝`handoffs/reconcile/p16-q11-r3/synth.md` |

> **✅ Q-8／Q-9／Q-10／Q-11 皆已裁決並落地 `docs/P16_COMMITTEE_DEBT_SPEC.md` v1.2.1（2026-07-27）。**
> **剩餘閘門**：SPEC v1.2.1 須經**三家重審 + RECONCILE-STAMP** 才可派實作（v1.2 的舊戳記不自動延續）。

> **⚠️ Claude 自我更正（R2 grok 指出）**：v0.2 的 Task 1.5 改法 0 稱「composer §4 與 grok §4 均獨立判定合規」為**引用過寬**——grok R1 §4 只判過「不拿**產出 marker** 當分類器」，並未替「brief 內範本 token 覆寫 `_bk`」背書。此為本 epic 第三次「把證據拉伸得比實際更強」。

> **R1 未採納的委員意見（逐條交代，非靜默略過）**：
> - **CODEX-R1-P0-01**（Task 1.5 違 R-4）→ **部分不採納**，理由見 Task 1.5 改法 0；要改須先改 SPEC。
> - **COMPOSER-R1-P2-02 後半**（`test_completeness_lock` 應為 3 處）→ **不採納**：SPEC 該列是 `lock`+`_semantic` 兩檔合計（3+1=4），TODO 照抄正確；composer 誤讀為單檔。
> - **CODEX-R1-P1-07 的數字**（7 檔 10 處）→ **檔數不採納**：Claude 實跑為 6 檔 10 處。

---

## §Z 執行端注意（冷啟動必讀）

- **兩輪斷路器**：任何 bug/測試/疑問自己弄 ≤2 輪仍失敗 → 停手回報，交委員會，禁 solo 硬幹。
- **rc 直接取**，禁 `cmd | tail; echo rc=$?`（讀到的是 tail 的 rc）。
- **改檔一律用編輯工具**，禁 `python3 - <<'PY'` 之類 heredoc 字串取代（靜默無動作 + 無 diff 可審）。
- **`pytest tests/governance -q` 約 110 秒**（287 tests）；跑完須 `bash scripts/restore_golden_inventory.sh` 還原 golden inventory 副作用。
- **禁 `git checkout` tracked 檔**（執行端合約 `AGENTS.md`）。
- 產出的每個新腳本收工前跑 `bash -n scripts/<name>.sh` 語法檢查（本 epic 歷史上因未先 `bash -n` 多燒一輪）。
