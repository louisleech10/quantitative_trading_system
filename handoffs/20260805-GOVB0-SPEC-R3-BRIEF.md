# 第 0 批 SPEC R3 閉合複核

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（**本輪 ROUND=R3**）。

## 🔴 本輪的不受理範圍（逐字宣告，請先讀）

依使用者定死「**沒 100% 解就做 95% 那版現在收，殘留具名記錄不當阻塞**」與
「**brief 須宣告不受理範圍否則審查沒終點**」，本批**明確不受理**下列四項。
**三家已於 R2 戳記輪表態接受**（codex 逐項確認「不使本批交付物本身失效」；composer／grok 未反對），
並已隨 R2 收斂檔 `RECONCILE-STAMP` 全數 APPROVED（body sha `8b8d0a94…`）。

| 不受理項 | 殘留票 |
|---|---|
| **產出截斷偵測 oracle**（expected manifest／record count／byte digest） | `票 B-35 GOV-OUTPUT-TRUNCATION-ORACLE` |
| **`B-34` 語意閉合**（stamp roster vs 角色閘） | `票 B-34`（本批僅用權宜第三方戳記並明文標註） |
| **`B-24` 機械強制面** | R1 `D-6` 已裁 SPLIT；TODO §0 須標「`B-24` 部分完成」 |
| **`B-15` FP-2 定位** | 已定補查條件（Phase 0 後 ≥200 筆 `gate_deny` 或 ≥30 日） |

**處置規則**：再提上述任一議題，請標 `OUT-OF-SCOPE` 並附「不做會怎樣」的具體失效場景，**不作為 BLOCKING**。
**唯一例外**：能證明不做會使**本批交付物本身失效**（而非只是不夠完美）者，仍可 BLOCKING，但須寫明失效路徑。

**為何要劃這條線**：R1 = 19 findings（5 P0）→ R2 = 17 findings（**7 P0**），**P0 未下降**。
R1 的 findings 已由 composer 逐條重跑確認全數 CLOSED，R2 的 17 條全是對**新文本**的新發現
⇒ 命中 `docs/SCAR_LEDGER.md` 記載的 P16 scope-accretion 失敗模式（八輪卡在 20-25 findings）。

## ⚠️ 前置說明（勿誤 block）

- 🔴 **本輪 `brief-kind=review`，不需要戳記。產出中請勿出現 `## RECONCILE-STAMP` 這個標題**（`票 B-32`，修法在 Phase 1，尚未實作）。
- **禁改碼**。探針一律隔離副本；禁變異 repo 內 `scripts/*.sh`／`tests/**`；禁 `git checkout`／`git restore`。
- **rc 一律直接取，禁經 pipe**。
- ⚠️ `.claude/gate/ts_stamp.log` 為 `Non-ISO extended-ASCII`＋NEL；預設 locale 下 `grep` 靜默返空。需分析時用 `LC_ALL=C grep -a`，**但勿 `export`**（會洩漏進其他檢查流程，主委因此弄紅過 6 個測試）。

## 審查標的

- **`docs/GOVB0_FRICTION_SPEC.md`（R3 版）** —— 本輪唯一標的。`template_check.sh spec` rc=0。
- R2 收斂裁決：`handoffs/reconcile/20260805-govb0-spec-r2/synth.md`（17 findings，E-1～E-13，三家 APPROVED）
- 你自己的 R2 產出：`handoffs/20260805-govb0-spec-r2-<你的家族>.md`
- 主委探針（可自行重跑）：`handoffs/govb0_probes/b15probe{,2,3,4,5,6}.sh`、`runlog_dur.sh`

## R3 相對 R2 的變更清單（逐條對應 E 群集）

| E 群 | 你們的 finding | R3 怎麼改 |
|---|---|---|
| E-1 | `CODEX-R2-P0-05` | §V 的 Task 數改為 **11** 並逐一列出，加「須與 `grep -c '^\*\*Task '` 相等」的機械核對要求 |
| E-2 | `CODEX-R2-P1-09`／`COMPOSER-R2-P2-01` | §V 改為「**rc 只能作輔助護欄**，每條 `ASSERT … rc` 都必須有同 Task 內對應的狀態斷言」；Task 1.1 unknown 補**四項無副作用狀態斷言**（無 token／audit 零新增／未開債／無產出檔） |
| E-3／E-4／E-13 | `COMPOSER-R2-P0-01`／`CODEX-R2-P0-04`／`COMPOSER-R2-P1-02`／`COMPOSER-R2-P1-01` | Task 2.0 契約由 5 項擴為 **10 項**（新增：命令位置完整定義／`eval` 遞迴／unquoted `-c`／遞迴深度上限／跳脫引號／heredoc）；**逐項標示原型③已涵蓋／未涵蓋**，明文「禁止照抄原型即宣稱完成」；驗收改為 ≥20 條語料、10 個 mutation |
| — | 主委 R3 自行實測新增 | Task 2.0 新增 **1b 項：剝引號必須「跨行有狀態」**，明文禁用 `sed` 行內替換、且**禁用「正規化為單行」**（會使真多行指令第 2 行漏網）。出生事故＋四象限實測見下 Q3 |
| E-5 | `CODEX-R2-P0-01` | **劃入不受理**，Task 3.2 改法⑤明文標註本 marker **不保證內容完整**，並指向 `票 B-35` |
| E-6 | `CODEX-R2-P0-02` | 並發改為**序列化拒絕**（第二個 attempt 直接拒絕啟動並記 audit），演進紀錄三版皆寫入 |
| E-7／E-8 | `CODEX-R2-P0-03`／`CODEX-R2-P1-10` | **兩個 baseline 分離**：語料 A（Phase 0，判定應不變）／語料 B（Phase 2，判定應改變），各自獨立 snapshot 與檔案，測試須斷言兩者 sha256 不同；Task 0.1 新增改法⑤明列 `audit_events.json` 須新增哪些 key 與驗收方式 |
| E-9 | `CODEX-R2-P1-08` | Task 3.2 新增**順序契約**：format check 與 publish 均在 CLI wait 返回之後；**timeout 只涵蓋 CLI process-group 區間，不涵蓋 publish**；`result_state` 每 attempt 恰一筆 |
| E-10 | `CODEX-R2-P1-07`／`COMPOSER-R2-P1-04` | 定稿門檻**改採 codex 較嚴者**（每家族 ≥50 筆 ＋ ≥3 個不同 session／UTC 日期）；未達門檻的處置由主委明示取捨（見下 Q4） |
| E-11／E-12 | `CODEX-R2-P0-06`／`COMPOSER-R2-P1-03`／`COMPOSER-R2-P2-02` | 均劃入不受理並具名留票；TODO §0 強制標「`B-24` 部分完成」 |

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: R3 為 4 Phase／11 Task，`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` rc=0，
且 `grep -c '^\*\*Task ' docs/GOVB0_FRICTION_SPEC.md` == 11 == §V 宣稱值
→ 主委實跑 2026-08-05。

fact-verified: 原型③（`handoffs/govb0_probes/b15probe5.sh`）對 26 條語料 **26/26 全對**；
`b15probe4.sh` 證實 `eval`／`$()`／反引號／子 shell 在**現行 gate 即已 fail-open**
→ 主委實跑；**codex 於 R2 戳記輪獨立重跑確認**（`E3_VERIFY`，probe4／probe5 rc=0）。

fact-verified: `b15probe6.sh` 四象限實測——`sed` 行內剝引號**仍會誤擋**引號內多行字串，
`awk` 跨行狀態機版 4/4 全對（含真多行指令仍 BLOCK）
→ 主委實跑 2026-08-05。

assumed: E-1～E-13 **全部已在 R3 落實，且未引入新矛盾**。← 請直接攻。

assumed: Task 2.0 的 **10 項契約 ＋ 1b 跨行剝引號**已涵蓋所有會影響判定的詞法情境。← 請攻，補出遺漏項。
🔴 但**若你補出的新情境屬於「理論上可能、repo 內無實例、且需新增機制才能處理」**，
請標 `P2` 並註明「不阻擋本批」——這是為了中止 R1→R2 的 accretion。

assumed: 序列化拒絕（E-6）不會造成新的可用性問題（例如正常重派被誤拒）。← 請攻。

## 必答（逐條 verdict；須附實跑 receipt 或明確碼證）

### Q1 — **你自己 R2 的每一條 finding，逐條判定是否真關閉**
依章程 §B8：**由原提出方重跑同一反例確認**。
逐條輸出：finding ID ／ CLOSED 或 NOT-CLOSED ／ 重跑的反例與結果。
NOT-CLOSED 者須指出 R3 的哪一句仍不足。

### Q2 — R3 是否引入**新的**矛盾
特別檢查：①Task 2.0 的 10 項契約與 Task 2.1–2.4 的驗收是否一致 ②兩個 baseline 分離後，
Phase 0 的「判定不變」與 Phase 2 的「判定應變」是否真的不互斥 ③序列化拒絕與 Task 3.3 逾時重派的互動。

### Q3 — 跨行剝引號的設計是否正確（主委 R3 自行新增，未經你們審過）
主委實測：`git commit -m "…多行訊息，某行以 codex 開頭…"` 被現行 gate 誤擋（本 session 第 7 次）。
首擬修法「正規化為單行」**已被主委自己的實測推翻**——真正的多行指令第 2 行開頭可能是真派工。
現行設計＝**剝引號必須跨行有狀態**（逐字元），禁 `sed` 行內替換、禁正規化為單行。
請裁定：①此設計是否正確 ②在 `gate_check.sh` 的熱路徑（每次工具呼叫都跑）用 `awk` 是否可接受，
或有更便宜的純 shell 作法 ③是否有本設計仍漏的多行情境（heredoc、續行 `\`、`$'...'` 等）。

### Q4 — E-10 未達門檻時的處置取捨（主委裁決，與 codex 原主張不同）
`CODEX-R2-P1-07` 要求「未達門檻**不得用暫定值**」；主委改為「timeout **機制照常上線並以暫定值運作**，
但 Task 3.3 **不得宣稱完工**、值標 `PROVISIONAL`、`票 B-14` 保持未定稿」。
理由：**無 timeout 正是 `B-14` 事故成因**（空等 2h20m），「有暫定 timeout」嚴格優於「無 timeout」。
請裁定此取捨是否接受；不接受請給可執行的替代方案。

### Q5 — `票 B-36`（收斂工具的群集表盲點）的嚴重度與歸屬
本輪實證：主委群集表漏掉 `COMPOSER-R2-P1-01`，而 `completeness_check --lock` 仍 **rc=0**
（因附錄逐字保留使任一 ID 必然存在）⇒ **「有沒有進群集表」沒有任何機器檢查**，
由你們在戳記輪各自獨立指出才被發現。
請裁定：①嚴重度 ②是否應**併入 `票 B-13`**（搬遷／收斂填表漏填不會被擋）或獨立 ③修法應在檢查端還是產出端
（主委傾向產出端：`reconcile_build.sh` 生成骨架時預列全部 ID，只准填處置不准刪列）。

### Q6 — §V 的驗收是否真的可證偽
逐 Task 檢查：是否仍有「有 `rc` 斷言但**無**對應狀態斷言」者？是否有 mutation 寫成恆真？

### Q7 — 可以進 TODO 生成嗎？
若仍為「需修補」，請**明列 BLOCKING 清單**（編號 ＋ 具體修法方向），並**逐條標明是否落在不受理範圍內**。

## 產出

canonical 四欄 findings（ROUND=**R3**）+ **Verdict**。**禁改碼**。
**勿寫 `## RECONCILE-STAMP` 標題**。收尾清 /tmp workdir（保留 claude-501）。
