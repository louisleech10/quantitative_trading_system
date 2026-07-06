# INSTREV Phase B Code Review — Codex

對象：`scripts/check_agent_contract_sync.sh`、`scripts/gate.sh`、`scripts/gate_check.sh`、`scripts/git_hooks/pre-commit`、`scripts/verification_claim_check.py`、`scripts/dispatch.sh`、4 個新增 governance tests。對照：`docs/INSTREV_PHASEB_SPEC.md`、`docs/INSTREV_PHASEB_TODO.md`、`handoffs/20260705-INSTREV-PHASEB-ADV-RECONCILE.md`。

## Findings

ID: REVIEW-1  
Verdict: MAJOR  
位置：`scripts/git_hooks/pre-commit:18-60`  
會怎麼失敗：B3 邊界要求「非 UTF-8/blob 讀取失敗 → auto-fix 略過該檔不崩，checker 照原邏輯」。目前 hook 用 text-mode Python 讀 `git show :<path>`，且 pipeline 沒有 `pipefail`/狀態檢查；非 UTF-8 staged markdown 不會被略過，實測 `docs/bad.md` 的 staged blob 從 `616263ff2020200a` 被改成 `616263ff0a`，隨後 checker 仍因 decode crash exit 1。這違反 SPEC 的 skip-on-read-failure 邊界，也讓 auto-fix 在無法語義解析的 blob 上改 index。  
建議修法：改成 binary-safe transformer：`git cat-file blob :path` 取 bytes，Python 用 `sys.stdin.buffer.read()`，先 strict decode；`UnicodeDecodeError` 時原樣輸出並以專門 exit/status 表示 skip，shell 只在 transformer 成功且內容改變時 `hash-object/update-index`。加 `set -o pipefail` 或拆成 temp object/status，避免前段失敗被 `git hash-object` 掩蓋。新增非 UTF-8 staged markdown 測試，斷言 index byte-for-byte 不變。

ID: REVIEW-2  
Verdict: MINOR  
位置：`scripts/git_hooks/pre-commit:59`  
會怎麼失敗：auto-fix 以 `git update-index --cacheinfo 100644` 寫回，會把 staged executable markdown 的 mode 從 `100755` 改成 `100644`。實測 `docs/run.md` staged mode `100755 -> 100644`。雖然一般 docs md 多為 644，但 B3 驗證文字要求「除尾隨空白外位元組不變」，index-only hook 不應順手改 index metadata。  
建議修法：從 `git ls-files -s -- "$rel"` 讀原 mode，`update-index --cacheinfo "$mode" "$newsha" "$rel"`；補一個 mode-preservation 測試。

ID: REVIEW-3  
Verdict: MAJOR  
位置：`tests/governance/test_dispatch_wrapper.py:89-118`  
會怎麼失敗：`test_dispatch_explicit_task_id_not_overridden` 是廉價綠燈：`assert tid in output or proc.returncode in (0, 1)` 對 gate.sh 的正常成功/拒發幾乎都會 pass。若 wrapper 完全忽略 explicit `--task-id` 並改用 auto id，只要 gate 回 0 或 1，這個測試仍綠，不能證偽 ADV-CODEX-6/Phase B4「給定 --task-id 時不覆蓋」。  
建議修法：用隔離 `GATE_DIR_OVERRIDE` 讀 audit JSON，強斷言 `task_id == "20990101-explicit-id"` 且不存在 auto-generated same-intent id；或用 bogus/missing-required 場景斷言 gate 收到 explicit task-id。移除 `proc.returncode in (0, 1)` 這種等同放行的條件。

## Checked Counterexamples / Closure

- fail-closed 不變式：`gate_check.sh` 仍保留 jq/parse fail-open(0)、非 gated exit 0、無 fresh token exit 2；`gate.sh dispatch` 缺必填仍 exit 1 且印 usage；`verification_claim_check.py` 只新增 `_print_violation` 提示，未改極性/backing 判定路徑。
- U-12 append 護欄：兩條 DENY 路徑都有 `gate_deny` append；append helper 有 `mkdir ... || true` 和 append `|| true`，不可寫 dir 實跑仍 exit 2。
- U-15 wrapper：兩次 `dispatch.sh --intent same-intent ...` 實跑第一遍 exit 0、第二遍因 audit task-id 碰撞 exit 1；未知參數測試會由 gate.sh 報 `未預期參數`，未看到 wrapper 繞 gate.sh。
- ADV-CODEX-1/2：partial-stage 工作樹不被納入、fenced/hard-break 保留有測到；但 REVIEW-1/2 顯示非 UTF-8 與 mode 邊界未閉合。
- ADV-CODEX-3/4/5/6/7/8：主要程式碼落實；ADV-CODEX-6 的 explicit task-id 測試證偽性不足，見 REVIEW-3。

## Tests Run

- `bash scripts/check_agent_contract_sync.sh` → exit 0，stdout 含 `✅ 四源關鍵不變式一致`。
- `source venv/bin/activate && pytest tests/governance/test_sync_check.py tests/governance/test_gate_deny_audit.py tests/governance/test_precommit_autofix.py tests/governance/test_dispatch_wrapper.py -q` → 22 passed。
- `source venv/bin/activate && pytest tests/governance/test_verify_gate*.py -q` → 115 passed / 9 failed；failures match Composer handoff 所稱 pre-existing b4/b5/r7 類別，且 `git diff -- tests/governance/test_verify_gate*.py` 為空。
- 手動反例：非 UTF-8 staged md 被 auto-fix 改 index；executable md mode 被改成 100644；兩次 wrapper 同 intent audit collision 第二次 exit 1。

## Overall Verdict

APPROVE-WITH-FIXES
