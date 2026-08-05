# GATELEX-REDESIGN2 — Composer 委員會諮詢產出

**family**: COMPOSER | **task-id**: GATELEX-REDESIGN2 | **brief**: `handoffs/20260805-GATE-LEX-REDESIGN-BRIEF.md`
**date**: 2026-08-05 | **禁改碼**: 本輪僅分析＋實測

---

## Verdict：需修補後派工

E-1（真換行 fail-open）與 E-2（awk O(n²)）均已獨立重現；斷路器條件成立，**不宜再發局部熱修補**。§B「單趟 FSM、不轉換」方向正確，但表格**未覆蓋契約 5／10 與 claude 子模式**，不可原樣開工。建議獨立成批 `GOVB0-B3R-LEX`（Hybrid C），排在 B3 review 之後；latency 測試**維持現狀 (a)**。

---

## §0 前提宣告

### 被當成事實的未驗證假設（挑戰 brief §0）

| brief 宣稱 | 標記 | Composer 覆核 |
|---|---|---|
| E-1 與 E-2 有共同根因（§B-1） | **assumed** | **部分推翻**——同屬「grep/awk 近似詞法」架構族，但 immediate fix 不同：E-1 是 `_gate_cmd_is_self_gate` 誤判 + 早退；E-2 是 `out=tok cc` O(n²)。修 E-2 不解 E-1。 |
| 主委指令 <10K ⇒ 非即時風險 | **assumed** | 未量測歷史 `cmd_head` 分布；但 Write/Edit 超大 payload 可觸發 E-2（200K→4.8s 已驗）。 |
| 763 passed（brief §0） | fact-verified | **覆核一致**：`pytest tests/governance -q` → `763 passed in 296.40s` rc=0 |
| E-1 換行 rc=0 | fact-verified | **覆核**（真換行，非 JSON 字面 `\n`）：見 RECHECK 區 |

### 本委員 fact-verified 摘要

```
# E-1（真換行）
jq -nc --arg c $'bash scripts/gate.sh\ncodex exec hi' '{tool_name:"Bash",tool_input:{command:$c}}' \
  | bash scripts/gate_check.sh; echo rc=$?   → rc=0（fail-open）
jq -nc --arg c 'bash scripts/gate.sh; codex exec hi' '…' | bash scripts/gate_check.sh; echo rc=$? → rc=2

# E-1 根因鏈
. scripts/_gate_lex.sh
_gate_cmd_is_self_gate $'bash scripts/gate.sh\ncodex exec hi'; echo self=$?      → self=0（誤判）
_gate_cmd_is_dispatch $'bash scripts/gate.sh\ncodex exec hi'; echo disp=$?     → disp=0（會擋，但到不了）
printf '%s' $'a\nb' | grep -Eq '\n'; echo literal=$?  → 1
printf '%s' $'a\nb' | grep -Eq $'\n'; echo real=$?    → 0

# E-2
. scripts/_gate_lex.sh && _gate_lex_preprocess "$(awk 'BEGIN{for(i=0;i<200000;i++)printf"x"}')"
→ n=200000 elapsed=4.820s（e2.txt）

# governance
pytest tests/governance -q → 763 passed in 296.40s rc=0

# latency
pytest tests/governance/test_debt_gate.py::test_gate_check_latency_under_100ms -q -s
→ cold_ms=75.2 second_ms=76.2 samples=[79.9,75.2,75.2] real_audit_lines=34796 PASSED
```

---

## COMPOSER-R17-P0-01

**斷言**: E-1 主因不是 §B-1 所稱「grep 逐行漏檢」，而是 `_gate_cmd_is_self_gate` 用 ERE 字面 `\n` **無法匹配真換行** → 換行複合命令被當自呼叫 → `gate_check.sh:211-212` **早退 exit 0**，`_gate_cmd_is_dispatch` 永不執行。

**碼證**: `scripts/_gate_lex.sh:354` `grep -Eq '[;&|`]|\$\(|\n'`；RECHECK 見 §0 fact-verified 區。`dispatch_newline=0` 證明 match_scan **會**命中第二行 codex。

**來源摘要**: scripts/_gate_lex.sh#debe1484a7e5

[BLOCKING] 信心度=High；若 implementer 只修「全字串 grep 錨定」而不動 self_gate 順序／換行檢測，E-1 仍 fail-open。

---

## COMPOSER-R17-P1-01

**斷言**: §B-2 結構化輸出（command position + first token）**不能導出契約 5（路徑正規化 `./`／`//`／`../`）**，須獨立 `_gate_lex_normalize_path` 子模組（現行亦在 B4 Task 2.4）。

**碼證**: `docs/GOVB0_FRICTION_SPEC.md` Task 2.0 第 5 項；`scripts/_gate_lex.sh` 無 normalize 實作。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#283298bb1e8a

[MAJOR] 信心度=High；照 §B 原表開工會在路徑變形向量 fail-open。

---

## COMPOSER-R17-P1-02

**斷言**: §B-2 低估契約 10（heredoc 七條機械規則 + ⑥允許清單 + ⑦ fail-closed + 多 heredoc 順序）；不能由「span 內不產 command position」一句帶過——現行 Pass 1 已 ~110 行 awk。

**碼證**: `docs/GOVB0_FRICTION_SPEC.md:196-218`；`scripts/_gate_lex.sh:86-139`。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#283298bb1e8a

[MAJOR] 信心度=High；無 heredoc 子規格則語料 B heredoc 區塊必紅。

---

## COMPOSER-R17-P2-01

**斷言**: §B-2 自我豁免「command position 總數 == 1 且 token 為 gate 腳本」對 `bash scripts/gate.sh dispatch …` **語意不足**——first token 是 `bash` 非 `gate.sh`；須「單一簡單命令 + gate 腳本路徑匹配」谓词（現行 `_gate_cmd_is_self_gate:358-359` 已處理，但 §B 表未寫清）。

**碼證**: D-1 三樁 rc=0（`bash scripts/gate.sh dispatch --task-id X` 等）。

**來源摘要**: scripts/_gate_lex.sh#debe1484a7e5

[MINOR] 信心度=Medium；B-2 方向對，predicate 須寫進 mini-SPEC。

---

## COMPOSER-R17-P2-02

**斷言**: latency 100ms **有 P16 SPEC 出處**；本機 34796 行 audit 上 cold_ms=75.2ms 通過——**(c) 調高門檻是改契約，非「無依據放寬」**；本輪不建議。

**碼證**: `docs/P16_COMMITTEE_DEBT_SPEC.md` Task 3.1；`pytest …test_gate_check_latency_under_100ms -s` receipt 見 §0。

**來源摘要**: docs/P16_COMMITTEE_DEBT_SPEC.md#56915f8bdab3

[MINOR] 信心度=High。

---

FINDINGS_COUNT: 5

---

## 逐項核對表

### 問1 — E-1 與 E-2 是否真有共同根因？

**結論：架構族相同（無單一 tokenizer），immediate root cause 不同，不是單一 bug。**

| 缺陷 | 根因（本委員實測） | 與 §B-1 差異 |
|---|---|---|
| **E-1** | `_gate_cmd_is_self_gate` 換行檢測失效 + `gate_check.sh:211` 早退 | §B 歸因 grep 逐行；實際 dispatch **會**命中 line-2，被早退截斷 |
| **E-2** | `_gate_lex_preprocess` 多處 `out=out c` / `tok=tok cc` O(n²) | 與 §B-1 一致 |

### 問2 — §B 是否可行？11 契約能否由提案②輸出導出？

**方向可行；現行 §B-2 表格不可直接開工。** 語料 A 行數：`grep -c '^{' tests/governance/fixtures/gate_invariance_corpus.txt` → **30**（未改）。

| # | 契約 | B-2 可導出？ | 缺口 |
|---|---|---|---|
| 1 | 引號內 `;|&|` 非分隔符 | ✅ | quote 內不 emit command position |
| 1b | 跨行引號狀態 | ✅ | 單趟 FSM 跨 `\n` |
| 2 | 命令位置（含 `(` `` ` `` `$(` `&&` `\|\|` eval xargs） | ⚠️ | 需完整 position 觸發表；first token 不足以涵蓋 eval/xargs 後位 |
| 3 | `-c` / eval 遞迴 | ✅ | inner span + depth 遞迴 |
| 4 | 引號路徑 | ✅ | quoted token 原子化 |
| 5 | 路徑正規化 | ❌ | **需獨立 normalize** |
| 6 | 未閉合引號 → fail-closed | ✅ | fail 訊號 |
| 7 | unquoted `-c` → BLOCK | ✅ | unquoted 引數抽取 |
| 8 | 遞迴 ≤3 | ✅ | depth counter |
| 9 | 跳脫引號 | ✅ | 邊界不明 → fail |
| 10 | heredoc 七規則 | ⚠️ | **需完整 heredoc 子 FSM** |
| — | claude `-p/--print` | ⚠️ | §B 表未列；現行 `_gate_lex_match_scan:201` 獨立於 executor 名單 |

**攻擊 §B**：主委風險 #2 **成立**——11 項中 **1 項不可導出、3 項需顯式擴規**。

### 問3 — 若 §B 不可原樣採納，替代設計？

**推薦 Hybrid C（單趟 FSM + 子模組，保留語料 B 測試面）**

1. **核心**：POSIX awk **單趟** FSM，emit `(pos, argv0)` 串列 + fail flags；**禁止** materialize 改寫字串（`out=out c`）。
2. **子模組**（同檔）：`_gate_lex_normalize_path`（契約 5）、port 現 Pass1 為 `_gate_lex_heredoc_scan`（契約 10）。
3. **判定**：查 emit 串列替代 grep；**自我豁免** = 單一簡單命令 + gate 路徑匹配（**非** grep 字面 `\n`）。
4. **過渡**：保留 D-2「無引號/heredoc 走 raw」至 FSM 穩定；FSM 上線後可移除 preprocess。
5. **禁**：再疊「preprocess + grep」；禁 length 截斷 fail-open。

**最小替代（僅對照，不作本批建議）**：調 self_gate 順序（先 dispatch 再 self）+ `$'\n'` 檢測——斷路器已禁主委再發此類熱修補。

### 問4 — 改多少？

| 選項 | 評估 |
|---|---|
| 全面 §B 重寫 | 正確方向；觸發膨脹升級；須 mini-SPEC + adversarial |
| 局部熱修 | **斷路器已禁**（連續修補引入新缺口） |
| 維持現狀 + 具名殘留 | ❌ E-1 是 **P0 fail-open**（真換行 rc=0 已驗）；E-2 可列殘留但不可對 E-1 妥協 |

**建議幅度**：詞法核心重寫（Hybrid C），非推翻 governance 語料／測試架構。

### 問5 — 排哪一批？

**獨立成批**（建議 `GOVB0-B3R-LEX` 或 Phase 2.0′）：

1. **B3 code review**（進行中）——標記 E-1/E-2 為 **BLOCK merge**。
2. **本諮詢收斂** → mini-SPEC（補契約 5/10/claude/self_gate predicate）→ 實作。
3. **B4**（2.2/2.3/2.4）與 lex 同熱路徑；**2.4 路徑正規化建議併入 B3R-LEX**，2.2/2.3 可緊接其後。

**不建議**塞回已 frozen 的 B3 熱修補。

---

## §B 三段獨立評估

### 提案① 共同根因 — **部分同意、需修正**

- **同意**：「先轉換再 grep、無單一 tokenizer」是 E-2 與維護風險的正確診斷。
- **推翻**：E-1 **不是** match_scan 逐行漏檢，而是 **self_gate `\n` 假陰性 + 早退**（R17-P0-01）。兩 defect **不共享 single fix**。

### 提案② 不轉換只偵測 — **架構採納，表格未完工**

- O(n)／移除長度上限／結構化查詢：✅
- 必補規格：**path normalize**、**heredoc FSM**、**self_gate predicate**、**claude 模式**
- awk 單趟記憶體：bash 3.2 + macOS awk **可行**；heredoc body 跳過仍 O(body) 時間，可接受。

### 提案③ 主委風險 — **覆核**

| # | 主委風險 | Composer |
|---|---|---|
| 1 | awk O(1) 記憶體 | 單趟 FSM 可行；禁 `out=out c` |
| 2 | 11 契約能否導出 | **#5 不能；#2/#10/claude 需擴規** |
| 3 | 改動規模 | 中→大；獨立批合理 |
| 4 | 語料 A 不可改 | invariance **30** 行；`pytest tests/governance -q` → **763 passed** |

---

## §D latency 諮詢

### 問D1 — 抖動根因

**主因：Python `_debt_ledger_core.py` 冷啟 + 進程 spawn；非 audit 行數結構退化。**

| 因子 | 實測 | 判定 |
|---|---|---|
| audit 規模 | 34796 行；cold_ms=**75.2** samples=[79.9,75.2,75.2] | **排除**行數主因 |
| debt_ledger 單獨 | 3× **~60ms** rc=1 | 佔 gate_check 大部分 |
| Task 通道 8× | **81.6–88.2ms**（無 token，rc=2） | 穩定 <100ms |
| Bash+引號 5× | **36.4–37.2ms** | preprocess 常數小 |
| 詞法 E-2 | 200K→4.8s | 與 latency 測試路徑（**Task 通道**）無關 |

**§B 依賴**：lex 重寫後 Task 路徑 latency **可能略升或略降**；D1 量測在 FSM 落地後需 **一輪** receipt 重 baseline，現建議不依賴 preprocess 成本。

### 問D2 — 選項比較

| 選項 | 建議 | 理由 |
|---|---|---|
| **(a) 維持現狀** | **✅ 首選** | 3× pytest + receipt 全過；287ms 為單次 outlier（HANDOFF 已記） |
| (b) 中位→N 次取最小 | ❌ | 見 D3 |
| (c) 調高門檻 | ❌ | 有 P16 SPEC；改契約 |
| (d) 測試隔離 | 可選低優先 | 略減並行干擾；非主因 |
| (e) 只 assert 中位、放寬第 4 次 | ⚠️ | 現假紅率低，收益小 |

### 問D3 — 反例：最小值統計

**反例（推翻「真變慢時 min 也超」的充分性）**：延遲呈 **競爭雙模**——常態 110–130ms（CPU 競爭），偶發 70–80ms（閒置 + page cache）。程式**結構性變慢**時 p50 已 >100ms，但 min-of-5 仍有 `(0.3)^5` 量級機率撿到一次「幸運快 sample」而通過；**min 掩蓋 p50 退化**。

**RECHECK**: 背景 `yes`×3 + 連跑 5 次 gate_check，比較 min vs median 分叉（本委員未量化，邏輯反例成立）。

### 問D4 — 值得花力氣嗎？

- **抓過退化嗎？** `git log -S'test_gate_check_latency_under_100ms'` → 僅 `141e4b8` 引入；驅動 `_debt_ledger_core.py` 直呼叫。**未見** git 證據抓過 B3 awk 回歸。
- **偶發紅損失**：c2a351f audit 封存為 **287ms 假陽性過度反應**（fd6dc77 已撤回）——損失在工程時間，非安全。
- **結論**：測試 **保留**（brief OUT-OF-SCOPE 禁刪）；**不值得**再投入調門檻／archive audit。

### 問D5 — 100ms SPEC 出處

- **出處**：`docs/P16_COMMITTEE_DEBT_SPEC.md` Task 3.1「單次 `gate_check` 耗時 < 100ms」；`scripts/gate_check.sh:123` 註解同引。
- **理由**：PreToolUse **每次工具 call** 都跑；100ms = 可接受互動上限 + debt cold path budget。
- **(c) 是否放寬既定契約？** **是**——有明確 SPEC。

---

## 出場判準核算

| 出場條件 | 狀態 |
|---|---|
| E-1/E-2 有設計戳記（三家 consult） | 本檔 COMPOSER 戳記；待 codex/grok 同輪 |
| mini-SPEC 補契約 5/10/self_gate/claude | **未做**（本輪 consult only） |
| `pytest tests/governance -q` rc=0 | **763 passed**（本委員實跑） |
| 語料 A 零改（30 行） | **未改** |
| 語料 B 全綠 | 現況綠；E-1 未進語料 B（設計缺口） |
| B3 merge | **建議 BLOCK** 直至 B3R-LEX |
| latency | **維持 (a)**；FSM 後一輪 receipt |

---

## 建議下一步

1. **BLOCK B3 merge** 直至 E-1/E-2 設計三家收斂。
2. 主委寫 **`GOVB0-B3R-LEX` mini-SPEC**（Hybrid C + 上表缺口）；一輪 adversarial。
3. 實作 + `pytest tests/governance -q` + 語料 A **30** 行零改 + 語料 B 全綠 + **新增 E-1 真換行 TP 語料**。
4. latency **維持現狀**；FSM 落地後一輪 receipt。
5. 管線：B3 review → B3R-LEX → B4（2.4 併 B3R 優先）。

---

ASSUMPTIONS_VERIFIED: E-1 真換行 fail-open；E-2 O(n²) n=200K→4.82s；self_gate/dispatch 鏈；763 governance passed；latency cold_ms=75.2；語料 A=30 行；debt_ledger ~60ms
TESTS_RUN: pytest tests/governance -q → 763 passed 296.4s rc=0；pytest test_gate_check_latency_under_100ms ×4（3 quiet + 1 -s）；E-1/E-2/self_gate 手動探針；bash scripts/restore_golden_inventory.sh rc=0
FAILURES_SEEN: none（本輪未改碼）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
