# Reconcile — 20260805-gatelex-redesign2

**來源** 20260805-gatelex-redesign2-codex.md, 20260805-gatelex-redesign2-composer.md, 20260805-gatelex-redesign2-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併。**主委提案①被推翻、提案②被判不足**；
詞法層改寫獨立成 **B3.5**（先訂輸出契約＋原型＋差分/突變 oracle，通過才進 B4）；
**latency 維持現狀 (a)**，主委 min-of-N 提案**撤回**。

### 🔴 主委被推翻的兩項（三家獨立指出）

| 主委原判 | 三家裁定 | 證據 |
|---|---|---|
| 提案①：E-1 根因＝「先轉換再 grep」架構、grep 逐行漏檢 | ❌ **推翻**。真正根因＝`_gate_cmd_is_self_gate` 以 ERE **字面 `\n`** 比對，**無法匹配真換行** ⇒ 換行複合命令被當自呼叫 ⇒ `gate_check.sh:211-212` **早退 exit 0**，`_gate_cmd_is_dispatch` 根本沒執行 | `COMPOSER-R17-P0-01`、`GROK-R17-P0-02`（各自獨立實跑定位） |
| E-1 與 E-2 同根因 | ❌ **推翻**。共同**背景**是缺單一結構化 lexer，但**根因獨立**：E-1 是自呼叫判定的語義缺口，E-2 是 awk 字串累加的超線性物化 | `CODEX-R17-P0-01`、`GROK-R17-P1-01` |

⇒ 主委在 §B 自承「共同根因判斷未經任何獨立驗證」，該自承是對的——**確實錯了**。
**價值**：若照原提案派工，會改錯地方（動 preprocess 而非 self-gate predicate）。

### 🔴 latency：主委提案被具體反例推翻，三家一致「維持現狀」

主委原辯護：「程式真的變慢時，最小值一樣會超標，故 min-of-N 非統計手法達標」。

> <!-- claim-context: discussion -->
> **`GROK-R17-P1-02` 的反例**（逐字轉述委員判定，非主委實跑）：
> 真實冷路徑已退化到 >100ms 時，min-of-N 仍會**高機率全綠**——
> 因為只要 N 次中有一次落在快尾，門檻就過。
> ⇒ **確為「統計手法充當達標」**，違反使用者定死的測試品質條款。**主委提案撤回。**

三家對 latency 的一致結論：

| 項 | 結論 | 來源 |
|---|---|---|
| 選項 | **(a) 維持現狀** | 三家一致 |
| 100ms 出處 | **有依據**：`docs/P16_COMMITTEE_DEBT_SPEC.md:507` 明文 | `COMPOSER-R17-P2-02`、`GROK-R17-P2-01` |
| 抖動根因 | **CPU 競爭**（實測：併 8 個 `yes` 負載 → `cold=144.2ms` 失敗；靜止 `74.9ms` 通過） | `CODEX-R17-P1-03` |
| 與詞法層關係 | **無**——latency 測試走 Task 通道，**不經 lexer** | `CODEX-R17-P1-03`、`GROK` §D |

⇒ **使用者提問「是不是乾脆放寬」的答案：不用改，也不用花力氣。**
但理由不是「門檻太嚴」，而是**門檻有 SPEC 依據、抖動來自機器負載、且該測試與本次重寫無關**。

### 群集

| # | 群集 | 來源 ID | 級別 | 處置 |
|---|---|---|---|---|
| **F-1** | E-1 真正根因＝self-gate 以字面 `\n` 比對致早退；非「轉換＋grep」架構 | `COMPOSER-R17-P0-01`＋`GROK-R17-P0-02` | **BLOCKING** | **採納，推翻主委提案①**。修法對象改為 `_gate_cmd_is_self_gate` 述詞 |
| **F-2** | 提案②輸出欄位不足以導出契約 **3／5／7／10**（`-c`/`eval` 引數 span、路徑正規化、heredoc 七條規則、自呼叫述詞語意） | `CODEX-R17-P0-01`＋`COMPOSER-R17-P1-01`＋`COMPOSER-R17-P1-02`＋`COMPOSER-R17-P2-01`＋`GROK-R17-P0-01` | **BLOCKING** | **採納**。B3.5 第一步＝訂**完整輸出契約**（token 序列／正規化命令字／context／heredoc 有效性與 body span／遞迴深度／解析錯誤），逐條對照 11 契約後才寫碼 |

| **F-3** | 「O(1) emit」與現行 shell 介面及「emit span content」自相矛盾；E-2 之超線性為 awk `out=out c` 累加 | `CODEX-R17-P1-02`＋`GROK-R17-P1-01` | MAJOR | **採納**。scanner 改 reducer/stream-span，另定資源上限與 fail-closed；🔴 **禁回復 8192 截斷放行** |
| **F-4** | latency 維持現狀；min-of-N 為統計手法達標；100ms 有 SPEC 出處；抖動根因為 CPU 競爭 | `CODEX-R17-P1-03`＋`COMPOSER-R17-P2-02`＋`GROK-R17-P1-02`＋`GROK-R17-P2-01` | MAJOR | **採納**。**不動測試**；另立 lexer-size benchmark（不與 100ms canary 混用） |

🔴 **ID 歸戶：主委本輪錯位兩次，兩次都由外部抓到**

| 錯位 | 內容 | 誰抓到 |
|---|---|---|
| 第 8 次 | `GROK-R17-P0-01`（提案②契約覆蓋）與 `P0-02`（E-1 根因）對調 | 主委自檢 |
| 第 9 次 | `GROK-R17-P1-01`（E-2 超線性）與 `P1-02`（min-of-N）對調，且推翻表與 latency 段亦錯引 | **grok 戳記輪 REJECTED** |

`completeness_check` 只驗「ID 有沒有出現在綜合檔」，**對「歸到哪一群」完全無感**
⇒ 這類錯誤機檢抓不到，只有委員語意複核擋得住。
**已列為待開票**：收斂檔每個群集應強制附上所引 ID 的斷言摘句，並由腳本比對摘句是否
確實出自該 ID 的附錄本文——把語意錯位轉成可機械驗證的字串比對。

### 排期裁定

| 批 | 內容 |
|---|---|
| **B3.5**（新增，獨立批） | ①訂 lexer 輸出契約並逐條對照 11 契約 ②`/tmp` 原型 ③差分驗證（**基準見下**）④11×TP/TN＋26 parity＋11 mutation＋100K/500K 時限 ⑤通過才寫入 repo |

🔴 **差分驗證的基準（codex 戳記輪 `查3` 指出原設計不足，已補）**

原文只寫「新舊對同一語料判定一致」，**未定義可信的「舊」**。兩個候選都不合格：

| 候選 | 為何不能當基準 |
|---|---|
| 工作區未 commit 的 B3 修補 | 本身帶 E-1 fail-open 與 E-2 超線性，**不能當 oracle** |
| pre-Phase2 snapshot | 缺 Phase 2 的**正確新行為**，單獨不足以代表期望值 |

**採 codex 建議**：以**凍結 snapshot ＋ `phase2_expected_flips`** 合成
**不可變的 old/expected 判定矩陣**——snapshot 給「本來的判定」，flips 給「本批應該翻轉的條目」，
兩者相加即為期望值。**驗收＝非預期差集為零**。
另對 E-1／E-2 的新契約加**獨立 TP/TN、mutation、timeout／資源上限 gate**（不靠差分涵蓋）。
| **B4** | **B3.5 通過後**才開工。🔴 **禁在 B3 內再補一刀後併 B4**（三家一致） |

### 具名殘留（不阻塞 B3.5）

1. **C6** 多 heredoc 第二 body 誤擋——順延 B4。
2. **latency 抖動**——維持現狀，已知並行負載下會偶發紅；**偶發紅請重跑，勿據單次結果下結論**（主委已因此犯過一次破壞性錯誤）。
3. **工作區未 commit 的 B3 修補**——**保留**待 B3.5（全回退會重開三條原始 fail-open，
   部分回退無法安全裁定 C1 依賴）。
   🔴 **但主委原稱「非即時風險」的說法撤回**（codex 戳記輪 `查4` 不同意，判定成立）：
   `10K 字元→0.09s` **只覆蓋小輸入**，既不證明 E-1 fail-open 已無害，
   也不證明大輸入 O(n²) 的風險可接受。
   **正確表述＝兩害相權下暫留，風險未經證明**；B3.5 完成前不得 commit，
   且不得以此為由宣稱現況安全。

### 出場判準核算（本輪）

findings 去重後 **4** 群｜其中 BLOCKING **2**（F-1／F-2）
⇒ 本輪為**設計諮詢**非驗收，BLOCKING 表示「原提案不可直接派工」，已改為 B3.5 先行。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R17-P0-01
**斷言**：proposal ② 原輸出不能導出全部 11 契約。**碼證**：`pytest -q tests/governance/test_gate_lexical_contract.py tests/governance/test_debt_gate.py`→23 passed；`grep -c '^{'`→A/B=30/65；`bash scripts/gate_check.sh` newline/semicolon→0/2，顯示需完整 token/recursive facts。**來源摘要**：`docs/GOVB0_FRICTION_TODO.md#a1410ec31fcd`、`scripts/_gate_lex.sh#debe1484a7e5`、`tests/governance/fixtures/gate_decision_corpus.txt#1ffb72e0e666`。[BLOCKING|P0] 信心度 High；先補 output contract 與 differential/mutation oracle。
## CODEX-R17-P1-02
**斷言**：O(1) emit 宣稱與現行 shell 介面及 proposal 的「emit span content」互相衝突。**碼證**：`nl -ba scripts/_gate_lex.sh | sed -n '75,181p;362,424p'` 可見 `src=src line`、`out=out c`、`cmdsubs=$(...)`；quoted probe `timeout 40 /usr/bin/time -p bash scripts/gate_check.sh`→100K `real 1.32s`、500K `real 31.00s`、rc=0。**來源摘要**：`scripts/_gate_lex.sh#debe1484a7e5`、`scripts/gate_check.sh#b454a55ea513`。[MAJOR|P1] 信心度 High；scanner 應 reducer/stream-span，另定資源上限與 fail-closed，不回復 8192 截斷放行。
## CODEX-R17-P1-03
**斷言**：現 latency 測試不是 lexer gate，且在 CPU 競爭下可偶發假紅，不能作 B3 redesign oracle。**碼證**：`pytest -q -s ...test_gate_check_latency_under_100ms` baseline `cold=74.9ms` passed；同命令併 8 `yes` hog→`cold=144.2ms, second=155.9ms` failed；`git log -S'test_gate_check_latency_under_100ms'`→`141e4b8`。**來源摘要**：`tests/governance/test_debt_gate.py#f4d28ce5adbd`、`docs/P16_COMMITTEE_DEBT_SPEC.md#56915f8bdab3`。[MAJOR|P1] 信心度 High；保留 100ms canary，不改成 min/提高門檻，另立 lexer-size benchmark。
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

## GROK-R17-P0-01

**斷言**: 提案②列舉的輸出欄位無法導出契約 3／7／10（及路徑正規化 5 的完整判定），原案派工會在 `-c`／heredoc 上假綠或誤擋。

**碼證**: SPEC `docs/GOVB0_FRICTION_SPEC.md` Task 2.0 項 3、7、10（`:188-218`）要求 `-c`/`eval` 內層遞迴與 heredoc ⑥⑦；提案②只列 cmd_pos 首 token + cmdsub + fail-closed 旗標。反例：`bash -c codex` 與 `bash -c echo` 首 token 皆為 `bash`。RECHECK：對提案 schema 寫真值表，缺 InnerC 事件則無法區分。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#283298bb1e8a

[BLOCKING|P0] 信心度=High。修法：擴大 emit（InnerC/InnerEval/Heredoc 事件）或放棄「只偵測」改「直接 flags」，並逐契約填 逐項核對表 至全可。

---

## GROK-R17-P0-02

**斷言**: E-1 換行繞道的直接原因是 `_gate_cmd_is_self_gate` 用逐行 grep 把「首行 gate」誤判為整條自呼叫，與「先轉換再 grep」無因果。

**碼證**:  
```
. scripts/_gate_lex.sh
_gate_cmd_is_self_gate $'bash scripts/gate.sh\ncodex exec hi'  → YES
printf '%s' $'…\n…' | grep -Eq '[;&|`]|\$\(|\n'             → rc=1
gate_check 換行 → rc=0；分號 → rc=2
```
碼位：`scripts/_gate_lex.sh:351-359`。RECHECK：同上三命令。

**來源摘要**: scripts/_gate_lex.sh#debe1484a7e5

[BLOCKING|P0] 信心度=High。修法：self 豁免改全字串／cmd_pos 計數==1；不得只加字元長截斷。屬修不完整（舊版亦 rc=0），非本批新引入，但仍是 fail-open。

---

## GROK-R17-P1-01

**斷言**: E-2 為本批 preprocess 路徑上 awk 字串累加造成的超線性成本；500k quoted 實測 ~30s，屬新引入可用性洞。

**碼證**: quoted `echo "a"*n` 經 `gate_check`：1k→0.04s，10k→0.07s，50k→0.42s，100k→1.36s，500k→**29.81s**；unquoted 100k→0.14s。`_gate_lex_preprocess` `out=out c`（`:144-180`）。RECHECK：timeout 90 重跑 100k/500k。

**來源摘要**: scripts/_gate_lex.sh#debe1484a7e5

[MAJOR|P1] 信心度=High。修法：停止全量改寫字串（串流 flags）或改用可 O(n) 的緩衝策略；全面重寫排 B3.5，或具名殘留+監控。

---

## GROK-R17-P1-02

**斷言**: 將 latency 改為 min-of-N 會在真實冷路徑已退化到 >100ms 時仍高機率全綠，屬統計手法達標，違反測試品質。

**碼證**: (1) 集合反例 min(110,110,110,40)=40；(2) 模擬 min4 通過率 0.998 vs med3 0.879（退化 p50≈92）；(3) 現行 med+第4 次在空載 cold≈71 已穩。RECHECK：跑 `min_counterex.py` 邏輯或等價計算。

**來源摘要**: tests/governance/test_debt_gate.py#f4d28ce5adbd

[MAJOR|P1] 信心度=High。修法：**維持 (a)**；若動門檻必先修 P16 SPEC:507。

---

## GROK-R17-P2-01

**斷言**: latency 測試在並行負載下系統性超過 100ms，根因是 CPU 競爭而非 audit 行數或詞法；把單次紅歸因 audit 並封存會再次破壞 provenance。

**碼證**: 串行 3× cold_ms∈[70.7,71.1] PASSED；8 並行 cold_ms∈[147.9,177.4] 8/8 FAILED；empty vs full 僅 +20ms。事故對照 brief／HANDOFF：`c2a351f` 誤封存已撤。RECHECK：串行 vs 並行各跑 latency 單測。

**來源摘要**: docs/P16_COMMITTEE_DEBT_SPEC.md#56915f8bdab3

[MINOR|P2] 信心度=High。修法：文件註明 serial；委員會勿對單次紅做結構性「優化」；索引路徑等 audit 真逼近預算再做。

---

### 建議排期（再述）

```
B3（現況，含已知 E-1/E-2 殘留）──✗──► B4
         │
         └──► B3.5 詞法（獨立）──► B4（2.2/2.3/2.4）
Latency：不進 B3.5；維持現狀 (a)
```

---

ASSUMPTIONS_VERIFIED: F1–F12 皆附實跑；H1/H3/H5 已攻破或限縮；語料 A=30 B=65 實數非採信 brief  
TESTS_RUN:  
- E-1/self/dispatch 手工探針（見 F1–F2,F5）  
- E-2 曲線 1k–500k（F3–F4）  
- `pytest tests/governance/test_gate_lexical_contract.py -q` → 8 passed rc=0  
- `pytest …::test_gate_check_latency_under_100ms -s` ×3 → PASSED cold≈71ms  
- 同測 8 並行 → 8 FAILED cold≈148–177ms  
- 未跑全套 `pytest tests/governance`（763）；collect 非必須  
FAILURES_SEEN: 並行 latency 全紅（預期用）；無未解釋失敗  
SCOPE_CHANGES: none（禁改碼已遵守）  
NUMERIC_OR_SCHEMA_IMPACT: none  

STATUS: DONE

## 戳記

<!-- 委員 append RECONCILE-STAMP 行於此區段之後 -->
RECONCILE-STAMP: composer APPROVED 2026-08-06 sha256:d45ef4643041eba559499869c64a87ff0686db08130018e3a8effe24bf288866 task:GATELEX-STAMP
RECONCILE-STAMP: composer APPROVED 2026-08-06 sha256:862f7bee23daa514f6c01d8ce6990ca202afe737737df65f8ff12e1e418ad6e1 task:GATELEX-STAMP2
RECONCILE-STAMP: grok APPROVED 2026-08-06 sha256:862f7bee23daa514f6c01d8ce6990ca202afe737737df65f8ff12e1e418ad6e1 task:GATELEX-STAMP2
RECONCILE-STAMP: codex APPROVED 2026-08-06 sha256:862f7bee23daa514f6c01d8ce6990ca202afe737737df65f8ff12e1e418ad6e1 task:GATELEX-STAMP2
