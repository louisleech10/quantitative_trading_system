# GATELEX-REDESIGN2 — grok 委員會諮詢（詞法層重審 ＋ latency）

**家族**: GROK  
**task-id**: GATELEX-REDESIGN2  
**brief**: `handoffs/20260805-GATE-LEX-REDESIGN-BRIEF.md`  
**brief-kind**: consult  
**日期**: 2026-08-05  
**禁改碼**: 本輪只交分析與設計建議；未改 tracked 檔、未 commit、未 push。

FINDINGS_COUNT: 5

---

## Verdict

**需修補後派工（詞法）／維持現狀（latency）。不可把 E-1／E-2 當 B3 內再補一刀後併 B4。**

| 主題 | 結論（一句） |
|---|---|
| 問1 共同根因 | **否**（同架構主題、不同 code path；修一不自動修另一） |
| 問2 §B 提案 | 方向對，**輸出 schema 不足**導出 11 契約；不可原案派工 |
| 問3 替代 | 擴充 emit schema 的單趟判定器 ＋ differential 對語料 B；或**局部修 E-1 + 具名殘留 E-2** |
| 問4 改多少 | **局部止血可選；全面重寫須獨立批次**；「維持現狀＋具名殘留」合法 |
| 問5 排期 | **獨立批 B3.5（先於 B4）**；不塞 B3 尾、不與 B4 混 |
| 問D1 抖動 | **機器負載競爭為主**；audit 規模次要（+~20ms）；非詞法層 |
| 問D2 選項 | **(a) 維持現狀**（推薦）；可選 (d) 隔離 CI 負載；拒 (b)(c) 除非修 SPEC |
| 問D3 min-of-N | **會變成統計達標**；構造反例成立，推翻主委辯護 |
| 問D4 值不值得 | **不值得為抖動大改**；測試有 SPEC 依據，偶發紅代價＝重跑／誤診，非刪測理由 |
| 問D5 100ms | **有出處**：`docs/P16_COMMITTEE_DEBT_SPEC.md:507`；調高＝改契約，不是「放寬模糊門檻」 |

**建議下一步（排期）**

1. **立刻**：B3 凍結進 B4；E-1／E-2 **具名殘留**寫進 epic 殘留表（面向未來：修補只考慮新行為）。
2. **B3.5（獨立，先於 B4）**二選一（委員會收斂後擇一，本意見偏好 2a 若資源緊、2b 若要一次關洞）：
   - **2a 局部**：只修 `_gate_cmd_is_self_gate` 為全字串錨定／命令位置總數==1（關 E-1）；E-2 具名殘留 + 測「含引號長輸入」timeout 保護（不重寫 lexer）。
   - **2b 重寫**：單趟狀態機**直接出判定 flags**（非先轉字串再 grep），emit schema **補齊** `-c`/`eval` 內層、heredoc ⑥⑦、路徑 token；differential 對語料 B（65）＋不變語料 A（30）；**禁改語料 A 任一行**。
3. **Latency**：本輪 **(a) 維持現狀**；不排進 B3.5。若後續詞法重寫，D 量測須重做（Task 路徑本就不經 lexer，見下）。
4. **B4** 只在 B3.5 關 E-1（至少）且語料 B 全綠後再開。

**D 與詞法交互**：latency 測試用 `tool_name=Task`（`test_debt_gate.py:434-435`），**不進入** `_gate_cmd_is_dispatch`。詞法重寫**不會**改變該測試的成本曲線；E-2 量測與 latency 門檻**互相獨立**。本報告 latency 建議**不依賴**詞法現狀。

---

## §0 前提宣告

### fact-verified（本輪獨立實跑）

| ID | 事實 | 命令／觀測摘要 |
|---|---|---|
| F1 | E-1 換行 fail-open | `bash scripts/gate.sh\ncodex exec hi` → **rc=0**；分號同型 → **rc=2** |
| F2 | E-1 機制＝self_gate 短路 | `_gate_cmd_is_self_gate` 對換行輸入 **YES**；`grep -Eq '...\n...'` **rc=1**（逐行看不到換行）；首行 `^…gate.sh$` **rc=0** |
| F3 | E-2 超線性（quoted） | n=1k/10k/50k/100k/500k → real **0.04 / 0.07 / 0.42 / 1.36 / 29.81** s；500k/100k ≈ **21.9×**（5× 長度） |
| F4 | 無引號長輸入走快路徑 | unquoted 100k → real **0.14** s（vs quoted 1.36 s） |
| F5 | 正當自呼叫未誤擋 | `gate.sh dispatch --task-id X`／`gate_check.sh`／`register-output` → **rc=0** |
| F6 | 語料條數 | A：`grep -c '^{' …/gate_invariance_corpus.txt` → **30**；B：decision → **65** |
| F7 | 詞法契約測全綠 | `pytest tests/governance/test_gate_lexical_contract.py -q` → **8 passed** rc=0 |
| F8 | latency 空載全綠 | 連續 3 次 `-s`：cold_ms **70.7 / 71.1 / 70.8**；second≈71；lines=34796 |
| F9 | latency 8 路並行全紅 | 8/8 FAILED；cold_ms **147.9–177.4**（同機、同 audit） |
| F10 | empty vs full audit（harness） | gate_check Task：empty **0.04s** ×5；full **0.06s** ×5；debt core alone：0.02 vs **0.04** |
| F11 | 100ms 出處 | `docs/P16_COMMITTEE_DEBT_SPEC.md:507` 明文「單次 gate_check < 100ms」+ O(N) 掃 audit 須改尾端/索引 |
| F12 | 三條 fail-open 未回退 | 語料契約測仍綠；本輪未重跑全 763（見 TESTS_RUN） |

### assumed（brief 或主委，本輪攻）

| ID | 假設 | 本輪判定 |
|---|---|---|
| H1 | E-1 與 E-2 **有共同根因** | **架構類比成立、因果同一不成立**（見 問1） |
| H2 | 實際指令 <10K ⇒ 非即時風險 | **日常合理**；未能量測歷史分布（`cmd_head` 截斷）；惡意/偶發 quoted 大輸入可 30s hang |
| H3 | 提案②輸出可涵蓋 11 契約 | **不成立**（見 逐項核對表） |
| H4 | awk 可 O(1) 記憶體串流 | **未在 macOS awk 證成**；且 `scan=$(preprocess)` 必物化全字串 |
| H5 | 「真變慢時 min 一樣超標」 | **可構造反例推翻**（見 問D3） |

### 被當成事實的未驗證假設（§0 挑戰）

- brief §B「兩個缺陷都源於『先轉換、再 grep』」——E-1 的 self_gate **在 preprocess 之前**對 **raw** 做 grep，**根本不經轉換**。把 E-1 歸因於「轉換架構」是**錯誤歸因**（至少 MAJOR 前提錯誤）。
- 「長度上限可完全移除」依賴提案②真 O(n) 且不再建輸出字串——在 schema 補齊前不可當承諾。

---

## 逐項核對表

契約來源：`docs/GOVB0_FRICTION_SPEC.md` Task 2.0（11 項：`1`／`1b`／`2`–`10`）。  
提案②聲稱輸出：命令位置起點+首 token；`$()`／反引號 span；未閉合／heredoc fail-closed 訊號；命令位置總數。

| 契約 | 僅用提案②輸出能否判定 | 缺口 |
|---|---|---|
| **1** 引號內 `;|&` 非分隔 | **可**（quote 內不產生命令位置） | — |
| **1b** 跨行剝引號狀態 | **可**（SM 跨行） | 實作細節，非 schema 洞 |
| **2** 命令位置完整定義 | **可**（若 SM 枚舉 `^ ; & \| ( \` $( && \|\| eval後 xargs後`） | 須寫死與 SPEC 同集合 |
| **3** `-c`／`eval` 引數遞迴 | **不可** | 輸出**無**「shell -c 的下一引數／eval 字串」；僅首 token=`bash` 無法區分 `bash -c codex` vs `bash -c echo` |
| **4** 帶引號路徑當一 token | **部分** | 首 token 可含空白路徑；但若 executor 不在 argv0（罕見）會漏 |
| **5** 路徑正規化 | **不足** | 需對 token 做 `./`／`//`／`..` 正規化步驟；輸出未含「正規化後 basename」 |
| **6** 未閉合引號 fail-closed | **可** | — |
| **7** unquoted `-c`（`bash -c codex`） | **不可** | 同契約 3：須看 argv 後續，非僅命令位置首 token |
| **8** 遞迴深度 ≤3 | **外置可** | 由呼叫端 depth 計數，非 lexer 輸出本身 |
| **9** 跳脫不終止 span | **可**（SM 規則） | 邊界不明 → fail-closed 須寫進 SM |
| **10** heredoc 七條（⑥允許清單＋⑦＋多 heredoc＋body 不掃） | **不可僅靠「heredoc 訊號」** | 須完整 delim 解析／body 跳過／body 外續掃／多 heredoc 序；fail-closed 訊號≠正確 span |

**claude -p／--print**（現行第二段，Task 2.2 將收窄）：亦**非**「首 token ∈ executor 名單」可覆蓋。

**自我豁免（E-1）**：`count==1 ∧ token∈gate腳本` **可**關換行繞道——**前提**是命令位置計數對換行正確（換行＝新位置）。此條**不在 11 契約編號內**，但是 D-1 實作約束。

**結論**：11 項中 **至少 3、5、7、10 無法**由主委列舉的輸出直接導出 → 提案②**不可原樣派工**。

### 提案① 評估（共同根因）

| 缺陷 | 主委歸因 | 本輪碼證 | 採納？ |
|---|---|---|---|
| E-2 | awk `tok=tok cc` O(n²) | `_gate_lex_preprocess` `:77-80` `src=src line`、`:144-180` `out=out c`；曲線 1.36s→29.81s | **機制採納** |
| E-1 | 「判定散落 grep、grep 逐行」 | 部分對：真正短路在 `_gate_cmd_is_self_gate:351-359`，且 **在 preprocess 前** | **一半**：grep 逐行是真因；「先轉換」**不是** E-1 因 |

### 提案② 評估（不轉換、只偵測）

- **方向**：單趟 SM 出結構化事實、判定改查詢 → **正確**，可同時關 E-2（不建改寫字串）與把 self 豁免納入同一計數模型。
- **攻擊點**：
  1. schema 不足（上表）。
  2. 「O(1) 記憶體」與 bash `$(…)` 捕獲、heredoc 需行緩衝 **衝突**；應承諾 **O(n) 時間、有界額外狀態**，勿承諾 O(1) RAM。
  3. 若仍 `scan=$(awk…)` 再 grep，只是換皮的轉換架構。
  4. 熱路徑禁 python（TODO Task 2.1）→ 必須 awk/shell；可行但實作密度高。
- **可行條件**：擴大 emit（至少：cmd_pos tokens 序列或 argv0+flags；`-c`/`eval` 字串事件；heredoc open/close 事件；parse_status）；**判定函式讀事件流直接回 BLOCK/ALLOW**，不經第二輪字串 grep。

### 提案③ 風險補充

| # | 風險 | 嚴重度 |
|---|---|---|
| R1 | schema 漏 `-c`/`eval` → 契約 3/7 假綠 | P0 |
| R2 | heredoc ⑥⑦ 簡化 → 合法 delimiter 誤擋或攻擊鏈 fail-open（SPEC 已有事故敘事） | P0 |
| R3 | 重寫觸發膨脹（factories 級共用路徑＝gate 熱路徑） | P1 排程 |
| R4 | 語料 A 被「順便改」→ 不變性崩 | P0 流程 |
| R5 | macOS awk 字串/遞迴深度限制 | P2 |
| R6 | 與 B4（同改判定段）並發必衝突 | P1 排程 |

### 替代設計（問3）

**Alt-L（局部，推薦資源緊時）**

1. `_gate_cmd_is_self_gate`：禁止依賴 grep 逐行；改為「整串無未引號分隔／換行／cmdsub」**或** SM 計數 cmd_pos==1 且唯一位置為 gate 腳本。
2. E-2：不重寫；加 **timeout 防衛**（PreToolUse 側或 preprocess 前字元上限改為「僅 quoted/heredoc 路徑的 soft budget + fail-closed」需另 SPEC——若與 D-2 摩擦衝突則只具名殘留）。
3. 語料：加 TP `gate.sh\ncodex` → BLOCK；**不改**語料 A。

**Alt-F（完整，B3.5 大）**

1. 單檔狀態機：事件流 → `is_dispatch` boolean + `fail_closed` reason。
2. 事件至少含：CmdPos(token)、InnerC(string)、InnerEval(string)、CmdSub(string)、HeredocSkip、Unclosed、ParseFail。
3. 驗收：語料 B 65 條方向不變或差集具名；mutation 11 仍在；500k quoted **<1s**（或具名新門檻附 profile）。

---

## 出場判準核算

| 判準 | 現況 | 過關條件 |
|---|---|---|
| E-1 關閉 | **未**（rc=0 已證） | 換行複合 gate+executor → rc=2；正當單命令 gate 仍 rc=0 |
| E-2 關閉 | **未**（29s@500k） | quoted 成長近線性；或具名殘留+上限策略經委員會核可 |
| 11 契約可導出 | 提案② **否** | 逐項核對表全「可」或具名削減經 SPEC 修訂 |
| 語料 A | 30 條 | **零修改**（`grep -c '^{'` 仍 30 且內容 hash 不變） |
| 語料 B | 65 條 | 全綠；差集具名 |
| 三 fail-open 不回退 | 本輪詞法測綠 | 回歸集保持 |
| B4 開工 | **不可** | B3.5 至少關 E-1 或正式具名殘留+使用者／委員會接受風險 |
| Latency 大改 | **不建議** | 僅當 SPEC 修訂 100ms 或索引落地時 |

### 問D1–D5（latency）

**D1 抖動根因（實測區分）**

| 假說 | 證據 | 判定 |
|---|---|---|
| 機器負載競爭 | 串行 cold≈71ms 全綠；8 並行 cold 148–177ms **8/8 紅** | **主因** |
| 冷啟 I/O | second_ms≈ cold_ms（71 vs 71）；warm 與 sequential 同量級 | 非主因 |
| audit.log 規模 | empty 0.04s vs full 0.06s（+20ms）；debt core 0.02 vs 0.04 | **次要**；現 34k 行未逼近 100ms 預算 bulk |
| 詞法層 | Task 路徑不跑 lexer | **無關** |

**D2 選項**

| 選項 | 評價 |
|---|---|
| **(a) 維持現狀** | **推薦**。中位數×3 + 第 4 次 <100ms 已抗單次尖峰；空載穩定 71ms |
| (b) 改 min-of-N | **拒**（見 D3） |
| (c) 調高門檻 | 須先改 P16 SPEC:507；屬契約變更，不是「放寬模糊數」 |
| (d) 不與他測競爭 | 可選低成本：pytest 標記 serial／文件註明勿與重測並行；不改門檻 |
| (e) 索引/掃尾 | SPEC 已預留「超過即須索引」；屬 **audit 成長** 路徑，非現在 71ms 的優先 |

**D3 min-of-N 反例（推翻「真變慢 min 一樣超標」）**

1. **集合反例**：真實成本常態 110ms，偶發一次 40ms 快路徑 → `min(110,110,110,40)=40 <100` **綠**；`median(110,110,110)=110` **紅**。主委辯護不成立。
2. **分佈模擬**（`min_counterex.py`，seed=42）：退化後 p50≈92ms 且 10% 尖峰～180ms 時，`min-of-4` 通過率 **0.998**，`median-of-3` **0.879**——min 幾乎永不報警。
3. 並行實測下樣本全在 140–180，min 仍 >100 故仍紅；但辯護的一般性已被 (1)(2) 推翻。

**D4 值不值得**

- `git log -S'test_gate_check_latency_under_100ms'`：引入於 `141e4b8`（P1-6 B5）；其後與 latency 相關的破壞性動作是誤診 archive（`c2a351f`）與撤回（`fd6dc77`）——**不是測試抓住真實 lexer 退化**，而是人為誤判 audit 規模。
- 本輪：空載 3/3 綠；負載 8/8 紅 ⇒ 抓到的是 **CI/本機並行噪聲**，不是「gate 邏輯變慢」。
- 偶發紅損失：重跑成本低；誤診損失高（已發生封存 audit 破壞 provenance）。  
⇒ **不值得為消抖花架構力氣**；值得的是避免再對單次紅做破壞性「優化」。

**D5 100ms 出處**

- **有依據**：`docs/P16_COMMITTEE_DEBT_SPEC.md:507`（Task 3.1 驗證）；`docs/P16_COMMITTEE_DEBT_TODO.md:453` 效能驗收複述。
- 理由原文：audit append-only 只會長，熱路徑 O(N) 重掃；超過 → 掃尾或索引。
- 因此 (c) 調高門檻 **＝修改已凍結契約**，不是「放寬無出處的經驗值」。若要動，走凍結修訂程序，不在本 consult 偷改測試。

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
