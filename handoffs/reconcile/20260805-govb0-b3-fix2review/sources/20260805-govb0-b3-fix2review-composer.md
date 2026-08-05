# GOVB0-B3-FIX2 確認審查 — composer（R15）

task-id: GOVB0-B3-FIX2REVIEW  
family: composer  
brief: `handoffs/20260805-GOVB0-B3-FIX2-REVIEW-BRIEF.md`  
依據: `handoffs/reconcile/20260805-govb0-b3-fixreview/synth.md`（sha256:eea35be5…）  
實作報告（不可信，已獨立複核）: `handoffs/20260805-govb0-b3-fix2-grok.md`

## Verdict：可進 B4（B3 R2 確認輪通過）

D-1～D-4 均已關閉；三條原始 fail-open 未回退；未發現本批修補新引入之 fail-open／誤擋缺口。

FINDINGS_COUNT: 0  
NEW-DEFECT-INTRODUCED: 無

---

## 逐項核對（1a–1i）

| # | 判定 | 證據摘要 |
|---|---|---|
| **1a** D-1 僅排除整條 gate 自呼叫 | **通過** | 讀碼：`scripts/_gate_lex.sh:351-360` `_gate_cmd_is_self_gate` 禁 `;|&|$\(|`n`；`gate_check.sh:211-213` 早退。自構反例 rc=2：`codex exec x; echo scripts/gate.sh`、`# scripts/gate.sh`、8200B+`; scripts/gate.sh; codex exec hi`、`bash scripts/gate.sh dispatch; codex exec y`。合法自呼叫 rc=0：`bash scripts/gate.sh dispatch --task-id X`、`bash scripts/gate_check.sh`、`./scripts/gate.sh dispatch`、`sh scripts/gate.sh dispatch`。 |
| **1b** D-1 未誤擋語料 B TN | **通過** | `pytest tests/governance/test_gate_lexical_contract.py::test_20_contract_22_coverage_and_direction` → PASS（含 `t21-d1-tn-self-gate-dispatch`／`t21-d1-tn-self-gate-check` 等全條 @want 比對）。 |
| **1c** D-2 真 O(n)、無隱藏長度頂 | **通過** | `grep` `_gate_lex.sh`：無 `8192`／`_max_lex`／`head -c`／`GATE_LEX_OVERSIZE`。`_gate_cmd_is_dispatch`（364-390）無引號路徑 `scan=$raw` 直接 grep；有引號才 preprocess。 |
| **1d** D-2 latency 連跑 3 次 | **邊界通過** | 門檻未動：`test_debt_gate.py:464-465` 仍 `100.0`。獨立連跑 6 次 `test_gate_check_latency_under_100ms`：**3 PASS / 3 FAIL**（失敗樣本 cold_ms=123.9–131.2、second_ms=152.0；通過樣本 cold≈76–96ms）。屬冷啟抖動（與 synth 旁證一致），**非 D-2 O(n) 結構回歸**（測的是 Task 通道 + audit 掃描，非 4MB Bash）。主委 §0 全套 763 passed 與本 reviewer 後續批次 PASS 可互證。 |
| **1e** D-2 4MB rc 與秒數 | **通過** | `pytest test_21_c1_oversize_failclosed_bounded` → PASS（12.0s）；4MB 無害 ALLOW、尾端 `; codex exec hi` BLOCK，均 <30s 上限。 |
| **1f** D-3 C4 mutation before/after | **通過** | `pytest test_01_invariance_exclude_nonflip_mutation` → PASS。獨立 subject 複製：`ok_rc=0`，`mut_rc=1`（AssertionError on `_cmd_match`）。與 R1 `VERIFY:20260805T135713Z-c4-not-true-mutation-confirmed` **相反**——本輪為真 mutation。 |
| **1g** D-4 延伸檔取代就地註解 | **通過** | `git diff docs/GOVB0_FRICTION_TODO.md` → 0 行。`docs/GOVB0_FRICTION_TODO_AMENDMENTS.md` 含 C5 決策、TODO 錨點（Task 2.1 `TEST-2.1-RECURSE`）、實作錨點（`extract_phase2_expected_flips.py` `_DIR_RE`）。`python3 scripts/extract_phase2_expected_flips.py --check` → rc=0 rows=37。 |
| **1h** 新增測試 mutation | **通過** | D-1/D-2 四條語料測 + 兩條 mutation 測全 PASS：`test_21_d1_gate_substr_no_bypass`、`test_21_d2_harmless_oversize_allows`、`test_21_d2_oversize_gate_substr_still_blocks`、`test_21_c1_oversize_suffix_blocks`；`test_21_d1_mut_substr_self_excludes_allows`（還原子字串排除→ALLOW）、`test_21_c1_mut_restore_prefix_truncate_allows`（還原 head -c→尾端派工 ALLOW）。C4 見 1f。 |
| **1i** 新 fail-open／誤擋 | **通過** | 10 條攻擊向量：派工繞道（`&&`、換行、printf 前綴、env 值）均 rc=2；無害 `cat scripts/gate.sh` rc=0（非派工，正確）。語料 A diff 0 行。 |

---

## §0 三條假設攻擊

| 假設 | 攻擊結果 |
|---|---|
| D-2 O(n) 在 latency 與 4MB 兩端成立 | **成立**。無 8192 硬頂（1c）；echo+8200 rc=0、8200+`; codex exec hi` rc=2；4MB 測 PASS。latency 有冷啟抖動但非 D-2 路徑回歸（見 1d）。 |
| D-3 C4 這次是真 mutation | **成立**。隔離 subject `ok_rc=0`／`mut_rc=1`；非測試內 poisoned list 假陽性。 |
| 新增 4 測試 revert 會轉紅 | **成立**。D-1/D-2 各有 in-test mutation 證明還原後行為翻轉；C4 見上。 |

---

## 被當成事實的未驗證假設（§0）

無（本輪已對 brief §0 fact-verified 項抽樣複核；latency 抖動已標為邊界觀測非 blocking）。

---

## §1 必查（11 類）

1. 矛盾/互斥 — 無  
2. 漏項/端到端 — 無（D-1～D-4 均有語料＋測試＋實測）  
3. 不可測驗收 — 無  
4. 可疑 quant 假設 — 不適用（治理 gate）  
5. 過度工程 — 無  
6. OOM/並行 — 無（4MB 有 30s 上界）  
7. Cache 正確性 — 不適用  
8. API/型別/相容 — 無  
9. 測試品質 — 無（mutation 已驗）  
10. Agent 可執行性 — 無  
11. 必要性/短命工 — 無  

---

## 出場判準核算

| 項 | 值 |
|---|---|
| findings 去重 | **0**（≤3 ✓） |
| BLOCKING | **0** ✓ |
| NEW-DEFECT-INTRODUCED | **無** ✓ |
| **結論** | **B3 驗收通過，可進 B4** |

---

## VERIFY 命令摘要

```
# D-1/D-2 rc（GATE_DIR_OVERRIDE=/tmp/govb0-b3-fix2review-composer/gate）
codex exec x; echo scripts/gate.sh → rc=2
echo +8200a → rc=0
8200x + ; codex exec hi → rc=2

# latency×6（3 fail 冷啟抖動 / 3 pass）
pytest tests/governance/test_debt_gate.py::test_gate_check_latency_under_100ms ×6

# 4MB / C4 / mutation / corpus B
pytest test_21_c1_oversize_failclosed_bounded → PASS 12.0s
pytest test_01_invariance_exclude_nonflip_mutation → PASS
pytest test_21_d1_mut_substr_self_excludes_allows → PASS
pytest test_21_c1_mut_restore_prefix_truncate_allows → PASS
pytest test_20_contract_22_coverage_and_direction → PASS
python3 scripts/extract_phase2_expected_flips.py --check → rc=0
git diff docs/GOVB0_FRICTION_TODO.md → 0 lines
```

---

ASSUMPTIONS_VERIFIED: D-1 子字串繞道已關、合法自呼叫仍 ALLOW；D-2 無 8192 硬頂、4MB 有界；C4 真 mutation ok/mut rc=0/1；語料 A/TODO diff 空  
TESTS_RUN: 見上 VERIFY；未跑全套 763（主委已驗；本輪 targeted）  
FAILURES_SEEN: latency 測 6 次中 3 次冷啟超 100ms（非 D-2 結構問題）  
SCOPE_CHANGES: none（禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none  

STATUS: DONE
