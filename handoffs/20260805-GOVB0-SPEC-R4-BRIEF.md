# 第 0 批 SPEC R4 閉合複核

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（**本輪 ROUND=R4**）。

## 🔴 本輪定位：預期為最後一輪 SPEC 審查

**你們三家在 R3 戳記輪一致認定 accretion 已中止**：
- codex：「現證據不足以推翻 accretion 已中止」
- composer：「**不必開 R5**；R4 預期剩餘為 `F-2`／`F-3` 定稿實作＋交叉引用紀律。
  **若 R4 >5 條且含 ≥2 新 P0 機制缺口，再評估 R5**」
- grok：「同意同量級新機制 P0 的 accretion 已中止；**不同意『R4 零風險、不必再盯交叉引用』**」

⇒ **本輪採用 composer 的出場判準**：R4 findings **≤5 條**或**新 P0 機制缺口 <2 個** ⇒ 進 TODO 生成；
否則再評估 R5。**請在 Verdict 中明確給出「是否符合出場判準」的判定。**

## 🔴 不受理範圍（逐字宣告，三家已於 R2／R3 表態接受）

截斷 oracle（`票 B-35`）／`B-34` 語意閉合／`B-24` 機械強制面／`B-15` FP-2 定位。
再提請標 `OUT-OF-SCOPE` ＋ 失效場景，**不作為 BLOCKING**；
唯一例外＝能證明不做會使**本批交付物本身失效**（須寫明失效路徑）。

## ⚠️ 前置說明（勿誤 block）

- 🔴 **本輪不需要戳記，產出中請勿出現 `## RECONCILE-STAMP` 標題**（`票 B-32`，修法在 Phase 1，尚未實作）。
- **禁改碼**；探針用隔離副本；禁 `git checkout`／`git restore`。**rc 直接取，禁經 pipe**。
- `ts_stamp.log` 為 Non-ISO＋NEL，需分析時用 `LC_ALL=C grep -a`，**勿 `export`**。

## 審查標的

- **`docs/GOVB0_FRICTION_SPEC.md`（R4 版）** —— 唯一標的。`template_check.sh spec` rc=0。
- R3 收斂裁決：`handoffs/reconcile/20260805-govb0-spec-r3/synth.md`（11 findings，`F-1`～`F-7`，**三家 APPROVED**，body sha `2949edaa…`）
- 你自己的 R3 產出：`handoffs/20260805-govb0-spec-r3-<你的家族>.md`
- 主委探針：`handoffs/govb0_probes/`（`b15probe{,2,3,4,5,6}.sh`、`runlog_dur.sh`、`awk_hotpath_bench.sh`）

## R4 相對 R3 的變更（逐條對應 F 群集）

| F 群 | 你們的 finding | R4 怎麼改 |
|---|---|---|
| F-1 | `CODEX-R3-P0-01`／`COMPOSER-R3-P0-01` | Task 0.1 驗收**刪除「兩份 JSON diff 為空」**，改為對 **decision trace**（只含 `(rc,kind)`，與 audit 事件為**兩份不同產物**）逐項相等；audit 面另立一條斷言（欄位集合 == `audit_events.json` 所定） |
| F-2 | `CODEX-R3-P0-02` | 契約 7–10 項的**判定結果定死**：unquoted `-c`→BLOCK／遞迴**上限 3 層**逾限 fail-closed／跳脫字元**不終止 span**、邊界不明時 fail-closed／heredoc 本體**視為引號 span**。Task 2.1 限制放寬為「純 shell／`sed`／`awk`」＋**附效能 receipt**（見下 fact-verified） |
| F-3 | `CODEX-R3-P0-03`／`COMPOSER-R3-P1-03` | Task 3.2 新增完整 **lock 生命週期**：ownership（attempt id＋pid＋UTC 戳）／release 在 `_emit_family_result` 後**必定執行**（不依賴 publish 成功）／stale＝pid 已死**或**逾 (家族 timeout＋外層閥)／`failed` 後同 `<out>` 重派**放行**／被拒 attempt **不寫 `result_state`**。並補三條防誤拒／防鎖死狀態斷言 |
| F-4 | `CODEX-R3-P1-04`／`COMPOSER-R3-P1-01` | Task 3.3 定稿門檻由 ≥20 **更正為 ≥50 筆 ＋ ≥3 個不同 session／UTC 日期**；未達門檻**只有一種處置**（機制上線、值標 `PROVISIONAL`、Task 3.3 不得宣稱完工、`B-14` 未定稿），**消除 R3 未定義的 10–19 灰區** |
| F-5 | `COMPOSER-R3-P2-01` | 契約計數 10 → **11**（`1`／`1b`／`2`–`10`），驗收語料 ≥20 → **≥22**，mutation 10 → **11**；並加「本行數字須與條目數相等，code review 機械核對」 |
| F-6 | `COMPOSER-R3-P1-02` | Task 2.1 補**四條 1b 具名語料**（來源 `b15probe6.sh`）：引號內多行訊息（第 2 行以家族名開頭）×2 → **ALLOW**；真多行指令（第 2 行為真派工）×2 → **BLOCK**；並加 mutation「換成 `sed` 行內替換 → 前兩條轉 BLOCK」 |
| F-7 | `CODEX-R3-P1-05`／`COMPOSER-R3-P2-02` | `票 B-36` 已記「併入 `B-13`、修法在產出端」，並**補具名殘留**：產出端修法只能擋「漏」、擋不了「錯位」 |

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: R4 為 4 Phase／11 Task，`template_check.sh spec` rc=0；且三處計數自檢一致——
`grep -c '^\*\*Task '` == 11 == §V 宣稱；契約條目 11 == 驗收宣稱 11
→ 主委實跑 2026-08-05。

fact-verified: `awk` 在 PreToolUse 熱路徑的成本＝**每次工具呼叫 +5 ms**
（`bash handoffs/govb0_probes/awk_hotpath_bench.sh`，N=200；對照：正常工具呼叫約 80 ms、
權限分類器 2300–3000 ms）→ 主委實跑 2026-08-05，回應 `CODEX-R3-P0-02` 要求的 latency receipt。

fact-verified: R3 收斂檔已獲三家 `RECONCILE-STAMP APPROVED`，body sha `2949edaa…`，
`completeness_check --lock` rc=0 → 主委實跑 2026-08-05。

assumed: `F-1`～`F-7` **全部已在 R4 落實，且未引入新矛盾**。← 請直接攻。

assumed: `F-2` 定死的四項判定結果（含遞迴上限 3 層）**在實作上可執行且無歧義**。← 請攻。
特別是 heredoc「視為引號 span」——heredoc 的 delimiter 可自訂（`<<EOF`／`<<'X'`／`<<-EOF`），
掃描器如何機械界定其起訖？若你認為此項仍不可實作，請給可執行的替代定義。

assumed: `F-3` 的 lock 生命週期**涵蓋所有失效路徑**（正常／格式失敗／SIGKILL／外層 timeout／跨裝置 rename 失敗）。← 請攻。

assumed: 本 SPEC 已可生成 TODO。← 請攻；若否，**明列 BLOCKING 並逐條標是否落在不受理範圍內**。

## 必答（逐條 verdict；須附實跑 receipt 或明確碼證）

### Q1 — **你自己 R3 的每一條 finding，逐條判定是否真關閉**
依章程 §B8 由原提出方重跑同一反例確認。逐條輸出：ID ／ CLOSED 或 NOT-CLOSED ／ 反例與結果。

### Q2 — 是否符合出場判準
本輪 findings 是否 ≤5 條？其中**新 P0 機制缺口**（非主委同步／計數／措辭類）是否 <2 個？
**請明確回答「符合／不符合」**，這決定要不要開 R5。

### Q3 — `F-2` 的 heredoc 與遞迴上限是否真的可實作
請給出你認為可機械執行的 heredoc span 界定規則（含 `<<EOF`／`<<'X'`／`<<-EOF`／多個 heredoc 併存），
或說明為何應降級為 P2 不阻擋本批。

### Q4 — `F-3` lock 生命週期的失效路徑覆蓋
逐一檢查：正常結束／格式失敗／SIGKILL／外層 timeout／跨裝置 rename 失敗／lock 檔本身被外部刪除。
是否有路徑會**永久鎖死** `<out>` 或**誤拒**合法重派？

### Q5 — 交叉引用紀律（grok 於 R3 戳記輪明示「不同意 R4 零風險、不必再盯」）
請**機械核對**本 SPEC 內所有「N 項／N 個」數字與其可導出來源是否一致，列出任何不符者。

### Q6 — §V 是否仍有「有 rc 斷言但無對應狀態斷言」者

### Q7 — 可以進 TODO 生成嗎？

## 產出

canonical 四欄 findings（ROUND=**R4**）+ **Verdict**（須含 Q2 的出場判準判定）。
**禁改碼**。**勿寫 `## RECONCILE-STAMP` 標題**。收尾清 /tmp workdir（保留 claude-501）。
