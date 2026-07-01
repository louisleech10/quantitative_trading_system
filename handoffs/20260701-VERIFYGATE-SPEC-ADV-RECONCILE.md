# VERIFY_GATE_SPEC 雙家族 adversarial reconcile

**兩家**:Codex(`...-ADV-CODEX.md`)、Composer(`...-ADV-COMPOSER.md`),皆 **VERDICT: CHANGES-REQUESTED**。
**結論**:SPEC 方向(receipt+claim checker+hook+ledger)正確,但 v1 仍可「換名重演事故」→ 須補 BLOCK 後重審再派實作。

## 收斂 BLOCK(兩家一致,必修)
- **B-FORGE 偽造 receipt**:receipt 自證,手寫+對 sha 即過。修:`run_with_receipt.py` 發 **append-only 審計事件**(`.claude/gate/audit.log`)含 `receipt_id+command_sha+git_head+log_sha+started/ended`;checker 要求 receipt 有匹配審計事件才採信(手寫無事件→拒)。`run_receipts/` 不偽造路徑 + 引用的 receipt/log 須與 commit 同 staged(Codex MAJOR-4)。
- **B-HOOK hook 缺席/停用/`--no-verify`**:本地 hook 可繞。修:**三層**①PreToolUse 攔 `Edit/Write` HANDOFF.md+handoffs/(堵 Claude 編輯主路徑,非 git 繞不過——本事故正是此路徑);②repo-tracked `core.hooksPath=scripts/git_hooks` 的 pre-commit+commit-msg(本地網);③**CI(.github/workflows)on PR/push 跑 checker over diff**(--no-verify 擋不掉的後盾)+`verify_hooks_health.sh` 在 preflight/postflight/CI 檢 hook 存在可執行。
- **B-CLASS runtime_class 自宣告**:修:由 command argv+selected node-ids+markers **推導**;mutation_runtime 須 `-k test_mutation_`+node-id 前綴 test_mutation_+pass/fail 非零;requires_kline_runtime 須 `requires_kline` marker;傳入值僅「requested」非「authoritative」。
- **B-EXEMPT VERIFY-EXEMPT 太寬**:修:`VERIFY-EXEMPT:<窄類別>:<issue/review-id>`,類別白名單;**HANDOFF.md/commit/RESULT 段禁豁免**;`claim-context: discussion` 僅作用於 fenced evidence block 或白名單 forensic 檔 pattern,不蓋任意新 operational handoff;濫用須測(應擋)。
- **B-LEDGER pending ledger 規格不足/race**:修:`pending_id+claim_fingerprint+source_file/line+required_runtime_class+required_node_ids/markers+opened_by_sha`;事件單調排序;close 須對 exact pending_id 驗證;checker 以 reduce 事件求未結,非 task_id 字串比對。
- **B-SCOPE v1 暫緩 #6/#7 留著事故自身失效模式**:修(v1 至少最小版):#7 RESULT 硬欄位 `MUTATION_STATIC:/MUTATION_RUNTIME: NOT_RUN|PASS|FAIL` 為 pending 可靠輸入;#6 根 HANDOFF 至少做「過期/superseded claim 衝突檢查」(同 assertion 紅燈後舊 receipt-backed claim 不得仍綠)或明列殘餘風險為 N/A+後續 blocker。

## 收斂 MAJOR(必修或明列 N/A)
- 同義詞/NFKC/零寬/拆段繞過(兩家):normalize(NFKC+strip ZWSP+hyphen/space/case)+段落級語意 pattern+未知變體 WARN 模式。
- 「同段」演算法未定義:每個 claim 產 claim-object(極性+scope 詞+runtime 詞+鄰近 receipt id);一 receipt 只滿足 scope 與其 command/node-id 交集的 claim;同段未支撐 claim 仍須 FAIL(Codex MAJOR-2/Composer 拆段)。
- receipt schema 內部不一致:P1 未產 `log_sha256` 但 P2 要求(Codex MAJOR-3)→ schema 明列 log_sha256 + V1 斷言;定義 stdout/stderr 是否合併。
- §V mutation 過窄:增反例 falsifier(偽 receipt、誤標 class、同段多 claim、HANDOFF 內 EXEMPT、hook 未裝、untracked receipt、unicode 同義詞)。
- pytest 解析失敗不阻斷 與 範圍匹配自相矛盾:解析失敗對「需範圍」的 claim 應 fail-closed。

## 收斂 MINOR
gate_check.sh `jq` 缺→fail-open 應列殘餘風險(避免 jq 於關鍵路徑或加 health check);`passed`/`通過` 詞太廣易誤擋→精確界定敘事 vs 宣稱語境;P4 包裝改 buffering/rc 透傳需 fixture 驗失敗路徑也產 receipt。

## 待使用者決策(威脅模型/範圍,見下方給使用者問題)
本事故=**編排者疏忽過度宣稱**(非惡意密碼學偽造)。兩家以惡意對手攻擊。修到哪一級(careless-proof vs forgery-proof)是成本/野心取捨,屬使用者優先序,非純技術正確性 → 問使用者。
