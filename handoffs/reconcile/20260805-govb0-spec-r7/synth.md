# Reconcile — 20260805-govb0-spec-r7

**來源** 20260805-govb0-spec-r7-codex.md, 20260805-govb0-spec-r7-composer.md　|　**roster** codex,composer

## 群集 / 處置

Verdict: 可合併 — 4 條全部歸戶、**無未分群 ID**。兩家一致判 **deliverable-invalidating = 0、可進 TODO 生成**。

**收斂趨勢**：R1 19（5 P0）→ R2 17（7 P0）→ R3 11（3 P0）→ R4 8（2 P0）→ R5 2（2 P0）→ R6 3（2 P0）→ **R7 4（0 P0）**。
🔴 **R7 是 P0-1／P0-2 的最後一輪**（brief 明文宣告終止條件，依使用者定死「95% 解法就收・殘留先記錄」）。
兩家皆依該條件將新缺口分類為 **named-residual**，無人主張 deliverable-invalidating。

**收斂基數**：4 條（codex 2／composer 2）。**兩家獨立收斂到同樣的兩個問題**，故群集為 2。
ID→斷言對照由 `awk` 自附錄機械抽出後才填表（防歷來 7 次錯位）。

**驗證 receipt**（主委實跑 2026-08-05）：
VERIFY: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS` rc=0
VERIFY: `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r7/sources.lock` → rc=0，4/4 ID 全在綜合檔

| 群 | 主張 | 對應 finding | 處置 |
|---|---|---|---|
| H-1 | **⑥(c) 允許清單非完整 shell-word grammar**：`~`／`{`／`}`／`[`／`]`／`!`／`*`／`?` 為合法 Bash delimiter 卻未列入 ⇒ 走⑦ fail-closed ⇒ **誤擋合法 heredoc**，與本批「止血摩擦」目標自相矛盾 | `CODEX-R7-P1-01`／`COMPOSER-R7-P2-01` | **ACCEPT → 已部分修 ＋ 具名殘留**：允許清單補入 codex 實跑驗證的 8 字元 `~{}[]!*?`（`BASH_UNQUOTED[…] rc=0` 全數證實 bash 接受）。**但允許清單本質是枚舉，非完整 grammar** ⇒ 未列字元仍走⑦。🔴 **殘留方向安全**（過擋而非漏放，不使 gate 失效）。補查條件同 `B-15` FP-2：Phase 0 上線後以 `gate_deny` 反查誤擋，命中才擴。**本批不再擴。** |
| H-2 | **reclaim lock 孤兒**：stale takeover 持有者若在步驟③（刪主 lock＋建新 lock）後、④（釋放回收權）前 crash，`<out>.reclaim.lockdir` 殘留 ⇒ 後續 takeover 於步驟①即 EEXIST 拒絕 ⇒ **該 `<out>` 路徑鎖死至人工清理** | `CODEX-R7-P1-02`／`COMPOSER-R7-P2-02` | **ACCEPT → 具名殘留，修法落 TODO 運維項**。codex 實跑：`CRASH_CHILD_RC=137`／`MAIN_LOCK_AFTER_CRASH=present`／`RECLAIM_LOCK_AFTER_CRASH=present`／`NEXT_DISPATCH=REJECT_EEXIST`。🔴 最壞後果＝**單一 `<out>` 暫時不可用**，不會雙 CLI 並存、不會漏放真派工 ⇒ 非 deliverable-invalidating。TODO 三擇一：(a) 清 orphan 的運維腳本 (b) reclaim lock 加 TTL／lease＋受保護的 stale-reclaim CAS (c) 改用 crash 自動釋放的 `flock`。**TODO §0 須明文標「reclaim 孤兒回收未實作 ⇒ 需人工清理」，不得宣稱 lock 機制全綠。** |

**兩家獨立收斂到同一組問題，是本批首次出現**

R5 兩家結論相反（composer 判全 CLOSED，看到 codex 反例後改判）；R6 兩家仍相反（composer CLOSED、codex 3 findings）。
**R7 是第一次兩家在未互見的情況下各自提出同樣的兩條**，且嚴重度分類一致（皆 named-residual）。
⇒ 這是比「都說 PASS」更強的收斂訊號：兩條獨立路徑指向同一組殘留，且都同意不阻塞。

**主委補記：H-1 的修法違反過本 repo 自己的規則**

R6 版⑥用**排除清單** `([^[:space:]|&;()<>]+)`，被 `CODEX-R6-P0-01` 實跑證偽（接受了⑦要求拒絕的混合引號）。
`票 B-23` 早已定「列舉禁止符號永遠列不完 ⇒ 反轉為允許清單」——**主委寫 R6 版時未遵守本專案自己的既有裁決**。
R7 改為允許清單後，H-1 剩下的只是「枚舉不完整」，方向已從 fail-open 轉為 fail-closed。
⇒ 應列為 `票 B-23` 的佐證：**排除清單的病不是「列不完」，而是「列不完時的失敗方向是危險的」**。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R7-P1-01

**斷言**: R7 的 unquoted heredoc delimiter allowlist 不是完整 shell-word grammar；合法 Bash delimiter `~`、`{`、`}`、`[`、`]`、`!`、`*`、`?` 會被掃描器送入⑦ fail-closed，造成誤擋。

**碼證**: SPEC:199-210 定義 `([A-Za-z0-9_.:+=,%@^-]+)`；SPEC:232-239 只納入目前列出的合法／拒絕語料。實跑 `bash .govb0-r7-probe.sh` stdout：`BASH_UNQUOTED[~] rc=0`、`BASH_UNQUOTED[{] rc=0`、`BASH_UNQUOTED[}] rc=0`、`BASH_UNQUOTED[[] rc=0`、`BASH_UNQUOTED[]] rc=0`、`BASH_UNQUOTED[!] rc=0`、`BASH_UNQUOTED[*] rc=0`、`BASH_UNQUOTED[?] rc=0`。RECHECK：以同一 probe 重新執行，並在 heredoc 後保留 `printf AFTER`，確認 shell 真的完成 delimiter consume。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#96f69c2e93ad

[MAJOR] 信心度=High；分類=named-residual。這不會讓真派工漏放，也不會讓兩個 CLI 並存，但與本批降低 accidental friction 的目標衝突。可執行修法：在 TODO 固定完整 shell-word／quote-removal grammar 並加入上述字元的 TP/TN corpus；若刻意維持 allowlist，則把未列字元的誤擋範圍與後續票面列為明確 residual。

## CODEX-R7-P1-02

**斷言**: stale takeover 持有者在步驟③建立新主 lock 後、步驟④釋放 reclaim lock 前 crash，會留下永久存在的 `<out>.reclaim.lockdir`；後續 stale takeover 依①直接 EEXIST 拒絕，無法自行恢復。

**碼證**: SPEC:406-412 規定取得回收權、刪除／重建主 lock、最後釋放回收權，但沒有 crash recovery、lease、owner token 或 orphan reclaim 的清理協定。實跑 `bash .govb0-r7-lock-crash.sh` stdout：`CRASH_CHILD_RC=137`、`MAIN_LOCK_AFTER_CRASH=present`、`RECLAIM_LOCK_AFTER_CRASH=present`、`NEXT_DISPATCH=REJECT_EEXIST`。RECHECK：在③後以 SIGKILL 終止持有者，再用第二個 dispatcher 重跑①；預期可重現 EEXIST 拒絕。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#96f69c2e93ad

[MAJOR] 信心度=High；分類=named-residual。這是 fail-closed 的可用性／恢復缺口，不構成 brief 定義的 deliverable-invalidating（沒有漏放真派工或雙 CLI）。可執行修法：改用 crash-releasing `flock`，或為 reclaim lock 定義帶 owner token／pid／時間的 lease，並以受保護的 stale-reclaim CAS 清理孤兒後重試；同時加入③→④ crash mutation。

## COMPOSER-R7-P2-01

**斷言**: ⑥(c) 允許清單未收 `~` `{` `}` `[` `]` `!` `#` 等 shell 可能用作 delimiter 的字元，實作者照 SPEC 會對這類合法 heredoc 走⑦ fail-closed，造成誤擋（非 fail-open）。

**碼證**: SPEC:199–210（允許清單字元集）；探針 `EDGE_WOULD_BLOCK=5/5`（`<<EOF~1` 等）。RECHECK: 對五個罕見 delimiter 形跑契約 shape 掃描，預期⑦ `BLOCK`。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#96f69c2e93ad

**[MAJOR→降級 P2] 信心度=Medium**；分類：**named-residual**（⑦ 方向為過擋而非漏放派工，不使 gate 失效）。修法（非本批阻塞）：Phase 0 上線後以 `gate_deny` 反查 heredoc 誤擋；若命中則擴允許清單或開票 `B-15` 子項。

## COMPOSER-R7-P2-02

**斷言**: stale takeover 協定④要求釋放 `<out>.reclaim.lockdir`，若持有者在③（刪主 lock＋建新 lock）之後、④（`rmdir` reclaim）之前 crash，回收權殘留會使後續 stale takeover 在① `mkdir reclaim` 處 EEXIST 拒絕，該 `<out>` 路徑暫時無法自動回收。

**碼證**: SPEC:406–412（①–④ 步驟）；探針模擬③後不執行④ → `RECLAIM_STUCK=yes`、`NEXT_TAKEOVER=blocked_by_reclaim`。RECHECK: 建立 reclaim 後不 `rmdir`，再跑 takeover ⇒ 第一步拒絕。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#96f69c2e93ad

**[MAJOR→降級 P2] 信心度=Medium**；分類：**named-residual**（不導致雙 CLI 並存；最壞為單路徑鎖死至手動清 reclaim）。修法（非本批阻塞）：TODO 加運維腳本清 orphan reclaim，或 TTL＋audit 警示（超出本 SPEC 範圍，記 `票 B-15` 家族）。


## 戳記
RECONCILE-STAMP: codex APPROVED 2026-08-05 sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd task:GOVB0-R7-STAMP

RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd task:GOVB0-R7-STAMP

RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd task:GOVB0-R7-STAMP
