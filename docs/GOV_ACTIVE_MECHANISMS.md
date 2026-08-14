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
| `check_agent_contract_sync.sh` | 常態檢查 | 未掛 |
| `check_decoupling.sh` | 常態檢查 | 未掛 |
| `check_decoupling_phase4.sh` | 常態檢查 | 未掛 |
| `check_doc_anchors.sh` | 常態檢查 | 未掛 |
| `completeness_check.sh` | 常態檢查 | gate cx_run reconcile_build  |
| `coverage_check.sh` | 常態檢查 | gate  |
| `doc_format_precheck.sh` | 常態檢查 | PostToolUse gate gov_check cx_run  |
| `draft_selfcheck.sh` | 常態檢查 | 未掛 |
| `factkey_write_guard.sh` | 常態檢查 | PostToolUse  |
| `gate_check.sh` | 常態檢查 | PreToolUse gate  |
| `gov_check.sh` | 常態檢查 | pre-push gate cx_run  |
| `govb1_ghostpath_check.sh` | 常態檢查 | 未掛 |
| `govb1_selfcheck.sh` | 常態檢查 | gate  |
| `govb1_single_source_check.sh` | 常態檢查 | gate  |
| `install_verify_hooks.sh` | 工具 | 未掛 |
| `mutation_probe_check.sh` | 工具 | gov_check  |
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
| `template_check.sh` | 常態檢查 | gate gov_check committee_run  |
| `test_template_check.sh` | 一次性驗證 | 未掛 |
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
| `check_decoupling_imports.py` | 常態檢查 | 未掛 |
| `check_doc_manifest_b.py` | 常態檢查 | 未掛 |
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
| **commit** | pre-commit／commit-msg | `plain_docs_sync_check.sh`、`verification_claim_check.py` | 白話說明未同步、訊息有宣稱無憑據 |
| **push** | pre-push | `gov_check.sh`（全套） | 上述總驗＋全套 pytest |

---

## 四、為什麼有些票「做了、在用、卻不能收案」

依產出端覆蓋鐵律與 `S0.2` 三值定義：

> **收案 ＝ 驗收條件全部達成**，且該票的檢查已擋在產出端並登記於
> `docs/GOV_ENFORCEMENT_REGISTRY.md`；擋不了者須具名寫出為什麼。

現況：**61 張票中收案 0 張**、17 張「部分完成」。

| 票 | 機制在用？ | 為何不能收案 |
|---|---|---|
| `B-25` | ✅ 產出端守衛在跑 | 票內另有三段未閉：語意互斥機械偵測不到、既有散文判準不溯及既往、機制證據登記訊號近零 |
| `B-31` | ✅ 產出端有檢查點 | 🔴 票面明寫**不得說「強制」**——只擋意外不防蓄意 |
| `B-38` | ✅ 產出端在跑 | 委員若沒讀到指示，交件照樣過，等收斂才炸 |
| `B-16` | ✅ 部分在跑 | 原條文「散文契約偵測」主幹未做，只做了擴充 A/B/C |
| `B-39` | ✅ 派工前在跑 | 完整性只驗附錄逐字，群集盲點未閉 |
| `B-49` | ⚠️ 僅 pre-push | 閉合證據的靜態子集尚未前移到產出端 |
| 其餘 11 張 | ❌ 多未掛 | **改法本身未完成** ⇒ 無檢查可掛，非「不想掛」 |

🔴 多數票卡在「**改法本身沒做完**」，不是卡在「機制沒掛上」。

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
