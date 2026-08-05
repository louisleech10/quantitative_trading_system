# GOVB0 B0+B1 Code Review — composer

**家族**: composer  
**task-id**: `GOVB0-B0B1-REVIEW`  
**受審 commit**: `596fcb4`（`feat(governance): 第 0 批 B0+B1 實作完成`）  
**日期**: 2026-08-05

RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:596fcb46c7b1d831bcc05bcf19f0be074c5e492c task:GOVB0-B0B1-REVIEW

---

## Verdict：B0+B1 驗收通過，可進 B2

FINDINGS_COUNT: 0（BLOCKING=0，MAJOR=0，MINOR=0）

---

## §0 前提宣告

### fact-verified（本委員實跑）

| 宣稱 | 複驗 |
|---|---|
| 測試 701→715 | `pytest tests/governance -q` → **715 passed in 232.89s**，rc=0 |
| 既有測試檔零改動 | `git diff 596fcb4^..596fcb4 --name-only -- tests/governance/` 僅新增 snapshot／語料／`test_gate_deny_fields.py`；排除後無既有檔 diff |
| `test_gate_deny_fields.py` 14 測全綠 | `pytest tests/governance/test_gate_deny_fields.py -q` → **14 passed in 3.97s**，rc=0 |
| B0 snapshot 時序 | `git show 596fcb4^:scripts/gate_check.sh` sha256 **==** `gate_check_pre_phase2.sh.snapshot` **==** `871258c9…1606a`（sidecar 一致） |
| 語料 A/B sha256 不同且 tracked | A=`1ae51fc7…` B=`57434c99…`；`git ls-files --error-unmatch` 兩檔 rc=0 |

### 攻擊 §0 四條假設

| 假設 | 攻擊結果 |
|---|---|
| 其餘 17 個測試有恆真斷言／只驗不拋錯 | **推翻**——本檔實為 **14** 個測試（非 17）；逐條讀畢：`TEST-0.1-INVARIANCE`／`TEST-0.1-MUT`／`TEST-0.1-FIELDS`／三邊界測為實質斷言；`TEST-0.1-RC-*` 僅驗 rc 屬 TODO 設計的薄煙霧層，**由 INVARIANCE 20 條語料補強**，非恆真 |
| 三處 scope 變更皆必要且最小 | **成立**——見下節獨立驗證；三處皆為 TODO 字面缺口，實作者明文宣告，未靜默偏離 |
| `715 passed` 主委未親跑 | **推翻**——本委員實跑 715 passed（見上） |
| B0 snapshot 為 B1 改動前狀態 | **成立**——`596fcb4^:gate_check.sh` 與 snapshot 位元組一致 |

---

## 三處 scope 變更（獨立驗證）

| # | 變更 | 判定 | 依據 |
|---|---|---|---|
| 1 | `required_fields_per_event.gate_deny` 保留 `tool`／`kind` | **理由屬實；未弱化** | `test_gate_deny_audit.py:49-52` 已斷言 `tool`／`kind`；TODO L153 僅列 6 欄屬主委漏列。保留後 FIELDS 測試要求 **精確集合相等**（8 欄），較舊 4 欄 audit **更嚴** |
| 2 | `event_object_allowed_keys` array→map | **必要；語意未弱化** | 舊值為 debt 定義鍵陣列（`origin_script`…`fields`）；TODO 要求 `.gate_deny` 鍵與 array 結構不相容。`rg event_object_allowed_keys` 在 `scripts/`／`tests/governance/` **零消費者**——僅 schema 登記；map 保留 `_debt_event_definition` 原 6 鍵並新增 `gate_deny` 白名單 |
| 3 | 語料 B 最小占位 | **必要；誤導風險低** | `TEST-0.1-CORPUS-DISTINCT` 要求兩檔皆 tracked 且 sha256 不同，但語料 B 內容屬 Task 2.0。占位檔 L1–3 註解明寫 `placeholder`／`Task 2.0 覆寫`；payload 含 `PLACEHOLDER_FOR_TASK_2_0` 字串，Task 2.0 實作者不易誤判為完成 |

---

## 逐項核對表

| # | 查什麼 | 判定 | 依據（實跑命令＋結果） |
|---|---|---|---|
| 1 | 語料 A 是否涵蓋現行判定全分支 | **部分覆蓋（本批可接受）** | `grep -c '^{' gate_invariance_corpus.txt` → **20** 條（brief 寫 24 為筆誤）。涵蓋：Task／Bash executor 全族／env 剝除／管線與 `;` 分隔／gate 自身排除／檔名子字串誤擋否定。**未涵蓋**：Write→`artifact`、fresh token 放行、`open_debt` deny。`diff -u snapshot gate_check.sh` 顯示 **判定段 `grep -Eq` 與 kind/rc 邏輯零改動**（僅 deny 後 audit 擴欄）⇒ 未覆蓋分支在本 commit 無行為漂移風險；`token_expired` 由 `test_01_enum_token_expired` 單測覆蓋 |
| 2 | `grep -Eo` 是否在判定之後且不回流 | **是** | `rg 'grep -Eo' scripts/gate_check.sh` 僅命中 `_gate_deny_match_info`（L53/L56）；判定段 L171 僅 `grep -Eq`。`_mi` 只在 `deny_reason` 已定後、`_append_gate_deny_audit` 前呼叫（L203–205、L217–219）；`frag` 變數未參與 rc/kind |
| 3 | 356 行新測試有無廉價綠燈 | **無** | 14 測逐條審：`INVARIANCE` 比對 20 項 `(rc,kind)` 差分==0；`MUT` 錨點 `assert anchor in text` 防漂移；`FIELDS` 集合精確相等；`4mb` 斷言行長≤1024；無 `assert True`／空 `pass` |
| 4 | B0 snapshot 時序 | **正確** | `shasum -a 256 <(git show 596fcb4^:scripts/gate_check.sh) snapshot` → 兩者 **871258c9…1606a** |
| 5 | 截斷邊界：4MB→≤1KB；控制字元→合法 JSON | **通過** | `pytest …::test_01_boundary_4mb_audit_line_le_1kb -q` PASSED；`…::test_01_boundary_control_chars_valid_json` PASSED；`gate_check.sh` L97–110 超 1024 字元清空 `cmd_head` 重組 |
| 6 | 兩份語料 sha256 不同且 tracked；A 含真實被擋案例 | **通過** | sha A≠B（見 §0）；A 含真實 executor 指令（`codex exec`／`cursor-agent`／`grok`／`agy`／`claude -p`）與真實放行案例（`cat handoffs/`、`grep …/docs/`、`sp_codex.txt`），非全憑空 JSON |

---

## 出場判準核算

| 項目 | 值 |
|---|---|
| findings 總數 | **0** |
| BLOCKING | **0** |
| 公式 `findings ≤5 且 BLOCKING=0` | **滿足** |
| 結論 | **B0+B1 驗收通過，可進 B2** |

### 殘留觀察（不計 finding，供 B2／Task 2.0）

- 語料 A 未含 Write/artifact、fresh-token 放行、`open_debt` 三路徑——建議 Task 2.0 語料 B 或後續補條，非本批阻塞項。
- `match_rule` 枚舉中 `open_debt`／`unknown`／`outer_script`／`role_gate` 未在 `test_gate_deny_fields.py` 單獨觸發——`open_debt` 由 case 直接賦值，風險低。

---

ASSUMPTIONS_VERIFIED: B0 snapshot==parent gate_check sha256；715 governance passed；14 gate_deny_fields passed；grep -Eo 僅 deny 後路徑；三 scope 變更理由屬實；既有 test 檔零改動。  
TESTS_RUN: `pytest tests/governance/test_gate_deny_fields.py -q` → 14 passed rc=0；`pytest tests/governance -q` → 715 passed rc=0；`shasum` snapshot vs `596fcb4^:gate_check.sh`；`git diff 596fcb4^..596fcb4 --name-only -- tests/governance/`；`grep -c '^{' corpus A`；`rg 'grep -Eo' scripts/gate_check.sh`。  
FAILURES_SEEN: none。  
SCOPE_CHANGES: none（僅 review 產出）。  
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼）。  
OUTPUT_FILE: `handoffs/20260805-govb0-b0b1-review-composer.md`  
STATUS: DONE
