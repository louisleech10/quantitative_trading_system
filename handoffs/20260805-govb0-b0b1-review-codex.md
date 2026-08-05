family: codex
reviewed_commit: 596fcb4
scope: B0 snapshot + B1 Task 0.1 only; read-only review

## Verdict

**Verdict**: B0+B1 通過出場判準，可進 B2；有 2 條非阻塞 finding，P0/BLOCKING=0。

## §0 前提宣告

- fact-verified: `pytest tests/governance -q` = **715 passed**；targeted suite = **14 passed**。
- fact-verified: snapshot 與 `596fcb4^:scripts/gate_check.sh` byte-identical；sidecar、四個 fixture 均 tracked；A/B sha 不同。
- fact-verified: 實作者三處 scope 變更皆有依據；#1 保留既有欄位，#2 保留舊 debt key set，#3 明確標成 Task 2.0 placeholder。
- assumed attacked: 主委轉述的 715 passed、snapshot 時序與三處 scope 合理性；前兩者已由本 review 獨立重跑/比對，第三者見下表。

### 實作者三處 scope 變更獨立驗證

| # | 判定 | 實跑依據 |
|---|---|---|
| 1 | **屬實，無弱化** | `test_gate_deny_audit.py:49-52` 仍斷言 `event/tool/kind`；registry 與產出欄位集合相等；full governance 715 passed。 |
| 2 | **屬實，無現有 repo consumer 受影響** | `jq` 顯示 `_debt_event_definition` 保留原 6 keys，`required_fields_per_event.gate_deny == event_object_allowed_keys.gate_deny`；`rg` 無 consumer；full governance 715 passed。此 map 擴充是滿足 `.gate_deny` key 的最小相容形狀。 |
| 3 | **屬實，且未冒充完成** | `gate_decision_corpus.txt:1-4` 明寫 placeholder、Task 2.0 覆寫與 22+ 條要求，JSON sentinel 為 `PLACEHOLDER_FOR_TASK_2_0_decision_corpus_not_invariance`；本輪不計 Task 2.0 完工。 |

## 逐項核對表

| # | 判定 | 依據（實跑命令＋結果） |
|---|---|---|
| 1 | **部分，見 CODEX-R10-P1-01** | `awk`：A 只有 20 JSON rows、Write=1、gated Write doc=0、token/open_debt=0；runtime trace=20（11 blocked/9 allowed）。 |
| 2 | **PASS** | `rg -n 'grep -Eo|_gate_deny_match_info|...' scripts/gate_check.sh`：判定 `grep -Eq` 在 :170，`grep -Eo` 僅在 helper :53/:56，helper 呼叫在 deny 後 :203/:217。 |
| 3 | **部分，見 CODEX-R10-P2-02** | 新測試 356 行、14 tests 全綠；核心欄位/邊界/mutation 非 smoke，但非空 command 的 hash 內容未被 oracle 綁定。 |
| 4 | **PASS** | `cmp parent_gate_check.sh snapshot` rc=0；兩者 sha=`871258c9ea2e...01606a`；sidecar cmp rc=0。 |
| 5 | **PASS** | targeted 14 passed，包含 control/newline JSON 與 4 MB audit line ≤1 KB；full 715 passed。 |
| 6 | **PASS（B 為明示占位）** | A sha=`1ae51fc7a445...e876`、B sha=`57434c991807...8de01`，皆 `git ls-files` rc=0；A runtime 11/20 為真實 deny cases。 |

## CODEX-R10-P1-01

**斷言**: `TEST-0.1-INVARIANCE` 的語料 A 未覆蓋現行 `gate_check.sh` 的 gated `Write` artifact 分支，也未覆蓋 token/open-debt 決策分支，因此不能證明全部既有 `(rc, kind)` 分支不變。

**碼證**: `tests/governance/test_gate_deny_fields.py:179-193` 只把 `CORPUS_A` 跑 snapshot/current；實跑 `awk` 得 20 rows、`Write=1`、`file_path.*(SPEC|TODO|PLAN)=0`、`dispatch.token|open_debt=0`。`gate_check.sh:176-183` 確有 `Write` artifact 判定；額外 probe `Write docs/NO_SUCH_SPEC.md` rc=2、既有 docs path rc=0。RECHECK：重跑上述 awk/rg、`pytest tests/governance/test_gate_deny_fields.py -q`，並把 missing/existing governance Write 與 fresh/open-debt cases 加入 immutable A。

**來源摘要**: `tests/governance/test_gate_deny_fields.py#7f507806714d`; `tests/governance/fixtures/gate_invariance_corpus.txt#1ae51fc7a445`; `scripts/gate_check.sh#635f951eddfe`; `docs/GOVB0_FRICTION_TODO.md#a1410ec31fcd`

[MAJOR] 信心度=High；目前程式行為未被本 finding 證明錯誤，缺口在 invariance oracle。若後續改動誤改 artifact/token 分支，B1 的核心不變式仍可能綠。修法是擴充 A 與對應 trace，保留 B1/B3 的 baseline 分離。

## CODEX-R10-P2-02

**斷言**: 新測試只驗非空 `cmd_head` 與 64 字元 hash，未驗 `cmd_sha256 == sha256(完整 command)` 或 `cmd_head == 前 512 bytes`；因此 hash 改成錯誤但同長度仍可綠。

**碼證**: `test_gate_deny_fields.py:214-227` 僅斷言 enum、head truthiness、hash length；`:306-316` 僅斷言 audit line ≤1 KB；唯一 hash 內容斷言 `:301-302` 只涵蓋空 command。RECHECK：`rg -n 'cmd_sha256|cmd_head|hashlib' tests/governance/test_gate_deny_fields.py` 與 `pytest tests/governance/test_gate_deny_fields.py -q`；補充非空完整 hash/head oracle 及 >512-byte command mutation。

**來源摘要**: `tests/governance/test_gate_deny_fields.py#7f507806714d`; `scripts/gate_check.sh#635f951eddfe`; `docs/GOVB0_FRICTION_SPEC.md#283298bb1e8a`

[MINOR] 信心度=High；現行實作 :23-38 的正常路徑計算正確，問題是測試無法防止未來錯誤改動。修法是以固定非空 command 計算 expected full SHA、以 byte-faithful head 比對，並對控制字元/512-byte 邊界保留 JSONL 與 ≤1 KB 斷言。

## 出場判準核算

FINDINGS_COUNT: 2
BLOCKING_COUNT: 0（P0=0）
EXIT_RULE: findings ≤5 且 BLOCKING=0 → **PASS，可進 B2**。
OUT-OF-SCOPE: B2 以後 Task、SPEC/TODO 重開、已具名 E-SCOPE/H-1/H-2/F-7/B-36；本 review 未以其列 finding。
TESTS_RUN: targeted 14 passed；full 715 passed；snapshot cmp/sidecar cmp/tracked checks rc=0；golden restore rc=128（sandbox 禁 `.git/index.lock`），`git status --short tests/golden/` 為空。
FAILURES_SEEN: restore_golden_inventory.sh 受 sandbox 阻擋，未留下 golden diff；其餘驗證無未解失敗。
SCOPE_CHANGES: none；未改 production、既有 tests、SPEC/TODO 或 data_cache；僅新增本報告。
NUMERIC_OR_SCHEMA_IMPACT: review only；未改產品數值/schema/output。
HANDOFF_OUTPUT: `handoffs/20260805-govb0-b0b1-review-codex.md`
RECONCILE-STAMP: codex APPROVED 2026-08-05 sha256:82e216df937ad661116b7fad00aa626c0da362fc3a24f45104eef8cdcd0d9c20 task:GOVB0-B0B1-REVIEW
STATUS: DONE
