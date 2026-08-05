# GOVB0 SPEC R7 — composer 窄確認報告

task-id: GOVB0-SPEC-R7
family: composer
brief-kind: review
scope: 唯讀審查 `docs/GOVB0_FRICTION_SPEC.md` R7 修法；禁改碼／禁改 SPEC／不 commit。

## Verdict

**可進 TODO 生成。** R6 三條（P0-01 允許清單＋token 邊界、P0-02 stale takeover 回收權協定、P1-03 ⑪ process-discovery fail-closed）在 SPEC 層均已關閉；deliverable-invalidating 缺口 **0**；具名殘留 2 條（P2，不阻擋 TODO）。

## §0 前提宣告

### 主委 fact-verified（複核）

- `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS`（rc=0）
- `grep -c '^- FACT-RECEIPT:' docs/GOVB0_FRICTION_SPEC.md` → `10`（rc=0）
- `grep -c '^\*\*Task ' docs/GOVB0_FRICTION_SPEC.md` → `11`（rc=0）

### brief 三條假設攻擊結果

| 假設 | 攻擊結果 | 依據 |
|---|---|---|
| 允許清單 `[A-Za-z0-9_.:+=,%@^-]` 已涵蓋實務 delimiter | **部分成立；殘留誤擋風險** | 探針 `<<EOF~1`／`<<EOF{1}`／`<<EOF[1]`／`<<EOF!1`／`<<EOF#1` 五條皆走⑦ `BLOCK`（`EDGE_WOULD_BLOCK=5/5`）；常見形 `<<EOF-1`／`<<'EOF-1'`／`<<EOF.1` 等 8/8 `ALLOW` shape。未實測全 repo heredoc 命中率 |
| reclaim lock 協定無新競態（雙 CLI） | **雙 CLI 競態已關**；**回收權殘留未關** | 序貫探針 `STALE_TAKEOVER_STARTS=1`（`A:START`＋`B:REJECT_OWNER_MISMATCH`）；模擬③後④前 crash ⇒ `RECLAIM_STUCK=yes` 阻擋後續 takeover |
| ⑪⑫ 反向 mutation 可構造 | **SPEC 層可證偽**（未跑實作） | ⑪：472–476 行含注入 `EIO`／權限錯誤＋「改為無鎖放行 ⇒ 斷言 FAIL」；⑫：477–482 行含 barrier＋移除 reclaim／owner CAS 的 mutation |

## 逐條確認表

| 項 | 判定 | 依據（實跑命令＋結果） | 若 NOT-CLOSED：deliverable-invalidating 或 named-residual |
|---|---|---|---|
| R6-P0-01 五向量是否全 BLOCK | **CLOSED** | `python3 /tmp/govb0-r7-composer-work/heredoc_r7_scan.py` 對 `<<E'O'F`／`<<E"O"F`／`<<$'EOF'`／`<<E\ F`／`<<EOF$(` → `FIVE_VECTOR_BLOCK=5/5`；排除清單 mutation 對混合引號 `EXCLUSION_MUTATION_HITS=3` | — |
| R6-P0-01 允許清單是否漏收合法字元 | **CLOSED（機制）／殘留（誤擋）** | 合法 8 形 `LEGIT_ALLOW=8/8`；`<<EOF-1` 攻擊鏈契約掃描器 → `BLOCK`（外部 `codex exec` 未被吞）；罕見字元 5 形誤擋見 COMPOSER-R7-P2-01 | named-residual |
| R6-P0-02 takeover 協定是否仍有窗口 | **CLOSED（雙啟動）／殘留（回收權）** | 序貫 stale takeover `STALE_TAKEOVER_STARTS=1`；crash 探針 `RECLAIM_STUCK=yes`＋`NEXT_TAKEOVER=blocked_by_reclaim` | named-residual（見 COMPOSER-R7-P2-02） |
| R6-P1-03 ⑪是否可實作且可證偽 | **CLOSED** | `rg -n '⑪\|process-discovery' docs/GOVB0_FRICTION_SPEC.md` rc=0；⑪ 含可執行斷言語意＋反向 mutation（476 行） | — |

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

## 出場判準核算

- findings 總數：**2**（皆 P2 named-residual）
- deliverable-invalidating：**0**
- 出場判準：「findings ≤5 且 deliverable-invalidating = 0 ⇒ 進 TODO 生成」→ **滿足**
- R6 三條狀態：P0-01 **CLOSED**｜P0-02 **CLOSED（雙啟動面）**｜P1-03 **CLOSED**
- 本輪後不再為 P0-1／P0-2 開 R8（依 brief 終止條件）
- 是否開 R8：**否**

### 必查類別摘要

矛盾=無；漏項/端到端=⑪已補；不可測驗收=無（⑪⑫均有 mutation 文本）；quant/OOM/cache/API=不適用；測試品質=R6 三條已可機械落地；Agent 可執行性=⑥⑦⑪⑫足夠；必要性/短命工=無；E-SCOPE／G-3～G-6／措辭=OUT-OF-SCOPE。

FINDINGS_COUNT: 2

ASSUMPTIONS_VERIFIED: template PASS rc=0；Task=11、FACT-RECEIPT=10；五向量 5/5 BLOCK；合法 delimiter 8/8 ALLOW shape；EOF-1 攻擊鏈契約掃描 BLOCK；stale takeover 序貫 1 START；reclaim crash 殘留探針 RECLAIM_STUCK=yes；⑪⑫ rg 命中＋mutation 文本存在。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` rc=0；`grep -c` Task/FACT-RECEIPT；`bash /tmp/govb0-r7-composer-work/r7_probes.sh` rc=0；`python3 …/heredoc_contract_scan.py` 攻擊語料 rc=0→BLOCK。
FAILURES_SEEN: 首版 shape 掃描器 `^` 錨點 bug（合法 delimiter 誤判 BLOCK），已修正後重跑；barrier FIFO 探針掛起已 kill，改依序貫探針。
SCOPE_CHANGES: none。
NUMERIC_OR_SCHEMA_IMPACT: none。
HANDOFF_OUTPUT: handoffs/20260805-govb0-spec-r7-composer.md
/tmp 清理：已嘗試 `rm -rf /tmp/govb0-r7-composer-work`；環境權限拒絕，**請手動刪除** `/tmp/govb0-r7-composer-work`（已保留 `/tmp/claude-501`）。

RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:96f69c2e93ad9199e0f08c6ec706b49854d3739b39b34800ca41df545feb5413 task:GOVB0-SPEC-R7

STATUS: DONE
