# 委員文件收斂方法 — 實作 SPEC（v3，三家審+codex 閉合複驗後修）

> 來源 PLAN/診斷：`handoffs/20260722-CONVERGENCE-METHOD-FINAL.md`（三家 CONDITIONAL APPROVE + R1-R6）+ `handoffs/20260722-convergence-spec-review-RECONCILE.md`（三家審 32 findings→17 群集 C1-C17 全收口）　|　日期：2026-07-22　|　對應 TODO：待生成 `docs/CONVERGENCE_METHOD_TODO.md`
> **v2 變更**：收口 v1 三家審 C1-C17（R1 digest 欄/禁 XFAIL/刪 advisory 逃生/R6 水位釘死/gate 掛 completeness/forward-dep/DEGRADE 命名空間/…）。
> **v3 變更**：收口 codex 閉合 3 殘留——C2 逐案 polarity 矩陣(9 機械案全列,M4b 排除)/C7 Oracle④ 去語意 stamp 消 forward-dep/M3 一詞多義釐清(純prose≠空目錄)。grok+composer v2 已 APPROVED(此三處不碰其閉合項)。

## 〇、白話簡述（門外漢版）

**要解的痛**：我（Claude 主委）把多家委員各自寫的審查報告「手動合併成一份」時，憑記憶重打 → **每次掉 ~15 項**（IC reconcile 事故）。害委員多跑幾輪補、浪費 token。

**做法**：把「有沒有掉項」交給一支**笨腳本**（非 AI）機械核對。委員報告改用固定格式標題（像貨物貼條碼 `## GROK-R1-P0-01`），腳本比對「來源所有條碼 vs 我合併稿的條碼」，少一個亮紅。我送委員前先自跑補到 95%+，委員只審「內容有沒有被我講水/降級」（語意層）。

**界線（使用者定死）**：只擋**意外/抄捷徑掉項**，目標第一版 **90-95% 完整**；**不防蓄意偽造**（那需外部 harness+CI，本 SPEC 不做）。不碰 gate 活洞 H1-H7。

專有名詞對照：finding=審查發現；canonical ID=標準條碼；roster=預期委員名單；closure/freeze=來源集合鎖定；mutation test=變異測試（故意改壞看測試會不會抓）；DEGRADED_PENDING=合法降級待補狀態；source digest=來源摘要（檔名+內容雜湊,防錯併/錯源）。

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：中（單一 module 級新工具 `scripts/completeness_check.sh` + governance 測試 + 掛進 gate.sh 裁決路徑）。
- **命中高風險原則**：不命中 (a)(b)(c)(d)——非數值/資料品質、非 momentum↔api 共用路徑、非多 phase 難回退（逐 Phase 可 revert）、非 ML/回測正確性。**但**本工具是**治理正確性**工具，測試宣稱「能抓掉項」→ 依 §V mutation 條件**必附可證偽變異測試**（獨立觸發，與 a/d 無關）。
- RISK-HIT: none
- 命中 (a)/(d)？否 → §G 不適用，移 §N 標 N/A。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（附 receipt，下列 3 條均 Claude/委員實跑）：
  - `FACT-RECEIPT:` `git log --oneline -1 574efba` → `574efba fix(governance): 先修地基——治理 suite 5 紅轉綠 + completeness_check 基線入 repo`（三家複驗 2026-07-22）——地基基線已入 repo。
  - `FACT-RECEIPT:` `pytest tests/governance -q` → `151 passed, 0 failed`（三家複驗 2026-07-22）——治理套件全綠。
  - `FACT-RECEIPT:` 現腳本洞（三家實跑對齊）：symlink 目錄外/跨源同 ID dup/同 ID 改 body/extra synth ID 皆 `RC=0`（漏）；`GROK-01`（缺 ROUND/SEVERITY）`RC=0`；M3 空 ID `RC=1`（Claude+codex+grok+composer 實跑 2026-07-22）——證明「須修成 FAIL」的目標洞真實存在，非假事實。
- **待使用者確認**：無（範圍/90-95%/不防蓄意，使用者已定死於 FINAL §〇）。
- **已確認結果**：`2026-07-22 使用者「commit 地基 + 起 SPEC」「這只是先針對如何將委員會文件整理收齊」`——鎖定收斂整併，不含 gate 活洞。

## §C 約束（引用 + 只列本任務相關）
- 解耦 7 條：只動 `scripts/` + `tests/governance/` + `templates/`，不碰 `momentum/`↔`api/` 邊界。
- 不可違反原則：不弱化既有 gate 斷言（既有「應失敗」測試不可刪斷言/放寬換綠）；不改 audit.log 語意（completeness 讀獨立 sources 目錄）。
- 本任務特別注意：`scripts/gate.sh`（reconcile final/stamp 路徑=掛 completeness 的裁決咽喉，見 Task 3.2）、`scripts/gate_check.sh`（PreToolUse）、`scripts/dispatch.sh`（只寫 roster/lock 快照,不裁決）為既有 caller,改動列同步點且不破現行 token 流程。

## §G Golden / Baseline
- **N/A**——本任務不涉 feature/kline/數值正確性/ML/回測（見 §N）。正確性改由 §V mutation（M1-M9）+ 5 oracle 保證（可證偽性等價於 golden 的「改壞必 FAIL」）。

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）

### Phase 0 — 前置地基（依賴：無）【已完工，commit 574efba】
**Task 0.1 — 修 5 紅 + 單一乾淨腳本**
- 目標：治理套件全綠 + `completeness_check.sh` 收斂單一紅隊加固版。　檔案：`CLAUDE.md`、`tests/governance/test_verify_gate_b5.py`、`scripts/completeness_check.sh`。
- 改法：已完成（去寫死家數→pointer / b5 fixture 補 5 欄 Task / STRICT=1 heading 錨定）。
- **驗證**：`pytest tests/governance -q` → `151 passed, 0 failed`（已達成）。
- **邊界（≥2）**：既有「應失敗」fixtures = `tests/governance/test_verify_gate_b5.py::test_b5_spec_missing_receipt_fails`(~L263)/`::test_b5_todo_missing_fails`(~L295)/`::test_b5_reconcile_missing_stamp_fails`(~L389) 未被動 → 仍正確亮紅（防假綠）；空輸入 SPEC → template_check FAIL。〔C16:改具名測試函式〕
- **存活至**：永久（後續全疊此綠基線）。
- **覆蓋風險**：無。
- 不可做：不刪任何既有「應失敗」斷言換綠。

### Phase 1 — 變異測試先寫紅（依賴：Phase 0）
> **鐵律（FINAL §四.2）**：先寫紅、**確認現在亮紅**、再實作轉綠。**禁 XFAIL 當完成態**（C2）。
**Task 1.1 — 構造 M1-M9 mutation（先亮紅 + 落 red-receipt）**
- 目標：`tests/governance/test_completeness_check.py` 構造 9 變異案並產**紅 receipt** 證明現腳本抓不到。　檔案：`tests/governance/test_completeness_check.py`（新建）+ `handoffs/reconcile/<session>/mutation-red.receipt`。
- 改法：每案建隔離 `tmp_path` 假 session。**M1** 少一整份來源檔；**M2** 合併稿改 finding 內文（body 竄改）；**M3** 委員產物純 prose 無 ID；**M4a** heading 後 body 空/無 `**斷言**`（意外空殼→機械須 FAIL）；**M4b** 假 body+sha 對（蓄意→out-of-scope，只 Oracle④/委員語意，非機械 PASS 門檻）〔C11〕；**M5** 大小寫/缺欄 ID 變體；**M6** 跨源重複 ID；**M7** late 檔 freeze 後到；**M8** 跨 round 舊檔；**M9** README/非 `*-<family>.md` 汙染檔〔C17〕。
- **驗證（可證偽）**：Phase 1 產物=**紅**。禁 `pytest.mark.xfail`；改用**裸 assert 目標 polarity（允許整檔紅，CI 暫 exclude 該 nodeid 至 Phase 3-6 轉綠）**或獨立 red-receipt 腳本，寫入 `mutation-red.receipt`（含每案 `name/cmd/observed_rc/expected_rc_after_impl`）。**逐案 polarity 矩陣（9 機械案全列，非「至少 N」；M4b 明確排除於機械 gate）**：〔C2〕

  | 案 | pre-impl RC(須紅) | post-impl 期望 | 屬機械 gate? |
  |----|----|----|----|
  | M1 少來源 | 0(漏) | ≠0 | ✓ |
  | M2 body 竄改 | 0(漏) | ≠0(Oracle④) | ✓ |
  | M3 純prose無ID | 1(已對) | ≠0(守住不退化) | ✓ |
  | M4a 空殼heading | 0(漏) | ≠0 | ✓ |
  | M4b 假body+sha對 | — | **out-of-scope** | ✗(僅 Oracle④/語意,非機械門檻) |
  | M5 缺欄ID變體 | 0(漏) | ≠0 | ✓ |
  | M6 跨源dup | 0(漏) | ≠0 | ✓ |
  | M7 late檔 | 0(漏) | ≠0 | ✓ |
  | M8 跨round | 0(漏) | ≠0 | ✓ |
  | M9 README汙染 | 0(漏) | ≠0 | ✓ |

  red-receipt 須 assert **全部 9 個機械案**(M1,M2,M3,M4a,M5,M6,M7,M8,M9) pre-impl RC 與 post-期望相反(M3 特例:pre 已 RC=1,斷言「守住不退化 vacuous」)。Phase 3-6 後 `pytest tests/governance/test_completeness_check.py -q` 全 PASS 且 `grep -c xfail` = 0。
- **邊界（≥2）**：M3 純 prose→抽出**空 ID 集合** → 現 `RC=1`（已對,守住不退化 vacuous PASS；此為 prose-no-ID,**非空目錄**——空目錄是 Phase 3.1 邊界,不同案）；M4b 假 body+sha 對 → 機械層**不誤放亦不宣稱抓到**（標 out-of-scope,計入 Oracle④/語意,不當 Phase 完成門檻）。
- **存活至**：永久（迴歸網）。
- **覆蓋風險**：無（測試只增不刪）。
- 不可做：不得為讓 Phase 1 綠而預先實作腳本；不得用 XFAIL 計入完成。

### Phase 2 — ① 委員範本 + canonical ID（R1）（依賴：Phase 1）
**Task 2.1 — canonical finding ID schema（含 source digest）+ 派工 prompt 範本**
- 目標：委員每 finding 用 `## <FAMILY>-<ROUND>-<SEVERITY>-<NN>` 全局唯一 + **四欄**（斷言/碼證/**來源摘要**/正文）。　檔案：`templates/COMMITTEE_FINDING_TEMPLATE.md`（新建）；派工 prompt 引用點白名單=`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` + `docs/MULTI_AGENT_ORCHESTRATION.md` 派工段（禁掃全 repo 改 prose）〔C15〕。
- 改法：ID 正則 `^#{2,6}\s+([A-Z]+)-(R\d+)-(P[0-3])-(\d{2,})\s*$`；FAMILY∈{CODEX,COMPOSER,GROK,CLAUDE,AGY} allowlist。**第四欄** `**來源摘要**: <src_path>#sha256[:12]`（或 harness 注入 `source_digest:`）為機器可讀欄，非語意〔C1〕。DEGRADE 為**第二命名空間**（正則 `^##\s+DEGRADE-[A-Z]+-\d{2,}\s*$`），不進 union completeness 分母，只進 degrade 狀態機〔C9〕。
- **驗證（可證偽）**：`scripts/completeness_check.sh` 對合法 ID 抽對應數量標籤；`GROK-01`（缺 ROUND/SEVERITY）→ invalid `exit≠0`（對應 M5）；跨源同 ID → FAIL（M6）；**缺 `來源摘要` 欄的 P0/P1 finding → exit≠0**（C1 可證偽用例）；severity P0/P1/P2/P3 任一 missing 全 FAIL（不因 P3 豁免）；合法 `## DEGRADE-GROK-01` **不**觸發 invalid-ID FAIL（C9 用例）。
- **邊界（≥2）**：純 prose 無 ID 檔 → collection 判 invalid 不進來源（M3）；同檔重複 ID → FAIL（M6）。
- **存活至**：永久（所有機械檢查前提）。
- **覆蓋風險**：無。
- 不可做：不允許 `UNION-*` 合併改名繞過（合併稿保留原始 ID）。

### Phase 3 — ③ 來源集合鎖定 + gate 掛載（R2）（依賴：Phase 2）
**Task 3.1 — physical per-round 目錄 + closure/freeze + roster 注入 + lock schema**
- 目標：來源集合 = harness 鎖定目錄內容 + 預期 roster，非 argv。　檔案：`scripts/completeness_check.sh`（讀 lock）、`scripts/dispatch.sh`（產 lock 快照）、`handoffs/reconcile/<session>/sources/`。
- 改法：dispatch 時 harness 寫 **`sources.lock`（固定 schema：`version` + `session_id` + `expected_roster[]` + 每源 `{realpath, sha256, family}` sorted + `freeze_ts` + `closure_state`）**〔C12〕；completeness 讀 lock，**禁 argv/env 覆寫**（正式入口 banned，僅隔離測試例外）。拒收：symlink（realpath 出目錄）、子目錄、root 外、freeze 後 late（sha 不符）、非 `*.md`、檔名不匹配 `*-<family>.md`〔C17〕。
- **驗證（可證偽）**：M1 少一份 → roster 對不上 → `exit≠0`；M7 late → sha 不符 → FAIL；`outside-link.md` symlink → 拒收（現版 `RC=0`,須修 FAIL）；M8 跨 round → 目錄隔離不混入；M9 README 汙染 → FAIL；空目錄 → `exit≠0`（非 vacuous）；lock 不存在 → fail-closed 拒發。**缺席狀態機（無第三態）**：`roster 缺檔 ∧ 無合法 DEGRADED_PENDING` → **必 FAIL**（不寫「或降級」軟化）〔C8〕。
- **邊界（≥2）**：目錄空 → `exit≠0`；lock schema version 不符 → 拒發（不猜舊格式）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：**分工鐵律**——笨腳本只管「鎖目錄+跑檢查」窄點；派工/重試/timeout/降級全主委做（閘門只在出口拒「來源對不上」，不接管流程→不死機）。不得把 roster 判定權交回 LLM。

**Task 3.2 — gate.sh reconcile final 路徑掛 completeness（裁決咽喉）**〔C6〕
- 目標：`gate.sh` 在 reconcile **final/收斂 stamp** 子命令**必**呼 completeness_check，否則 Phase 7「exit≠0→拒發」無 caller。　檔案：`scripts/gate.sh`（reconcile stamp 路徑 ~L325-340 加呼叫）。
- 改法：`gate.sh` final/stamp 路徑讀 `sources.lock`（禁 argv）跑 completeness；`RC≠0` 或 `DEGRADED_PENDING` → 拒發 token。dispatch 只寫 lock 快照，裁決單一 gate。
- **驗證（可證偽）**：mock session lock + 缺 ID → `gate.sh` final `exit≠0`；對 `DEGRADED_PENDING` 檔蓋 final → 拒發；完整合法 → PASS。
- **邊界（≥2）**：lock 缺 → 拒發（fail-closed）；completeness 腳本不存在 → 拒發（非放行）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不改 H1-H7 通用 gate 邏輯，只加 convergence-specific 出口〔範圍紀律〕。

### Phase 4 — ② 派工前自我體檢（R3）（依賴：Phase 3）
**Task 4.1 — self-check advisory + immutable 初稿 receipt（write-once）**
- 目標：送委員前自跑補到 95%+，自檢**只 advisory 不可當省委員理由**。　檔案：`scripts/completeness_check.sh`（`--self-check`）+ `handoffs/reconcile/<session>/{first_draft.sha256,coverage.json}`。
- 改法：整併後跑 self-check → 列漏 ID → 補 → 保留 **write-once/append-only 初稿 receipt**（`first_draft.sha256` + `coverage.json{missing_ids[],draft_sha256,id_coverage}`）〔C13〕；最終稿由**獨立出口重跑**（非自檢那次）；績效用 **post-review residual** 非 self-check PASS。分離 `ADVISORY_MISSING`（不阻塞，exit 0）vs 執行/輸入錯誤（exit≠0，不吞）〔C13〕。
- **驗證（可證偽）**：`test -f first_draft.sha256 && sha256sum -c` 通過；receipt 含 `missing_ids/draft_sha256/id_coverage`；**回寫初稿 receipt → 篡改測試須 FAIL**（write-once）；刪 receipt/改 missing 列表 → 下游獨立出口仍 FAIL（證明不靠自檢 PASS）；self-check 輸入失敗 → `exit≠0`（不當 advisory 吞）。
- **邊界（≥2）**：自檢 100% 也不得跳委員語意審；委員 charter 禁列漏 ID（只審語意，避免退化成②備援）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得用 self-check PASS 當「省一家委員」理由（道德風險防線）。

### Phase 5 — ⑤ 降級 SOP（R4，防重蹈 H3）（依賴：Phase 3，∥Phase 4）
**Task 5.1 — DEGRADED_PENDING 狀態機（非 waived 字串）**
- 目標：委員 timeout/死機 → 合法降級進 log，不卡死、不隨手 skip。　檔案：`scripts/completeness_check.sh`（degrade 狀態）+ `scripts/gate.sh`（拒對 DEGRADED 蓋 final,見 Task 3.2）。
- 改法：**禁 `waived:/skip` 字串**；降級輸出 = `DEGRADED_PENDING`（非 0 final,不可蓋 final stamp）；**P0/P1 不得 waiver**；**min_families≥2 硬下限**（低於→硬停）；缺席家族須顯式 `## DEGRADE-<FAM>-01`（第二命名空間,C9）指向 degrade event；須 receipt+獨立批准+expiry+補跑責任人；連續 2 輪同家族降級→升級使用者（AskUserQuestion 阻塞）。
- **驗證（可證偽）**：grok 缺席 ∧ 綜合無 `## DEGRADE-GROK-01` → FAIL；`min_families=1` → 硬停 `exit≠0`；`DEGRADED_PENDING` 檔跑 `gate.sh` 蓋 final → 拒發；P0 missing 試 waiver → 拒；合法降級（2 家+DEGRADE 事件+receipt）→ RC=DEGRADED_PENDING（非 0）。
- **邊界（≥2）**：合法降級 → 往下（非 final）；非法（靜默剔除/skip 字串）→ FAIL。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不提供任何 `--skip-completeness`/`ALLOWLIST`/`COMPLETENESS_ADVISORY_ONLY` 逃生口（H3 實證任何 bypass 必被當正規逃脫）〔C3〕。

### Phase 6 — 驗收 5 oracle + R6 水位量測（R5+R6）（依賴：Phase 2+3+5）〔C7:收窄依賴〕
**Task 6.1 — 5 獨立 oracle + retrofit canonical ID 量 90%**
- 目標：驗收拆 5 可證偽 oracle，並先補歷史產物 canonical ID 才量水位。　檔案：`tests/governance/test_completeness_check.py`（oracle 分組）+ `scripts/replay_convergence_coverage.sh`（回放）+ `handoffs/reconcile/<session>/coverage.json`。
- 改法：**Oracle①** ID completeness（synth∩union）；**②** invalid/dup/unknown 拒收；**③** closure/late/round 邊界；**④ body hash（純機械,byte 級偵測錯併/降級,不含語意判定）**——委員語意 stamp 屬 Phase 7,**Oracle④ 不依賴 Phase 7 產物**（消除 v2 forward-dep;M4b 蓄意假 body 由 Phase 7 語意層裁,Oracle④ 只做 body-hash 機械對比不宣稱抓到 M4b）〔C7〕；**⑤ post-review residual** = `|union_ids \ committee_accepted_ids|`，委員審後仍缺 ID → FAIL〔C10〕。
- R6：**回放清單寫死**（≥2 真實 handoff path，本 SPEC 鎖 `handoffs/20260722-ic-map-WHOLEMAP-v2.md` + `handoffs/20260722-pipeline-design-review-UNION.md`；禁順手改其他歷史委員文）〔C4/C5〕；retrofit **只允許新增 `+## FAM-R1-Pn-NN` heading 行 + digest 欄，finding 正文 strip-ID 後 hash 不變**（非整檔 byte-identical）〔C5〕；分母 `id_coverage=|synth∩union|/|union|`（非空守衛）+ session JSON schema（`{session,union_size,synth_size,coverage,p0p1_missing[]}`）；**P0/P1 missing 獨立 hard gate（不被比例稀釋）**；PASS 下限 90%。
- **驗證（可證偽）**：codex 現洞回歸——「同 ID 改 body」「extra synth ID」「跨源 dup」現皆 `RC=0`（漏），實作後各對應 oracle 亮對極性；回放 2 檔 retrofit 後 `id_coverage` 可算非 vacuous（現無 canonical ID=vacuous,故先 retrofit）；某輪含 P0 missing 但總 92% → 仍 FAIL（P0 不稀釋）。
- **邊界（≥2）**：分母為 0（union 空）→ 不算 PASS（守衛）；retrofit 後 finding 正文 strip-ID hash 與原一致。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得用 aggregate 比例掩蓋 P0/P1 缺漏；不得改回放目標檔正文語意。

### Phase 7 — ④ 委員語意審 charter（依賴：Phase 2+3+6）
**Task 7.1 — 委員語意審範本 + fresh=NONE 收斂**
- 目標：機械擔完掉箱後，委員只審「講水/降級/錯併」語意層 → append stamp。　檔案：`templates/COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md`（新建）。
- 改法：charter 明訂委員只審語意、**禁列漏掉的 ID**（那是②的活）；fresh review = NONE 新 finding → 收斂蓋章。順序=機械層 PASS（Task 3.2 gate）在前，語意 stamp 在後。
- **驗證（可證偽）**：`grep -c "禁列.*ID\|只審語意" templates/COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md` ≥1（存在性 smoke）；**主驗證（行為 oracle）**：造「機械層 `exit≠0` 之下委員試蓋 final stamp」→ `gate.sh` final 拒發（`exit≠0`，具名 fixture `test_semantic_stamp_after_completeness`）〔C14〕；一輪 fresh=NONE（0 新 finding）→ 允許 final stamp。
- **邊界（≥2）**：機械層未 PASS → 委員不得蓋 final（順序不可逆）；委員產出只列 missing ID 無語意 → charter 判非法。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：委員不得代替機械層找掉 ID（防退化）。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：本工具測試**宣稱能抓掉項**（驗正確性）→ **必附可證偽 mutation**（引 `docs/TEST_DESIGN_CHARTER.md`）。M1-M9（Phase 1）即 mutation 集；每案「改壞→必 FAIL」，**先紅（禁 XFAIL）後綠**。
- 測試層級：單元（ID 正則/severity/digest）、整合（目錄鎖+lock+roster+gate 掛載）、mutation（M1-M9）、邊界。可獨立 `pytest tests/governance/ -q` 跑，不需 run_api.py。
- **防假綠**：diff 既有 governance 斷言，不放寬/刪除換綠；既有「應失敗」fixtures 保持紅；Phase 1 結束時 `xfail` 標記數=0。
- **邊界目錄**（打勾對應 Task）：空目錄=無檔（3.1,**≠M3**）✓ / M3 純prose無ID（1.1）✓ / 空殼 heading（M4a）✓ / 蓄意假 body-out-of-scope（M4b/Oracle④）✓ / 缺欄 ID 變體（M5）✓ / 跨源重複 ID（M6）✓ / late 檔（M7/3.1）✓ / 跨 round（M8/3.1）✓ / symlink 出目錄（3.1）✓ / README 汙染（M9/3.1）✓ / 委員缺席降級（5.1）✓ / 初稿 receipt 篡改（4.1）✓。

## §R 回退
- 每 Phase 獨立 commit 可單獨 revert；本 SPEC 純新增 `scripts/completeness_check.sh` 邏輯 + `scripts/replay_convergence_coverage.sh` + `tests/governance/` + `templates/` + `gate.sh` convergence 出口，不改數值路徑 → 一鍵回退無下游污染。
- Phase 3-5 為行為性閘門：以 completeness 讀 lock 的入口為切換點，lock 不存在時 fail-closed（拒發而非放行）。**回退唯一路徑 = `git revert` 該 Phase commit**；**不提供正式 advisory-only 逃生口**〔C3〕（對照實驗用 flag 僅允許 `tests/governance/` 隔離 env，正式 `gate.sh`/dispatch 路徑拒 `COMPLETENESS_ADVISORY_ONLY`）。驗過即 ON，不預設關閉已驗證閘門。
- mutation/oracle FAIL → 不 merge。

## §N N/A 登記（被省略的必填段，逐一標理由）
- **§G Golden：N/A** —— 治理/文件收斂工具，不碰 feature/kline/數值/ML/回測；無數值 baseline；正確性由 §V mutation（M1-M9）+ 5 oracle 保證（「改壞必 FAIL」等價 golden）。
- 其餘必填段（§RISK/§A/§C/§P/§V/§R）均已填。

## §範圍與誠實邊界（承 FINAL）
- **只做**：意外/抄捷徑掉項防護，目標 90-95%。**不做**：防蓄意偽造（dummy 假 body/改 lock/async 偽凍結）——需外部 harness 全掌控 control plane + CI protected check，本 SPEC 明確延後（M4b 標 out-of-scope 即此界）。**不碰**：gate 活洞 H1-H7（獨立 backlog；Task 3.2 只加 convergence-specific 出口,不改通用 gate）。
- 本 SPEC = Claude 起草 v2（已收三家審 C1-C17）；**動工前須原提出方複驗閉合**（章程 §B8；codex REJECT 尤須 codex 重跑確認 C1/C2/C3/C4/C7 五 P0 群集關閉）+ RECONCILE-STAMP（實作者不自審）。未過閉合不動工。
