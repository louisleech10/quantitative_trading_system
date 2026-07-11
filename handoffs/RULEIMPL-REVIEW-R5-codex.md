# RULEIMPL R5 終驗 — Codex（R5）
審查客體：`handoffs/RULEIMPL-SPEC-DRAFT-R5.md`；逐條複驗 `handoffs/RULEIMPL-REVIEW-R4-codex.md` 四條 STILL-OPEN。

1. **STILL-OPEN — grandfather（R4 #2）**：R5 已鎖 cutoff、git-only diff、無 git fail-closed 與 V-T11–T13；但 production `VALIDATION_ENFORCE_BASE_SHA` 仍是 `<full-40-hex>`／`<開票時填入>`，尚非可執行常數。且 base 算法第 1 步在該 SHA 不是可解析 commit 時失敗，第 2 步仍對同一不可解析 SHA 執行 `git merge-base HEAD "$VALIDATION_ENFORCE_BASE_SHA"`，不能形成有效 fallback。故「相對哪個 ref」尚未在本稿唯一落值，實作者仍無法照稿得到 production `base_ref`。
2. **CLOSED — counterfactual 綁定（R4 #4）**：approval manifest 已必填 classification + canonical content digest，digest 納入 body hash，external path 亦須同 digest；九維、`range`、`mechanical_source`、unknown fail-closed 均凍結。V-M6、V-CF4–CF6 明確覆蓋缺欄／脫鉤、任一 yes + 舊 REVIEW hash、缺機械來源或範圍及 external tamper。
3. **CLOSED — command canonical + digest（R4 #6）**：`command` 已凍結為 `--` 後 argv string array，指定 JSON canonical serialization、UTF-8、SHA256 格式與 emitter/consumer 共用函式；consumer 必從 `command` 重算。V-G5b、V-G13、V-G14 覆蓋 receipt 字面重算、command tamper 與空格／Unicode／`--` round-trip，原缺口閉合。
4. **STILL-OPEN — IC1EB sidecar 防竄改（R4 #7）**：R5 已加入 formal SPEC hash、body digest、非作者 approval stamp 與 expiry tamper 測試；但 `sidecar_body_sha256` 定義為 `json.dumps(obj_without_stamps, ...)`，只說排除「戳記欄位」，未明定同時排除 `sidecar_body_sha256` 自身。依字面該 digest 欄仍在被雜湊物件內，形成不可計算的自我參照；不同實作者可各自排除不同欄位。須凍結明確 exclusion set（至少 `approval_stamps` 與 `sidecar_body_sha256`）及相同算法的 checker/test fixture，才可機械驗證 expiry 綁定。

ASSUMPTIONS_VERIFIED: 逐段核對 R5 §C、Phase 0–4、§V、D4/D10–D12 與 R4 四條 STILL-OPEN；並以 `git rev-parse HEAD` 確認 repo 現有真實 full SHA，但 R5 未鎖入該值。
TESTS_RUN: `sed`/`nl`/`rg` 唯讀比對 R4 review、R4/R5 draft、reconcile；`git rev-parse HEAD` → `e43350039ac2393e6aef70991c2b4cc35330cc96`。文件終驗，未跑 pytest。
FAILURES_SEEN: none
SCOPE_CHANGES: none；唯一新增本檔。
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查；指出 grandfather 常數/算法與 sidecar canonical digest 尚未閉合）。
VERDICT: BLOCK
