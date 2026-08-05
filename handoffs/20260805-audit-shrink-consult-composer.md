# AUDIT-SHRINK-CONSULT — Composer 諮詢產出

**task-id**: AUDIT-SHRINK-CONSULT  
**family**: composer  
**brief**: `handoffs/20260805-AUDIT-SHRINK-CONSULT-BRIEF.md`  
**date**: 2026-08-05

---

## Verdict：可派工（線 C 先做機械化消費者盤點＋熱路徑隔離；禁重跑 `audit_archive_legacy.sh` 白名單分流）

本輪為諮詢，非 SPEC/TODO reconcile；以下 findings 聚焦 brief §0 前提與主委已發生事故的根因鏈。

---

## COMPOSER-R13-P0-01

**斷言**: brief 稱「20 個消費者」與當前 repo 實測不一致；若以 `grep -rln 'audit\.log' scripts/` 計為 **17**，若以 `grep -rln 'audit\.log\|audit_log_path' scripts/` 計為 **23**（含 registry 驅動讀者）。

**碼證**:

```bash
grep -rln 'audit\.log' scripts/ | wc -l
# → 17

grep -rln 'audit\.log\|audit_log_path' scripts/ | wc -l
# → 23
```

audit.log 自身亦記載「registry驅動讀者8處與硬編audit.log讀者9處」（行 ~31549），與 17 接近、非 20。

**來源摘要**: handoffs/20260805-AUDIT-SHRINK-CONSULT-BRIEF.md#sha256:pending

[MAJOR] 信心度=High；消費者盤點若基於過時數字會漏改 `write_sources_lock.sh`／`audit_append.sh` 等 registry 讀者，重演主委只驗 `debt_ledger` 的失誤。  
**RECHECK**: 上列兩條 grep，對照下文 §1 表。

---

## COMPOSER-R13-P0-02

**斷言**: `audit_archive_legacy.sh` 白名單分流在「只驗 debt_ledger」時可綠，但必然破壞 `verify_task_provenance`／`reconcile_stamps_check`（需 `committee_dispatch`），且違反 `agent_postflight.sh` append-only 行數紅線。

**碼證**: brief 已記錄還原事故；`audit_events.json` 將 `committee_dispatch` 列於 `non_debt_legacy_events`（非 debt 白名單）。`agent_postflight.sh:45-52` 行數減少即 FAIL。

**來源摘要**: scripts/audit_events.json#sha256:pending

[BLOCKING] 信心度=High；任何「只留 debt 四事件」封存方案在當前消費者集合下不安全。  
**RECHECK**: 讀 `scripts/audit_archive_legacy.sh` 白名單來源 + `verify_task_provenance.py:99` 事件過濾。

---

## COMPOSER-R13-P1-01

**斷言**: brief 稱 latency 測試「冷啟約 287ms／門檻 100ms 紅」與本機 2026-08-05 實跑不一致；結構性 O(N) 風險仍成立，但當前環境可能已綠。

**碼證**:

```bash
source venv/bin/activate
pytest tests/governance/test_debt_gate.py::test_gate_check_latency_under_100ms -q -s --tb=line
# gate_check_latency receipt: cold_ms=71.3 second_ms=74.4
#   samples_ms=[73.4, 71.3, 68.2]
#   real_audit_lines=34497 real_audit_bytes=2096467
#   cutoff_override=2099-01-01T00:00:00Z
# PASSED
```

**來源摘要**: tests/governance/test_debt_gate.py:409#sha256:pending

[MAJOR] 信心度=Medium；100ms 門檻出處明確（`docs/P16_COMMITTEE_DEBT_SPEC.md` Task 3.1），但「現在就紅」非本機必要前提。  
**RECHECK**: 同上 pytest；若需重現紅，在較慢 runner 或更大 audit 上重跑。

---

## COMPOSER-R13-P1-02

**斷言**: brief 稱 audit.log「34,479 行」已過時；實測 **34,497 行**，其中 **3,542** 行 JSON、**30,955** 行非 JSON（legacy 純文字／多行紀錄），熱路徑仍須掃過全部行。

**碼證**:

```bash
wc -l .claude/gate/audit.log
# → 34497

grep -c '^{' .claude/gate/audit.log
# → 3542

awk 'BEGIN{j=0;t=0} /^\{/{j++} {t++} END{print "total="t,"json="j,"non_json="t-j}' .claude/gate/audit.log
# → total=34497 json=3542 non_json=30955
```

**來源摘要**: .claude/gate/audit.log#sha256:pending

[MAJOR] 信心度=High；瘦身若只刪 JSON 而留散文，I/O 仍 O(總行數)；若刪散文則觸發 postflight 行數紅線。  
**RECHECK**: 上列三命令。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 證據 |
|------|------|------|
| 20 個消費者 | **部分假** | 實測 17（字面）或 23（含 registry）；見 COMPOSER-R13-P0-01 |
| latency 現在就紅 | **環境依賴** | 本機 cold 71ms 綠；brief 287ms 未在本輪重現 |
| 多數消費者只需點查詢 | **部分真** | 語意上多為 task_id／session_name 點查，但實作皆先全檔掃描（見 §1） |
| cutoff_ts 可減讀檔量 | **假** | `_debt_ledger_core.py:84-123` 仍對全檔 `json.loads`；cutoff 只過濾債務語意 |
| 100ms 門檻無依據 | **假** | `docs/P16_COMMITTEE_DEBT_SPEC.md` Task 3.1 明文 |

---

## §1 消費者對照表（生產路徑）

說明：**讀**=執行時讀取 audit.log（或 registry 解析的同檔）；**寫**=僅 append。  
「歷史範圍」= 該消費者實作實際掃描範圍，非理想語意。

| # | 程式 | 讀/寫 | 需要的事件型別 | 歷史範圍 | 點查 vs 全量 |
|---|------|-------|----------------|----------|--------------|
| 1 | `scripts/gate_check.sh` → `_debt_ledger_core.py` | 讀 | `committee_round_open`, `committee_family_result`, `committee_debt_clear`, `debt_abandon`（debt 白名單） | **全檔**每行 `{`→`json.loads`；序號連續性用**全歷史** debt 事件；`has_open` 語意僅 post-cutoff | 全量掃描（熱路徑，每次 PreToolUse） |
| 2 | `scripts/debt_ledger.sh` | 讀 | 同上（委派 core） | 同上 | 全量 |
| 3 | `scripts/gate.sh` `_task_has_dispatch` | 讀 | `committee_dispatch` | 全檔至命中 `task_id` | 語意點查、實作全量 |
| 4 | `scripts/gate.sh` `_check_open_debt` | 讀 | 同上 #1 | 委派 debt_ledger | 全量 |
| 5 | `scripts/verify_task_provenance.py` | 讀 | `committee_dispatch`, `committee_output` | 全檔 JSON 行 | 語意點查 `task_id`／`output_path`；實作先載入全部事件 |
| 6 | `scripts/verification_claim_check.py` `_committee_registered_files` | 讀 | `committee_dispatch`, `committee_output`（`sources` 豁免另含 `committee_family_result`） | 全檔 JSON 行 | 建索引式全量掃描 |
| 7 | `scripts/reconcile_stamps_check.sh` | 讀（間接） | 經 #5 同型別 | 同 #5 | 同 #5 |
| 8 | `scripts/review_quorum_check.sh` | 讀 | `committee_dispatch` | `grep` 全檔 | 語意依 prefix 過濾；I/O 全量 |
| 9 | `scripts/reconcile_build.sh` | 讀 | `committee_round_open` + 同 round 的 `committee_debt_clear`／`debt_abandon` | 全檔 JSON 行 | 語意 `session_name`／`round_id` 點查 |
| 10 | `scripts/write_sources_lock.sh` | 讀 | 同 #9 | 同 #9 | 同 #9 |
| 11 | `scripts/audit_append.sh` | 讀+寫 | debt 四事件 + legacy 三事件；寫入時掃 `event_id` 唯一 | `_next_seq_locked`／`_scan_session_locked`：**全檔** | 每次 append 全量 |
| 12 | `scripts/cx_run.sh`／`committee_run.sh` | 寫（經 append） | debt／family_result | — | — |
| 13 | `scripts/dispatch.sh`／`gate.sh` dispatch | 寫 | `committee_dispatch` | — | — |
| 14 | `scripts/gate_check.sh` `_append_gate_deny_audit` | 寫 | `gate_deny` | — | — |
| 15 | `scripts/agent_preflight.sh` | 讀 | 不解析事件；**整檔**行數+sha256 | 全檔 | 完整性快照 |
| 16 | `scripts/agent_postflight.sh` | 讀 | 不解析事件；行數 + 前綴 sha | 全檔（前綴） | append-only 守衛 |
| 17 | `scripts/mutation_probe_check.sh` | 寫 | 非 JSON 純文字行 | append only | 不讀 |
| 18 | `scripts/register_legacy_committee_files.sh` | 寫 | `committee_output` | — | — |

**非 `audit.log` 消費者（brief 易混淆）**：`run_with_receipt.py`／`verify_audit_chain.py` 預設讀 `verify_audit.log`，不計入上表。

**事件型別分佈（實測）**:

```bash
grep -oE '"event": "[^"]+"' .claude/gate/audit.log | sort | uniq -c | sort -rn
# 1358 committee_dispatch
#  722 committee_output
#  365 committee_family_result
#  200 committee_round_open
#  161 debt_abandon
#   38 committee_debt_clear
# （gate_deny 格式為 "event":"gate_deny" 無空格，另計）
grep -c '"event":"gate_deny"' .claude/gate/audit.log
# → 698
```

---

## §2 可行瘦身方案比較

| 方案 | 作法 | 優點 | 風險 | 需改消費者？ |
|------|------|------|------|--------------|
| **(a) 依事件型別分流** | active 檔只留熱路徑事件；dispatch/output 進 `audit-provenance.log` | 熱路徑變小 | **已證明不安全**（主委事故）；`verify_task_provenance`／`reconcile_stamps`／`verification_claim_check`／`review_quorum`／`gate.sh register-output` 皆假設同檔 | **是，≥6 處** + registry `audit_log_path` 語意分裂 |
| **(b) 依時間分流 active+archive** | 新事件寫 active；舊事件整檔移 archive | 符合「面向未來」敘事 | 序號連續性需**全歷史** debt 行；provenance 需**全歷史** dispatch；`agent_postflight` 行數不可減 | **是**；且須新雙讀 API，禁「記得讀 archive」 |
| **(c) 建索引、檔案不動** | sidecar：`task_id→offset`、`max_debt_sequence`、`has_open` | 不改 append-only 語意；熱路徑 O(1) 讀 tail/索引 | `gate_check.sh:118-120` 明確拒絕無完整性保護的 `.has_open_idx`（毒化風險） | **是**（`gate_check`/`_debt_ledger_core`/`audit_append`）；索引須與 append **原子**更新 |
| **(d) 只讓 gate_check 熱路徑不讀全檔** | 維護受保護的 `has_open` 快取或 tail-scan | 直接解 B3 latency 壓力 | 與 SPEC「禁用未綁 cutoff 的 sidecar 快取」衝突；須證明不失效於 deny 追加 | **小**（主要 `gate_check`+`audit_append`） |
| **(e) 壓縮非 JSON 散文行** | 將 30,955 行 legacy 文字遷到唯讀 archive，active 只留 JSONL | I/O 從 ~2.1MB 降到 ~JSON 體積；語意消費者幾乎只認 `{` | **破壞 postflight 行數/sha 契約**；git 追蹤的 audit.log 歷史語意變更 | **是**（preflight/postflight + 治理測試） |
| **(f) 雙檔制（推薦方向）** | `audit.jsonl`（機器）+ `audit.human.log`（散文，可選）；registry 指向 jsonl | 關注點分離；熱路徑只讀 jsonl | 遷移一次性成本；須機械保證所有讀者改綁 registry | **是，但一次性機械化** |

**結論**：在「不接受靠紀律維持」前提下，**(a) 白名單封存不可再做**；**(c)+(d)** 是線 C 正路；**(e)** 只有連同 postflight 契約一起改才有意義。

---

## §3 風險與消費者改動需求（對應 §2）

1. **債務序號**：`_debt_ledger_core.py:133-150` `assert_seq_continuity` 掃**全歷史**白名單 debt 事件 → 不可刪任一 debt JSON 行（含 pre-cutoff）。
2. **Provenance**：`verify_task_provenance` 無 cutoff → 非 legacy-allowlist 的 `committee_dispatch` **永久**需在機器可讀路徑。
3. **完整性守衛**：preflight/postflight 把「行數單調遞增」當安全屬性 → 任何物理刪行都需先改契約與測試。
4. **索引／快取**：若做 sidecar，必須 (i) append 時同步更新 (ii) 校驗和或 HMAC (iii) 缺失時 fail-closed 回全掃 — 否則重現 B/C 類 false-green。

---

## §4 「面向未來」下仍須機器讀的歷史

依使用者「只考慮以後、不溯及既往」**與**現行腳本契約（非理想世界）：

| 類別 | 是否仍須機器讀 | 理由 |
|------|----------------|------|
| 全歷史 **debt 四事件** JSON | **是** | 序號連續性全歷史掃描 |
| 全歷史 **`committee_dispatch`** | **是** | stamp/adversarial provenance；僅 `LEGACY_STAMP_ALLOWLIST` 極少數可豁免 |
| **`committee_output`**（已註冊路徑） | **是** | `verification_claim_check` committee registry |
| **`committee_family_result`** | **視路徑** | 一般 provenance 不讀；`sources/` 豁免時讀 |
| **`gate_deny`** | **否（當前）** | 無生產讀者；僅測試／稽核 |
| **30,955 行非 JSON 散文** | **否（語意）／是（I/O）** | 無消費者解析內容，但全檔掃描仍讀過 |
| **pre-cutoff 且已 CLOSED 的 round** | **債務語意否／序號是** | cutoff 後不參與 `has_open`，但行不可刪 |

**可封存且當前腳本不要求機器讀的**：無 — 在 postflight append-only 與全檔 sha 下，**物理刪任何行**都需改契約。能做的是**新事件寫入較小檔** + **舊檔唯讀掛載**，而非靜默刪除。

---

## §5 低風險第一步 vs 完整解（線 C）

### 現在就能做（讓 B3 推得上去）

1. **凍結 `audit_archive_legacy.sh`** — 標記 DEPRECATED，CI/governance 加「active audit 行數不得單調減」探針已有（postflight）；禁止再跑白名單分流。
2. **機械化消費者盤點測試** — 新增 governance 測試：`audit_events.json` `hardcode_scan_exemptions` 鍵集合 == 實際讀 audit 的腳本集合（防再漏 `committee_dispatch`）。
3. **記錄 latency receipt 基線** — 在 `test_gate_check_latency_under_100ms` receipt 旁附 `json_lines`／`non_json_lines`（已可從測試印出擴充），作為線 C 前後對照，**不放寬 100ms**。

以上 **不改讀者行為**，風險最低；不解 O(N)，但防止再犯主委事故。

### 完整解（線 C，第 0.5 批）

推薦組合：**(f) JSONL 分離 + (c) 受保護索引**：

1. 新事件只 append `audit.jsonl`（或現檔但禁止新非 JSON 行）。
2. `audit_append.sh` 在持鎖 append 時原子更新：`max_sequence`、`has_open`、`task_id` Bloom/稀疏索引。
3. `gate_check.sh` 熱路徑：讀索引 O(1)；索引損壞 → fail-closed 全掃（慢但正確）。
4. `verify_task_provenance`：改讀 `task_id` 索引或二分 offset，禁止全檔 `read_text`。
5. 散文遷 `archive/audit-human-*.log`（唯讀）；**修訂** preflight/postflight 為「jsonl 單調 + 可選 archive 指紋」，而非整檔行數。

預估改動面：registry、`audit_append.sh`、`_debt_ledger_core.py`、`gate_check.sh`、`verify_task_provenance.py`、`verification_claim_check.py`、`agent_{pre,post}flight.sh` + 對應 governance 測試。

---

## 建議的下一步

1. **立即**：否決任何「只驗 debt_ledger 就封存」方案；採 §5 低風險三步。
2. **線 C SPEC**：以 **(f)+(c)** 寫任務，驗收含 (i) 全消費者契約測試 (ii) latency receipt (iii) 故意刪 `committee_dispatch` 必紅的 mutation。
3. **勿**放寬 100ms；若持續紅，優先削 **30,955 非 JSON 行** 的 I/O（方案 e/f），而非弱化 gate。

---

## FINDINGS_COUNT: 4

---

## 收尾報告

```
ASSUMPTIONS_VERIFIED:
  - 消費者計數（17/23）、行數（34497）、JSON/非JSON（3542/30955）、事件分佈、latency receipt（cold 71.3ms）均實跑
  - _debt_ledger_core 全檔掃描與序號全歷史：讀碼 + time ~40ms
TESTS_RUN:
  - pytest tests/governance/test_debt_gate.py::test_gate_check_latency_under_100ms -q -s → PASSED
  - grep/wc/awk 盤點命令見上文 RECHECK
FAILURES_SEEN: none（latency 本輪綠；brief 稱紅未重現）
SCOPE_CHANGES: none（禁改碼）
NUMERIC_OR_SCHEMA_IMPACT: none
```

**產出檔**: `handoffs/20260805-audit-shrink-consult-composer.md`

STATUS: DONE
