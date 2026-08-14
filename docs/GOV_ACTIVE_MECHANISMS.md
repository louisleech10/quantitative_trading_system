# 現行治理機制一覽 — 掛在哪、擋什麼、出自哪張票

> **這份回答一個問題**：治理做了這麼多，**現在有哪些是真的在用的**？
>
> 🔴 §二的表格由 `scripts/list_active_mechanisms.sh` **機械生成**，手改會被 `--check` 擋下。
> 其餘章節是人寫的解釋，會漂——**數字與掛載點一律以 §二為準**。

---

## 一、先釐清兩件常被混為一談的事

```
機制「在用」   = 這道檢查現在每次操作都跑，會擋人
票「收案」     = 該票的**全部**驗收條件都達成
```

**沒收案照樣可以掛上使用，而且現在就是這樣。**

最清楚的例子是 `票 B-25`：它的產出端守衛 `factkey_write_guard.sh` 已掛在
`PostToolUse`，在單一個工作階段內就實際擋下十餘次；但該票狀態是**部分完成**，
因為票裡還有**別的部分**沒做完（語意互斥偵測不到、既有散文判準不溯及既往）。

⇒ **機制的部署，不等於票的完工。** 一張票可能包含五件事，做完一件就能掛一件，
但五件全做完才叫收案。

---

## 二、掛載一覽（**機械生成，禁手改**）

> 由 `.claude/settings.json`、`scripts/git_hooks/` 與各呼叫端**實際掃描**導出。
>
> **類別**由封閉檔名樣式判定：`常態檢查`（應被自動路徑呼叫）／`一次性驗證`
> （`verify_*_independent`、`*_selftest`、`test_*`，設計上就不掛）／`工具`。
> ⇒ **「未掛」＋「常態檢查」＝ 真缺口候選**；「未掛」＋「一次性驗證」是正常的。
>
> 🔴 掛載判定以 **basename** 比對——呼叫端常寫 `"${SCRIPT_DIR}/x.sh"`，
> 用相對路徑比對會**偽陰性**。初版即因此把三支已掛的檢查判成「未掛」。

<!-- BEGIN GENERATED: gov-active-mechanisms -->
| 腳本 | 類別 | 掛載點（機械導出） |
|---|---|---|
| `brief_conformance_check.sh` | 常態檢查 | gate gov_check committee_run cx_run  |
| `check_agent_contract_sync.sh` | 常態檢查 | narrow_check_router  |
| `check_decoupling.sh` | 常態檢查 | 未掛 |
| `check_decoupling_phase4.sh` | 常態檢查 | 未掛 |
| `check_doc_anchors.sh` | 常態檢查 | pre-commit  |
| `completeness_check.sh` | 常態檢查 | gate cx_run reconcile_build  |
| `coverage_check.sh` | 常態檢查 | gate  |
| `doc_format_precheck.sh` | 常態檢查 | PostToolUse gov_check  |
| `draft_selfcheck.sh` | 常態檢查 | 未掛 |
| `factkey_write_guard.sh` | 常態檢查 | PostToolUse  |
| `g7_trailer_precheck.sh` | 常態檢查 | commit-msg  |
| `gate_check.sh` | 常態檢查 | PreToolUse  |
| `gen_fact_key_blocks.sh` | 常態檢查 | gov_check  |
| `gov_check.sh` | 常態檢查 | pre-push  |
| `govb1_ghostpath_check.sh` | 常態檢查 | 未掛 |
| `govb1_selfcheck.sh` | 常態檢查 | gate  |
| `govb1_single_source_check.sh` | 常態檢查 | gate  |
| `install_verify_hooks.sh` | 工具 | 未掛 |
| `list_active_mechanisms.sh` | 常態檢查 | PostToolUse  |
| `mutation_probe_check.sh` | 工具 | gov_check  |
| `narrow_check_router.sh` | 常態檢查 | PostToolUse  |
| `plain_docs_guard_selftest.sh` | 一次性驗證 | 未掛 |
| `plain_docs_sync_check.sh` | 常態檢查 | pre-commit gov_check  |
| `precommit_selfcheck.sh` | 常態檢查 | 未掛 |
| `proc_guard.sh` | 常態檢查 | 未掛 |
| `reconcile_cluster_attribution_check.sh` | 常態檢查 | reconcile_build  |
| `reconcile_stamps_check.sh` | 常態檢查 | gate  |
| `review_quorum_check.sh` | 常態檢查 | gate  |
| `session_name_check.sh` | 常態檢查 | committee_run  |
| `spec_fourway_check.sh` | 常態檢查 | 未掛 |
| `status_marker_check.sh` | 常態檢查 | Stop  |
| `template_check.sh` | 常態檢查 | gate gov_check  |
| `test_template_check.sh` | 一次性驗證 | 未掛 |
| `ticket_universe.sh` | 常態檢查 | 未掛 |
| `todo_spec_crosscheck.sh` | 常態檢查 | 未掛 |
| `verdict_filled_check.sh` | 常態檢查 | gate  |
| `verify_b1_independent.sh` | 一次性驗證 | 未掛 |
| `verify_b1fix_independent.sh` | 一次性驗證 | 未掛 |
| `verify_b2_independent.sh` | 一次性驗證 | 未掛 |
| `verify_b4_independent.sh` | 一次性驗證 | 未掛 |
| `verify_hooks_health.sh` | 常態檢查 | 未掛 |
| `verify_mutation.sh` | 常態檢查 | 未掛 |
| `verify_narrowing_consistency.sh` | 常態檢查 | 未掛 |
| `verify_narrowing_oracle_selftest.sh` | 一次性驗證 | 未掛 |
| `verify_pretooluse.sh` | 常態檢查 | PreToolUse  |
| `verify_role_gate.sh` | 常態檢查 | 未掛 |
| `verify_spec_stamp_delta.sh` | 常態檢查 | 未掛 |
| `b49_closure_static_check.py` | 常態檢查 | narrow_check_router  |
| `build_l65_golden_baseline.py` | 常態檢查 | 未掛 |
| `check_decoupling_imports.py` | 常態檢查 | narrow_check_router  |
| `check_doc_manifest_b.py` | 常態檢查 | 未掛 |
| `extract_phase2_expected_flips.py` | 常態檢查 | narrow_check_router  |
| `verification_claim_check.py` | 常態檢查 | pre-commit commit-msg  |
| `verify_audit_chain.py` | 常態檢查 | 未掛 |
| `verify_cgsa_pipeline.py` | 常態檢查 | 未掛 |
| `verify_l1_warmup_requirements.py` | 常態檢查 | 未掛 |
| `verify_l65_inplace.py` | 常態檢查 | 未掛 |
| `verify_nan_poisoning_fix.py` | 常態檢查 | 未掛 |
| `verify_task_provenance.py` | 常態檢查 | gate  |
<!-- END GENERATED: gov-active-mechanisms -->

**重跑**：`bash scripts/list_active_mechanisms.sh --write`

---

## 三、分層解讀（人寫，以 §二為準）

| 層 | 時機 | 代表機制 | 擋什麼 |
|---|---|---|---|
| **產出端** | 每次工具呼叫 | `gate_check.sh`（Pre）、`factkey_write_guard.sh`（Post）、`doc_format_precheck.sh`（Post）、`verify_pretooluse.sh`（Pre）、`status_marker_check.sh`（Stop） | 派工無 token、事實來源漂移、文件格式、無憑據宣稱、狀態標記不誠實 |
| **派工前** | `gate.sh dispatch` | `_check_open_debt`、`review_quorum_check.sh`、`reconcile_stamps_check.sh`、`template_check.sh`、`verdict_filled_check.sh`、`completeness_check.sh` | 委員債未清、quorum 不足、收斂檔無戳記、範本不合規、Verdict 未填、收斂掉項 |
| **收斂節點** | `reconcile_build.sh` | `reconcile_cluster_attribution_check.sh`、`completeness_check.sh --lock` | 群集掉項、逐字保真與 body-hash |
| **commit** | pre-commit／commit-msg | `plain_docs_sync_check.sh`、`verification_claim_check.py`、`g7_trailer_precheck.sh` | 白話說明未同步、訊息有宣稱無憑據、scope 外路徑漏帶 `Governance-Scope` trailer |
| **push** | pre-push | `gov_check.sh`（全套） | 上述總驗＋全套 pytest |

---

## 四、為什麼有些票「做了、在用、卻不能收案」

依產出端覆蓋鐵律與 `S0.2` 三值定義：

> **收案 ＝ 驗收條件全部達成**，且該票的檢查已擋在產出端並登記於
> `docs/GOV_ENFORCEMENT_REGISTRY.md`；擋不了者須具名寫出為什麼。

現況：**61 張票中收案 0 張**、17 張「部分完成」。

🔴 下表已依 `S6.1` 之重審更新——當時逐列重問「這個檢查掛 `PostToolUse` 可行嗎」，
**五列被實跑反例推翻**，其中三列（`B-10`／`B-19`／`B-39`）的檢查**一直都在產出端跑**，
只是登記寫錯。原表因此漏列它們，並把 `B-39` 誤記為「派工前」。

| 票 | 機制在用？ | 為何不能收案 |
|---|---|---|
| `B-25` | ✅ 產出端守衛在跑 | 票內另有三段未閉：語意互斥機械偵測不到、既有散文判準不溯及既往、機制證據登記訊號近零 |
| `B-31` | ✅ 產出端有檢查點 | 🔴 票面明寫**不得說「強制」**——只擋意外不防蓄意 |
| `B-38` | ✅ 產出端在跑 | 委員若沒讀到指示，交件照樣過，等收斂才炸 |
| `B-16` | ✅ 產出端在跑（`SPEC`／`TODO` 檔） | 原條文「散文契約偵測」主幹未做，只做了擴充 A/B/C；寫檔階段刻意**不執行** ASSERT |
| `B-39` | ✅ 產出端在跑（findings 檔） | 跨檔完整性須 lock 與全部來源，屬合理的消費端檢查；群集盲點未閉 |
| `B-10` | ✅ 產出端在跑（D 延伸檔） | 施工面無已知殘留，但狀態與現樹之落差尚未複核 |
| `B-19` | ✅ 產出端在跑（brief 檔） | 檢查深度不足：`R-12`——full path 不驗 `EXPECTED-DELTA` |
| `B-15` | ✅ 派工前在跑（`PreToolUse`）| 殘留是**誤擋率**而非缺掛載；誤擋事件無紀錄 ⇒ 無法量測、改完無法驗證 |
| `B-49` | ✅ 產出端在跑（閉合證據檔） | 🔴 2026-08-14 更新：靜態子集**已前移**（`scripts/b49_closure_static_check.py`，經 `narrow_check_router` 掛 `PostToolUse`）。仍不能收案，因四條具名殘留未閉（見 `docs/GOV_B49_ASBUILT_DELTA.md` §3）；隔離重放依其本質仍留在 pre-push |
| 其餘 8 張 | ❌ 多未掛 | **改法本身未完成** ⇒ 無檢查可掛，非「不想掛」 |

🔴 多數票卡在「**改法本身沒做完**」，不是卡在「機制沒掛上」。
🔴 **「在產出端跑」不等於「該票做完了」**——上表九張全部仍是 `部分完成`。

---

## 五、誠實邊界（不得逾越）

1. **機械對證驗得到「有掛」，驗不到「掛對」。**
   `S4.4` 實例：登記的 hook 確實存在、確實在跑，但它檢查的是**別件事**。
   要驗語意須讀腳本內容，屬 review 職責。

2. **腳本檔頭出現票號，不代表是該票的產物。**
   實例：`plain_docs_sync_check.sh` 註解寫「同 `票 B-23` 紀律」，但它不是 B-23 的產物——
   B-23 標「未開工」是正確的。⇒ **提及 ≠ 產出**。

3. **機械掃描本身也會錯。** §二的判定初版用相對路徑比對，
   把三支已掛的檢查誤判為「未掛」，差點據此宣稱「文件說機器強制但實際沒掛」。
   ⇒ 這類盤點必須附**可重跑指令**，讓結論能被第三方複驗，而不是相信一次掃描。

4. **全部只防意外與遺忘，不防蓄意。** `git push --no-verify` 可繞；
   hook 腳本被掏空仍會通過對證。

5. **豁免不等於完成。** 登記表 20 列中 16 列是豁免——那代表
   「已具名記錄為何掛不上」，不代表那張票做完了。

---

## 六、重跑指令（本檔任何數字過期時，以這些為準）

```bash
bash scripts/list_active_mechanisms.sh --check   # 掛載表是否與實況一致
bash scripts/list_active_mechanisms.sh --write   # 不一致時重生成
bash .claude/tmp/s04_export_delivered.sh         # 已交付票（部分完成 ∪ 收案）
LC_ALL=C jq -r '."governance-ticket-sot".rows[] | .[2]' scripts/fact_keys.json | sort | uniq -c
```

---

## 七、腳本級掛載判定（非票驅動，2026-08-14）

> 使用者原話：「**全部的票和腳本，該掛哪／為何沒掛／能不能掛，可以掛的就要掛上去，
> 只有掛和不掛兩種結果，不掛就要有原因，耗費時間太多也是原因。
> 沒有什麼可能、推理、想看看——你用推理都全錯。不是表格列出，是實際上線。**」
>
> 🔴 本節記的是**腳本**，不是票。它們不進 `docs/GOV_ENFORCEMENT_REGISTRY.md`，
> 因為該表的「對應票」欄由 `S1.1` 封閉集合鎖死，非票標的白名單經集合相等測試
> 鎖為使用者點名的 `G-7`／`測試套件` 兩值；為登記腳本而撬那道鎖，代價大於收益。
>
> 🔴 每一列的判定都附**實測**，不接受讀碼推論。本日推理四次全錯、實測兩次全中。

| 腳本 | 判定 | 依據（實測） |
|---|---|---|
| `check_agent_contract_sync.sh` | ✅ **已掛** `PostToolUse` | 經 `narrow_check_router.sh`，觸發條件＝四源合約檔之一被 Edit/Write。實測 rc=0／約 1 秒 |
| `extract_phase2_expected_flips.py --check` | ✅ **已掛** `PostToolUse` | 同上，觸發條件＝`GOVB0_FRICTION_TODO.md` 或其 fixture 被改。實測 rc=0／0 秒 |
| `check_doc_anchors.sh` | ✅ **已掛** `pre-commit`（非產出端） | 實測全庫 3.61 秒、`--files` 窄跑 3.76 秒 ⇒ **窄化省不到**（成本在建全庫標題索引）。掛 `PostToolUse` 技術上可行，但每次 `.md` 編輯多 3.6 秒，單一 session 的 md 編輯次數即為兩位數 ⇒ 分鐘級純摩擦。改掛 commit 邊界，且只在有 `.md` 進 staged 時才跑 |
| `draft_selfcheck.sh` | ❌ **不掛**（已有裁決，非未做） | 委員會 R4 收斂裁定（`handoffs/reconcile/20260801-gov-amend-r4/synth.md:133`，三家 APPROVED）：「只能是 advisory，**不得作為安全邊界**。把可繞過的字面檢查掛成 gate 是製造程序假綠。」⇒ 掛上去本身違反裁決。理由已寫死於該腳本檔頭 |
| `check_decoupling_imports.py` | ✅ **已掛** `PostToolUse`（2026-08-14 修好卡點後上線） | 經 `narrow_check_router.sh` 之目錄前綴列，觸發條件＝`momentum/` 或 `api/` 被 Edit/Write。實測 1.67 秒／次、帶 `--baseline` 故只擋新增違反。**卡點與修法見下方 §七.1** |

### §七.1 `check_decoupling_imports.py` 卡在哪、怎麼修好的（逐步實測，每步都可重跑）

> ✅ **2026-08-14 已上線。** 本節保留完整診斷路徑——它是「一支腳本掛不上時，
> 卡點常常不在那支腳本」的教科書案例：四層剝下來，前三層都不是它的問題。

canonical Rule 2/3/4 是 `CLAUDE.md` 標為 **Zero Tolerance** 的規則，它的 scanner 卻**不掛**。
理由不是「不想掛」，是四層剝下來以後**掛上去就是紅的**：

1. **現樹 rc=1，但紅因不是解耦違反**——是 `scripts/decouple_allowlist.md`
   缺 grok 的 `RECONCILE-STAMP`（既有兩枚皆 2026-07-14，而 grok 自 07-12 起為正式委員）。
   ⇒ scanner 從那時起 fail-closed 在戳記關卡，**一行程式碼都沒掃過**。
2. **本輪已請 grok 獨立審查並自行戳記**，戳記已落地（body hash 由 grok 自算，與既有兩枚一致）。
3. **戳記仍不被採信**：`verify_task_provenance.py` 的 `check_stamp_provenance` 要求審計中
   有一則指向**被戳記檔本身**的 `committee_output` 事件；而 `gate.sh register-output`
   **只接受 `handoffs/` 內的檔**（實測：對 `scripts/decouple_allowlist.md` 直接 rc=1）。
   🔴 既有兩枚戳記之所以過，是走 `_is_legacy_allowlisted_stamp` 的**豁免**，
   **不是**真的通過 provenance——查 audit 可見 `DECOUPLE-SCAN2` 的 dispatch 事件同樣是 `pending`。
   ⇒ **`handoffs/` 外的受戳記資產，新戳記在現行機制下無法通過 provenance。**
   這是本輪新發現的結構性缺口，未修；**不得**以修改該判準來讓自己過關。
4. **就算戳記通過，掃描本身仍紅**：以函式層注入 verifier 的唯讀探針量得
   R2=1／R3=17／R4=2，共 20 筆（`CLAUDE.md` 記載的「R2=5/R3=12/R4=1」已過期）。
   ⇒ 直接掛上會擋死所有 `momentum/`／`api/` 編輯。

**第 3 步之修法（已做）**：`scripts/gate.sh register-output` 的受管路徑集合由硬編
`handoffs/*` 改為 `handoffs/* ∪ scripts/stampable_artifacts.txt` 之**字面列**
（不接受萬用字元／目錄前綴／`..`，清單壞掉即 fail-closed；缺檔則退回只收 `handoffs/`）。
🔴 **修的是「什麼可以被註冊」，不是 provenance 判定本身**——
`check_stamp_provenance` 一字未改，仍要求有先行 dispatch、hash 相符、戳記格式正確。

🔴 修完第一次仍紅，暴露**第二個洞**：`verify_task_provenance._handoffs_relative`
對不含 `handoffs/` 的路徑**原樣返回** ⇒ 同一個檔用絕對路徑與相對路徑寫永遠比不相等。
實測：`reconcile_stamps_check.sh scripts/decouple_allowlist.md` rc=0，
同一支改傳絕對路徑 rc=1——而該 scanner 正是傳絕對路徑。已改為正規化為 repo 相對。

**已完成的準備**：
`--baseline` 模式（觀測集合 ⊆ baseline 即通過，只擋新增違反）、`scripts/decouple_baseline.txt`
（20 筆，鍵為 `路徑|規則|形式|標的|#序號`——不含行號故位移不失效，含 occurrence 序號
故「同檔同標的再加一個 import」仍判為新增〔`CODEX-R1-P1-05`〕）、
以及 `tests/governance/test_decouple_baseline.py` 10 條（含缺檔 fail-closed、
空 baseline 為最嚴格、以及「baseline 不得順手變成 stamp bypass」的反向確認）。

### §七.2 治理文件能不能封存：**機械判定為 0 份**（2026-08-14）

使用者要求「盤那兩萬行，能搬的搬 `docs/Archived/`，只留票 SoT 那一套」。
盤了：`bash scripts/gov_doc_triage.sh`（四個判準皆機械可導出——fact-key 宿主／
腳本非註解行引用／測試引用／被其他 `.md` 連結）。

**結果：`docs/GOV*.md` 42 份，可封存 0 份。**

第一趟只用「硬引用」判，42 份**全部**卡在「文件連結」；因治理文件彼此大量互連，
故加了不動點（只被同樣可封存的檔連到者仍算可封存，因為整群一起搬時群內連結一起搬）。
**跑完仍是 0 份。**

原因不是技術限制，是**它們就是票表的證據層**。實例：

| 被連的檔 | 連它的是誰 |
|---|---|
| `GOV_B49_ASBUILT_DELTA.md` | `GOV_TICKET_SOT.md`、`HANDOFF.md` |
| `GOV_CRITERIA_REGISTRY.md` | `GOV_TICKET_SOT.md`、`白話說明/接下來要做什麼.md` |

⇒ **票表每列的「還缺什麼」只有一行摘要，細節在那些檔裡。**
搬走等於把要保留的那份表的證據抽掉；而 `check_doc_anchors.sh` 已掛 `pre-commit`，
死連結會當場擋 commit。

**結論：不搬。** 要搬只能同時改寫票表與交接檔裡的引用路徑——那是把證據指標一起搬，
不是清雜訊，收益與風險不成比例。

🔴 **`draft_selfcheck.sh` 曾被誤記為「現樹就是紅的」**——那是拿 `HANDOFF.md` 當標的所致。
它是**草案**自檢（要求檔內有 schema 與 §oracle 表），`HANDOFF.md` 兩者皆無，紅是預期。
⇒ **探測選錯標的，不是樹紅。** 這正是「用推理寫進交接檔」的實例。
