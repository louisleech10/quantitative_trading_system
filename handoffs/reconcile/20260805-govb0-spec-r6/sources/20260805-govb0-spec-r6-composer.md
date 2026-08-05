# GOVB0 SPEC R6 — composer 窄確認報告

task-id: GOVB0-SPEC-R6
family: composer
brief-kind: review
scope: 只驗 P0-1（⑥⑦ heredoc）與 P0-2（原子 lock／⑨⑩）；未改碼、未改 SPEC、未 commit/push。

## Verdict

**可進 TODO 生成。** P0-1 與 P0-2 在 SPEC 層均已補齊可機械驗收的機制；重跑 codex 原始 heredoc 攻擊鏈後 R6 契約最小掃描器回 `BLOCK`（R5 仍 `ALLOW`）；barrier race 模擬 atomic `mkdir` 恰一個 `START`，兩步 check-create mutation 出現雙 `START` 可證偽。新 P0 機制缺口 0。

## §0 前提宣告

### 主委 fact-verified（複核）

- `grep -cE 'EOF-1' docs/GOVB0_FRICTION_SPEC.md` → `5`（rc=0）
- `grep -cE 'O_EXCL|lockdir|原子 exclusive claim' docs/GOVB0_FRICTION_SPEC.md` → `6`（rc=0）
- `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS`（rc=0）
- `grep -c '^- FACT-RECEIPT:' docs/GOVB0_FRICTION_SPEC.md` → `10`；`grep -c '^\*\*Task ' docs/GOVB0_FRICTION_SPEC.md` → `11`（皆 rc=0）

### 四條假設攻擊結果

| 假設 | 攻擊結果 | 依據 |
|---|---|---|
| ⑥ `([^[:space:]\|&;()<>]+)` 已窮舉實務 delimiter | **未推翻（無新 P0 繞過）** | 探針 `DELIM_DOT`／`DELIM_BRACE`／`DELIM_DOLLAR` 在外部 `codex exec` 時 R6 皆 `BLOCK`；`<<$'EOF'` 依⑦ fail-closed。未逐一實測 `*`/`?`/`[` 等罕見字元，但不構成機制缺口 |
| ⑦ fail-closed 不會造成實務誤擋暴增 | **未量測，風險低** | `rg '<<' scripts/` 僅見 `<<'EOF'`／`<<'PY'` 等標準形；無 `E'O'F` 類混合引號。⑦ 誤擋需非標 delimiter，本 repo 未見 |
| ⑨ barrier race 在 CI 可穩定重現 | **本地支持，CI 未驗** | deterministic barrier（`touch` 同步，非 sleep 競速）下 atomic 模式 `START_COUNT=1`；twostep mutation `START_COUNT=2` |
| `mkdir` 跨檔案系統原子 | **未實測 overlayfs** | POSIX `mkdir` exclusive create 語意；本地 APFS 探針符合。SPEC 已列 `mkdir`／`O_EXCL` 二選一 |

## 逐條確認表

| 項 | 你的判定 | 依據（實跑命令＋結果） |
|---|---|---|
| P0-1 攻擊鏈是否關閉 | **CLOSED** | `python3 /tmp/govb0-r6-composer-work/heredoc_shape_scan.py R5` 對 codex 攻擊語料 → `CONTRACT_SHAPE_SCAN=ALLOW`；同語料 R6 → `CONTRACT_SHAPE_SCAN=BLOCK`（rc=0）。語料＝`cat <<EOF-1` + body 含 `<<INNER` + `EOF-1` 後 `codex exec -s workspace-write x` + 終止 `INNER` |
| P0-1 是否有新繞過向量 | **無（P0 級）** | `BODY_TP`／`DELIM_DOT`／`DELIM_BRACE`／`DELIM_DOLLAR` R6 皆 `BLOCK`；`<<E'O'F` SPEC ⑦ 已要求整段 fail-closed（語料已列），非新機制缺口 |
| P0-2 原子取得是否足夠 | **CLOSED** | `bash /tmp/govb0-r6-composer-work/p0_2_lock_probes.sh` → atomic `START_COUNT=1` `BARRIER_RACE=PASS`；SPEC Task 3.2 已含 `mkdir`／`O_EXCL`、⑩ lock-create fail-closed |
| P0-2 ⑨ mutation 是否可證偽 | **是** | 同腳本 twostep 模式 → `START_COUNT=2` `A:START`+`B:START` `MUTATION_WOULD_FAIL=yes`；換回兩步檢查必雙啟動，與 SPEC ⑨ 反向 mutation 設計一致 |

## 出場判準核算

- findings 總數：**0**（≤5 ✓）
- 新 P0 機制缺口：**0**（<2 ✓）
- 出場判準原文：「findings ≤5 且新 P0 機制缺口 <2 ⇒ 進 TODO 生成」→ **滿足**
- 是否開 R7：**否**

ASSUMPTIONS_VERIFIED: brief fact-verified 四條 grep/template 已複核；codex 攻擊語料 R5=ALLOW/R6=BLOCK；barrier atomic=1 START、twostep mutation=2 START；⑥ 字元集探針無 P0 繞過；repo heredoc 用法 grep 未見 ⑦ 高風險形。
TESTS_RUN: `grep -cE 'EOF-1' …` rc=0→5；`grep -cE 'O_EXCL|lockdir|…'` rc=0→6；`bash scripts/template_check.sh spec …` rc=0 PASS；`python3 …/heredoc_shape_scan.py R5|R6` rc=0；`bash …/p0_2_lock_probes.sh` rc=0。
FAILURES_SEEN: 首版 p0_1 探針因 `bash -c` 執行未閉合 heredoc 掛起，已改為 shape-only + 終止；未改 repository tracked files。
SCOPE_CHANGES: none。
NUMERIC_OR_SCHEMA_IMPACT: none。
HANDOFF_OUTPUT: handoffs/20260805-govb0-spec-r6-composer.md
STATUS: DONE
