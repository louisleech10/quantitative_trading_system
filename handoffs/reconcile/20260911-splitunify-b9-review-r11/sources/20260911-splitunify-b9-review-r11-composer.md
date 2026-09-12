# SPLITUNIFY D-002 閉合輪 R11 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R11  
family: composer  
findings-round: R11  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第十一次修訂 v11）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: mutation 32 條、ID 01–32 連續 | **fact-verified** | `rg -c '^\| \`M-SU-D2-' docs/SPLITUNIFY_SPEC.D-002.md` → **32**；`for i in $(seq -w 1 32); do rg -q "M-SU-D2-$i" ...` → 無缺號 |
| brief fact-verified: register 25 條與標題／§R 一致 | **fact-verified** | `rg '^\| \`C5-' docs/SPLITUNIFY_SPEC.D-002.md \| wc -l` → **25** |
| brief fact-verified: golden 11 鍵、無 v8 檔 | **fact-verified** | `jq -r 'keys[]' tests/golden/splitunify/splitunify_golden.json` → 11 鍵；`test -f ...v8.json` → **MISSING**（施工前預期） |
| brief fact-verified: 三閘 rc=0 | **fact-verified** | `obligation_block_check` rc=0；`doc_format_precheck` rc=0 |
| brief assumed: register 25 條涵蓋全部單鍵消費面 | **assumption，否證** | (5.5) 列 pipeline／API／前端面板，register 無對應行 → **P1-01** |
| brief assumed: (G-4e) 人手填值顯著降低三份同錯 | **assumption，部分成立** | 探針：獨立 expected `g4e_pass=False`、三份同錯 `g4e_pass=True`；人手填錯仍會三份一致——SPEC 已登記殘餘誠實邊界，標註**足夠** |
| brief assumed: baseline 刪 `n_test` 不打破下游 | **assumption，未重跑** | `baseline.py:120` 仍寫 `n_test`；`splitAuthority.ts` 之 `n_test` 語意為 **metadata.split_unify** 事件數，與 baseline 舊鍵分離——刪 baseline 鍵不應動前端 disclosure 路徑 |
| brief assumed: M6 落地順序 (i)–(iv) 無法繞過 | **assumption，否證** | `--write` 仍可全檔覆寫主 golden → **P1-02** |
| brief assumed: M5 座標二擇一窮盡 | **assumption，第三路徑存在** | 逐 symbol 切片 ts/symbols 使 local 0..n-1 對齊，可不經 global rebase 通過單標 validator，但**不滿足** §V「多標的交錯批 global positions 非連續」斷言——二擇一對該斷言仍窮盡 |

## 必答 1–6

**1. 本家 R10 finding 是否閉合**

| ID | R10 斷言 | v11 落點 | 判定 | 確認方式 |
|----|----------|----------|------|----------|
| COMPOSER-R10-P1-01 | (6.2) 與 Task 9.4 互斥 | L125 刪等價、拆雙量、刪舊鍵；§V Task 9.4 三條 | **CLOSED** | `sed -n '125p;244p;268p' docs/SPLITUNIFY_SPEC.D-002.md` |
| COMPOSER-R10-P1-02 | §V metadata 只驗鍵 | §V L253 升級三層**值相等** | **部分閉合** | 值相等已修；Task L183「整鏈」仍未進 §V 可執行入口 → **P2-01** |
| COMPOSER-R10-P2-01 | M-31 無 §V 母斷言 | §V L268 Task 9.4 三條 | **CLOSED** | 對讀 L268 與 mutation M-31／M-32 |

**2. 檢驗主委自證六條（十項改動 M1–M8＋自產 A/B）**

| 項 | 宣稱落點 | 複驗 | 主委漏掉 |
|----|----------|------|----------|
| M1 (G-4e) | §G L162、§V #3、明禁共用 helper | **落在** | — |
| M2 metadata 值相等 | §V L253 | **落在** | 整鏈 E2E 入口仍未進 §V（→P2-01） |
| M3 baseline 三處同改 | (6.2) L125、Task 9.4 L244、§V | **落在** | — |
| M4 Task 9.4 §V | §V L268 | **落在** | — |
| M5 座標 adapter | Task 9.2b 步驟 0③、§V adapter 母斷言 | **落在** | — |
| M6 v8 不可變 | §G (G-4d)①、(iv)、§V #6 | **散文落在、可繞過** | `--write` 主檔無護欄（→P1-02） |
| M7 register 25 | (5.6) 表、標題、§R | **落在** | (5.5) 三處未進表（→P1-01） |
| M8 AST 觸發 | §N、TODO §E | **落在** | — |
| 自產 A 刪冗餘第 4 條 | Task 9.2b L221 | **落在** | — |
| 自產 B M-32 | mutation 表、條數 32 | **落在** | — |

**第七種自證形態（本輪新增）**：Task 正文要求之**驗收形態**（如「整鏈 E2E」「只增鍵不覆蓋」）未同步寫進 §V／`--write` 護欄——v11 修了「鍵→值相等」與「mutation→§V」，但未修「散文 E2E／版本化 freeze 護欄」與 §V 的對稱。

**3. 攻 (5.6) register**

**立場**：25 條與 (5.1)–(5.4) **大體對齊**，但**(5.5) 記帳鏈至少三處未登記**——register 宣稱唯一計數依據與 §N「可能不完整」並存，實作者按表施工會漏 `Task 9.4` 門檻路徑（→P1-01）。`C5-15`／`C5-16`／`C5-17` 標 `—` **可接受**——甲類維持不動、誤改不會靜默取錯複合鍵列，具名缺口即可，不必硬湊 mutation。

**4. 攻 (G-4e) 殘餘誠實邊界**

**立場**：人手填 `expected_side` **優於**第三次編碼（探針情形 A 可攔不對稱同錯），但**無機械解**消除「填值者照錯誤理解填」——與 (G-4c) 逐行重寫同性質。SPEC §G L162 已明寫「散文紀律、非機械保證」，§V L260 明禁共用 helper；**標註足夠誠實**，不另開 finding。

**5. 攻 M6／M5**

**M6 繞過構造**：換錨後直接 `python scripts/freeze_splitunify_golden.py --write`——現行 L373-386 `golden_path.write_text(...)` **全檔覆寫**，可把新成員集寫進既有 `g1_membership`／`g3b_oracle`，跳過 (i) 建 `v8.json`、(ii) 只寫 `g1_membership_v9`；§V 唯讀路徑會紅，但 `--write` 路徑無「拒改 11 鍵」句（僅拒 `.v8.json`）→ **P1-02**。

**M5 第三種座標情形**：對**每個 symbol** 傳 `ts[sym_mask]`／`symbols[sym_mask]` 且 `plan.row_index` 用 0..n-1 局部序——validator 可綠，但**不覆蓋** §V「多標的交錯批、global positions 非連續」斷言；實作若只走 per-symbol 切片會在該 §V 斷言紅。二擇一對**該斷言所涵蓋之批**仍窮盡。

**6. 修訂引入的新問題**

| 衝突 | 說明 |
|------|------|
| (5.6) vs (5.5) | register 缺 pipeline／disclosure／前端計數面（P1-01） |
| Task 9.1 vs §V | 整鏈散文 vs 可分層 mock（P2-01） |
| M6 §V vs freeze `--write` | 主檔 immutable 只在 read 路徑斷言（P1-02） |
| D-001／golden | 無新衝突；v8 檔待 Task 9.5 施工 |
| TODO §E | AST 觸發與 SPEC §N 已同步 |

## §1 必查摘要（11 類）

1. **矛盾**：register「唯一 25」vs (5.5) 未全登記 — **有**（P1-01）
2. **漏項**：Task 9.4 門檻路徑未進 register — **有**
3. **不可測**：Task 9.1 整鏈 E2E 未進 §V — **有**（P2-01）
4. **quant**：(G-4e) 殘餘已誠實標註 — **無新 BLOCKING**
5–11. 其餘 — **無新增 BLOCKING**

## COMPOSER-R11-P1-01

**斷言**: `(5.6)` register 宣稱 25 條為唯一施工清單，但 `(5.5)` 明列之 pipeline summary 計數（`split_projection.py:562` 一帶）、`metadata.split_unify` disclosure 鏈、前端 `splitAuthority.ts` 事件數顯示**均未登記**，實作者按 register 逐條施工會漏改 tier_min 靜默繞過路徑。

**碼證**: `(5.5)` L82 逐字列「`pipeline` 產出之 `n_train`／`n_test`／`n_purged`、其 API 模型、前端事件批面板」；`rg '^\| \`C5-' docs/SPLITUNIFY_SPEC.D-002.md` 僅 **25** 行且無 `:562`／`splitAuthority`／`build_split_unify_disclosure`；Task 9.4 L242 有改法散文但無 register 行。RECHECK: 對讀 (5.5) vs C5-01..25；`nl -ba momentum/Analysis/event_samples/split_projection.py | sed -n '559,570p'`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。複合鍵後 `n_test=2` 而真實事件數=1 可靜默繞過 `tier_min_test_events`（§RISK d）。**修法**：register 增 `C5-26`～`C5-28`（pipeline summary 計數、disclosure `n_test`、前端 splitAuthority），標題改 **28 條**，§R／§RISK 同步；各列 Task 9.4 與既有 §V 去重斷言。**可行性**：純 SPEC 表行擴充；碼側改法已在 Task 9.4 L242 寫死，只需把敘述層升為 register 行。

## COMPOSER-R11-P1-02

**斷言**: M6 落地順序 (i)–(iv) 可被 `--write` 全檔覆寫主 golden **繞過**——SPEC 只寫 `--write` 拒寫 `.v8.json`，未要求 `--write` 不得改動主檔 11 個既有頂層鍵或不得直寫 `g1_membership`。

**碼證**: `sed -n '373,386p' scripts/freeze_splitunify_golden.py` → `golden_path.write_text(json.dumps({**actual}))` 全檔覆寫；`test -f tests/golden/splitunify/splitunify_golden.v8.json` → **MISSING**；§G (G-4d)① (iv) 僅「`--write` 對 `.v8.json` 一律拒寫」。繞過：換錨後不建 v8、直接 `--write` 改 `g1_membership`。RECHECK: 對讀 §G (G-4d)① vs freeze `--write` 分支。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。Task 9.5 重凍可把換錨差異寫進舊鍵而無 v8 錨與 v9 平行鍵，M-SU-D2-29 讀路徑紅但 write 路徑仍可污染。**修法**：§G／§V 增 `ASSERT WHEN --write 會改動 splitunify_golden.json 之 11 個既有頂層鍵任一值 OR 寫入 g1_membership 而非 g1_membership_v9 THEN raise`；`--write` 只允許增 `g1_membership_v9`／`g3b_oracle_v9` 與其他新鍵。**可行性**：freeze `main()` 已有 read 路徑比對骨架；寫入前 diff 舊檔 11 鍵即可機械實作（與 §V #6 對稱）。

## COMPOSER-R11-P2-01

**斷言**: v11 把 §V metadata 升級為值相等，但 Task 9.1 L183 要求的 **producer→summary→metadata 整鏈 E2E** 仍未寫入 §V——實作者可用三個 mock 物件手塞相同 `discarded` 通過 §V，而 `ic_filter_orchestrator.py:1530-1534` 仍不傳 `discarded`。

**碼證**: `rg '整鏈' docs/SPLITUNIFY_SPEC.D-002.md` 僅命中 Task L183 與沿革，§V L253 無「經 orchestrator／pipeline」；`build_split_unify_disclosure`（`split_projection.py:123-180`）簽名仍無 `discarded`；caller `ic_filter_orchestrator.py:1530-1534` 仍只傳 `n_test`／`test_timestamps_ms`／`per_symbol_counts`。RECHECK: 對讀 Task 9.1 L183 vs §V L253；`rg 'discarded' momentum/Analysis/ic_filter_orchestrator.py` → 0。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a731f4b623a1;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293

[MAJOR] 信心度=High。R10 COMPOSER/CODEX P1-02 之殘餘：孤立 builder／disclosure 單測可綠，真實 IC 路徑計數仍可在 orchestrator 邊界遺失。**修法**：§V `Task 9.1` 增 `ASSERT 經 ic_filter_orchestrator（或 EventSamplePipeline.run 等價 derive）之 discarded_rows_by_feature_tf 與 metadata.split_unify 同值`；builder 增 `discarded` 參數並改 caller。**可行性**：Task 9.1 L183 已寫 handoff 路徑，§V 只需把「整鏈」從散文降為可執行斷言（與 Task 9.2 端到端句式對齊）。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` | **rc=0** |
| `rg -c '^\| \`M-SU-D2-' docs/SPLITUNIFY_SPEC.D-002.md` | **32** |
| `rg '^\| \`C5-' docs/SPLITUNIFY_SPEC.D-002.md \| wc -l` | **25** |
| `jq -r 'keys[]' tests/golden/splitunify/splitunify_golden.json \| wc -l` | **11** |
| `python handoffs/20260912-splitunify-b9-probe-g4e-triple.py` | 情形 A/B 皆符合預期 |
| `rg '16 處' docs/SPLITUNIFY_SPEC.D-002.md`（正文） | 僅沿革／「原寫」說明，無活躍矛盾標題 |
| `rg 'validate_split_pair_integrity' momentum/Analysis/event_samples/split_projection.py` | **0**（施工前預期） |

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R11-P1-01,COMPOSER-R11-P1-02
CLOSED: COMPOSER-R10-P1-01,COMPOSER-R10-P2-01

ASSUMPTIONS_VERIFIED: mutation 32／register 25 計數；golden 11 鍵；G-4e 探針；R10 三條逐條對讀 v11；M1–M8＋自產 A/B 落點表  
TESTS_RUN: 見「複驗」表；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r11-composer.md --family composer`（交件自跑）  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）

STATUS: DONE
