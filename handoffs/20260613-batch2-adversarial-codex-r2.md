# Batch2 Run Lifecycle Adversarial Review — Round 2

- Reviewer: Codex（聚焦確認輪）
- Date: 2026-06-13
- Inputs: SPEC/TODO/MANIFEST/DECISION V2 + round1 19 findings/6 Gates + 現行程式錨點
- Verdict: **FAIL**；API/前端/路徑政策大幅收斂，但 lease/registry/checkpoint 尚有 blocking race。

## 19 Findings 逐條核對

1. **RESOLVED** — 已升大型並命中 (b)(c)。證據：SPEC:6-9；MANIFEST:14。
2. **RESOLVED** — `add` 明定 merge-preserve alias/size/created_at。證據：SPEC:53-57；TODO:58-69。
3. **RESOLVED** — features resolver 與 CGSA resolver 分開，禁止互換。證據：SPEC:41-45；TODO:27-38。
4. **UNRESOLVED** — 文件聲稱 checkpoint 不改、靠 manifest-gone 重生成（SPEC:107-110；TODO:136-140），但真實 `resume_batch()` 在 `queued_items==0` 時直接回 completed（batch_service:174-189），completed item 不會再進 factory manifest gate；刪除亦未更新 `completed_items`/`queued_items`。
5. **PARTIAL** — generation 入口覆蓋 batch worker，warmup 亦被列入（SPEC:69-73；TODO:91-101）；但現行 factory 在方法內取得 lease 後只能在 return 前 release，而 warmup 在 service 收到 result 後才啟動（service:223-271）。V2 未定義可傳遞 lease 的介面，且 TODO:95 仍留「傳遞或重新 acquire」擇項；重新 acquire 存在 delete 插入空窗。
6. **PARTIAL** — mutation 有跨實例鎖（SPEC:53-57），但 TODO:63 明定 `get` 不加鎖，cleanup 卻以 `registry.get` re-check（TODO:82）。alias 可在 re-check 後、rmtree 前成功寫入，仍會發生「命名成功但 run 被刪」。
7. **PARTIAL** — pass1/pass2 task 清理與 hash suffix 已納入（SPEC:75-83）；但 stable_id 仍只用 `hash[:8]`，同 prefix 會碰撞，且 batch checkpoint 可見性未清除。
8. **RESOLVED** — override set 時 CGSA 不刪並明示原因。證據：SPEC:19,62；MANIFEST:9。
9. **PARTIAL** — writer/delete 與 candidate/set_alias barrier 已納入（SPEC:98-102）；但未覆蓋 alias 在「transaction re-check 後、刪除前」的關鍵 interleaving，也未覆蓋 stale-break 競態。
10. **RESOLVED** — 改為 vitest render/store 測試，含 loading/empty/error、409、partial、WS/polling。證據：SPEC:86-91；TODO:120-132。
11. **RESOLVED** — list 不掃 8.3GB，生成完成時計算 split/total size，缺值 null。證據：SPEC:75-83；MANIFEST:10。
12. **PARTIAL** — lifecycle mutation/cleanup corrupt 時 fail-closed，但 generation `add` 仍可把空 snapshot 寫回（SPEC:53-57；TODO:64,69）。另一實例之後會讀到合法空 registry，`_corrupt=False`，alias/ownership 資訊已永久丟失；未提供 round1 要求的顯式 reconciliation。
13. **RESOLVED（CGSA ownership）** — 刪前以 manifest 完整 hash 核對，mismatch/missing 不刪。證據：SPEC:60-64；MANIFEST:8。另有 pass2 hash8 ID collision，歸 #7。
14. **RESOLVED** — status/code/partial failure 已寫死。證據：SPEC:75-82；MANIFEST:10。
15. **RESOLVED** — created_at/size_as_of 為 ISO UTC；features/cgsa/total bytes 分列 nullable。證據：SPEC:75-79。
16. **RESOLVED** — typed completion payload、Zustand queue、WS/polling 等價及兩路測試均明定。證據：SPEC:81,87-90；TODO:123-132。
17. **PARTIAL** — 靜態四層 symlink 已有；SPEC §V 宣稱 swap（SPEC:102），但 Task 1.1/TODO 驗證只有既存 symlink（TODO:87），且「lstat→resolve→rmtree(path)」仍無法抵抗 check 後 parent swap。
18. **RESOLVED** — PermissionError 改 monkeypatch `shutil.rmtree`。證據：SPEC:64；TODO:87。
19. **PARTIAL** — 多數契約已凍結；但 warmup lease 仍交實作者擇傳遞方式（TODO:95），size 寫入 mutation API 未指定，且 auto_cleanup 的 lease 重入矛盾未拆成明確函式。

## Round1 最低重審 Gate

1. **PARTIAL** — canonical features/CGSA/default/override/opaque hash 已定；lock identity 的 `safe_s/safe_tf` 未指定使用 reject 或 normalize 規則，pass2 仍是 hash8 ID。
2. **PARTIAL** — single/batch generation 由 factory lease 覆蓋；warmup 無可實作的無空窗 ownership transfer，cleanup 另有重入問題。
3. **PARTIAL** — multi-instance mutation/merge-preserve 已定；alias re-check 未在 transaction 內，corrupt generation add 可洗掉 corrupt 狀態與 alias。
4. **UNRESOLVED** — registry/task/pass2 多數納入；batch completed checkpoint 不會因 run 刪除而重新 queue，與真實 resume 控制流衝突。
5. **RESOLVED** — API error/time/size/completion schema固定，WS/polling 等價。
6. **PARTIAL** — multi-instance/pass1/pass2/frontend/static symlink 已列；缺 stale-break、alias critical-window、真正 parent-swap interleaving，batch completed-checkpoint 測試方向錯誤。

## V2 新設計的實質 BLOCKING

### N1 — O_EXCL stale-break 可解除新的有效 lease

- V2：讀 lock 的 pid/age，判 stale 後 unlink，再競取；release 也只描述 unlink（SPEC:47-51；TODO:40-56）。
- 反例：A/B 同見舊 stale lock；A unlink 並 O_EXCL 建立新 lease；B 隨後執行其先前決定的 unlink，刪掉 A 的有效 lock，再取得第二把 lease。A/B 同時認為自己擁有 run，delete 可撞 generation。
- 派工前必凍結：lock payload 加唯一 owner token，stale takeover 使用不會誤刪 successor 的原子 claim/rename 或 inode/token compare；release 只可刪除自己 token/inode；新增雙 stale-break barrier 測試。

### N2 — cleanup lease 重入 + alias re-check 非交易

- `auto_cleanup` 先 acquire lease（TODO:82），而 `delete_run` 也必 acquire 同一 O_EXCL lease（TODO:77）；若直接呼叫會把自己判 busy。SPEC 用未定義的「delete_run 內核」（SPEC:63），TODO 未拆出 caller-holds-lease API。
- 同時 `get` 明定不加鎖（TODO:63），不滿足「registry transaction re-check」。即使避開重入，set_alias 仍可在 get 後成功、隨即被刪。
- 派工前必凍結：單一 `_delete_run_locked(..., lease)`；cleanup 在 registry transaction 中原子標記 deleting/驗 alias，或 set_alias 也取得同 run lease。測試需卡在 re-check 後、rmtree 前。

### N3 — generation lease 無法無空窗延伸至非同步 warmup

- factory 方法內 lease 的生命週期在 return 結束；service warmup 在 await executor 回傳後才啟動（現行 service:223-271）。TODO:95 的「傳遞或重新 acquire」不是已凍結介面；重新 acquire 允許 delete 在兩段間成功，傳遞則需改 factory/service contract 或由 service 預先持鎖，且會與 factory 內 acquire 自我衝突。
- 派工前必凍結唯一 owner：例如 service 計算 identity 後持 lease並注入 factory（factory 不重取），或 factory 回傳可轉移 ownership 的 handle；不可 release/reacquire。

### N4 — batch resume 的既有 gate 不會重查已完成 item

- checkpoint completed item 已從 queued 移除（batch_service:512-526）；resume 僅處理 queued，若為 0 直接 completed（:174-189）。因此刪 run 後「同 config resume 走 manifest-gone fresh」不成立。
- 派工前必選定 reconciliation：delete 更新含該 run 的 checkpoint、resume 啟動時驗 completed artifact 並 requeue missing，或明定舊 checkpoint 不可 resume且回顯式狀態；需真實 completed checkpoint 測試。

## 結論

V2 已解決 10/19、部分解決 7/19，仍有 2/19 unresolved；6 Gates 為 1 resolved、4 partial、1 unresolved。N1-N4 任一均可讓不可逆刪除與生成/命名/恢復狀態失去互斥或一致性，故尚不可派工。

ASSUMPTIONS_VERIFIED: 已逐行核對 V2 四文件；並核實 feature_registry add/load、factory config_hash/CGSA gate、service warmup、batch queued/completed resume 真實控制流
TESTS_RUN: read-only focused adversarial review；使用 nl/rg/sed，未跑 pytest/npm（文件審查）
FAILURES_SEEN: none
SCOPE_CHANGES: 僅新增 handoffs/20260613-batch2-adversarial-codex-r2.md；未改 docs/momentum/api/frontend/data_cache/HANDOFF.md
NUMERIC_OR_SCHEMA_IMPACT: none
STATUS: FAIL — O_EXCL stale takeover、cleanup alias transaction/lease 重入、warmup lease ownership、batch completed-checkpoint reconciliation 尚未閉合
