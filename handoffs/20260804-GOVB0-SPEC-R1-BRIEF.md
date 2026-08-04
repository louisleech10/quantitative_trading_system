# 第 0 批 SPEC 對抗審查 R1

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）

- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。
- 🔴 **本輪 `brief-kind=review`，不需要戳記。產出中請勿出現 `## RECONCILE-STAMP` 這個標題。**
  原因（已定位，見 `票 B-32`）：`cx_run.sh:512` 對每次派工都注入一句提及 RECONCILE-STAMP 的指示，
  但 `completeness_check.sh:179` 會把 `## RECONCILE-STAMP` 判為非法 finding ID ⇒ 交件必失敗。
  合法戳記本來就是**單獨一行** `RECONCILE-STAMP: <family> APPROVED <date> sha256:<hash> task:<id>`，**不是標題**。
  2026-08-04 composer 連兩次因此 `format-failed`。**本輪請直接略過戳記。**
- **禁改碼**。探針一律隔離副本（`cp` 到 `/private/tmp/<你的 workdir>/`），
  **禁變異 repo 內 `scripts/*.sh`／`tests/**`**，禁 `git checkout`／`git restore` 任何 tracked 檔。
- **rc 一律直接取，禁經 pipe**。
- ⚠️ `.claude/gate/ts_stamp.log` 為 `Non-ISO extended-ASCII`＋NEL 行結束符，
  **預設 locale 下 `grep` 會靜默返回空**（連 `-c` 都無輸出）。若要分析該檔一律 `LC_ALL=C grep -a`，
  **但不要 `export`**（會洩漏進其他檢查流程；主委 2026-08-04 因此弄紅 6 個測試）。

## 審查標的

- **`docs/GOVB0_FRICTION_SPEC.md`**（主標的，本輪唯一要審的 SPEC；`template_check.sh spec` rc=0）
- 佐證輸入：`handoffs/reconcile/govb0-recon-r1/synth.md`（R1 偵察收斂，21 findings，`completeness_check --lock` rc=0）
- 票源：`handoffs/20260801-GOV-AMEND-BACKLOG.md` 的 `## B-24`／`## B-15`／`## B-14`／`## B-30`／`## B-32`

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: 本 SPEC 涵蓋 5 張票、5 個 Phase、11 個 Task，`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` rc=0
→ 主委實跑 2026-08-04。

fact-verified: R1 偵察 21 條 findings 全數收斂、零掉項
→ `bash scripts/completeness_check.sh --lock handoffs/reconcile/govb0-recon-r1/sources.lock` rc=0（主委實跑 2026-08-04）。

fact-verified: `gate_check.sh:86` 現行正則對 7 條真派工全數 BLOCK；帶路徑前綴的家族 CLI（`/opt/homebrew/bin/codex exec`）
與直接 `bash scripts/cx_run.sh` 皆 ALLOW（既有 fail-open）
→ `.claude/tmp/b15probe.sh`、`.claude/tmp/b15probe2.sh` 實跑；`grep -c 'token' scripts/cx_run.sh` → 0。

assumed: 五張票合成**一個** SPEC、一次管線是對的。← 請攻。
若你認為某 Phase 必須拆成獨立票／獨立管線（例如 Phase 4 的 `B-24` checker 規模已達獨立中任務），**明講並給判準**。

assumed: Phase 2 的四個 Task（引號感知／`claude` 段收窄／basename 化／呼叫點）**疊加後不會互相抵銷或產生新的漏網**。
← 請攻。**這是本 SPEC 最高風險處**：四個修改同時作用在一條正則上，任一組合可能開新洞。
請具體構造「四項單獨都正確、疊加後漏網」的反例，或證明不存在。

assumed: Task 3.2 的 `.part` → rename 同時解 `B-30`（覆蓋自產）與 `B-14`（terminal marker）是正確的合併。← 請攻。
特別是：**委員是被告知寫到 `<out>` 的**，改成 `.part` 需要改 prompt 或由 `cx_run.sh` 轉手，兩種作法各有什麼失敗模式？

assumed: Phase 0（純觀測）真的能做到「行為逐位元組不變」。← 請攻。
`grep -Eo` 取命中片段是否可能改變既有判定的 rc 或副作用？

## 必答（逐條 verdict；每條須附實跑 receipt 或明確碼證）

### Q1 — `OPEN-1` timeout 量測基準與值（**本輪必須裁定，主委不自裁**）

R1 兩家給出差一個數量級的建議：
codex 20 分鐘（基準＝output 寫入 → runlog 關閉，n=127，codex p50=68s）；
grok 60 分鐘（基準＝runlog birth → 最後寫入，n=440，ALL p50=5.3m／p90=20.7m／p99=48.5m／max=146.7m）。
請裁定：
1. per-family timeout 要涵蓋的**精確區間**（從哪個事件到哪個事件），並說明為何該區間才是 `cx_run.sh` 能控制的。
2. **排除已知掛死樣本後**重算 p95／p99（掛死樣本至少含 composer 146.7m；請自行判定還有哪些該排除並說明判準）。
3. 給出建議值 ＋ **誤殺率估計**（在該值下，歷史樣本中有多少筆正常完成會被殺）。
4. 是否需要 per-family 不同值（codex 明顯較慢）。

### Q2 — `OPEN-2` locale 相依守衛：是否開票、是否納入本批

實測（主委 2026-08-04）：`export LC_ALL=C` 後
`gate.sh` 對 `## Verdict：`（全形冒號後空白）**發出 token**（應拒發）；
`doc_format_precheck.sh` 對 `**Verdict: （待填…）**` **rc=0 放行**（應 rc=2）；
`template_check.sh spec` 對合格 SPEC 誤判缺 §A 錨點（fail-closed 誤報）。
請裁定：①嚴重度（是否 BLOCKING）②是否開新票、票號與範圍建議 ③**是否納入本批**——
主委預設**不納入**（避免 scope 膨脹），請攻此判斷。

### Q3 — `OPEN-3` FP-2 至今無法重現

`for f in codex composer grok; do … done` 形態的誤擋，三家＋主委皆無法重現。
請裁定：①本批以「Phase 0 上線後補查」結案 ②或判定為記載錯誤、從 `票 B-15` 除役 ③或你能重現（請附指令）。

### Q4 — `B-24`（Phase 4）的規模與可行性

`CODEX-R1-P0-03` 指出 docs root 有 629 個候選行、無標註語料、無法估誤報率。
本 SPEC 的 Task 4.1 限縮為「只對新寫與本批修改的文件生效」＋grandfather 清單須具名且有到期日。
請裁定：這個限縮是否足以使 Task 4.1 可交付？grandfather 到期日該由誰、依什麼判準設定？

### Q5 — §V 的驗收是否真的可證偽

逐 Task 檢查「驗證」欄：是否存在**改壞了也不會紅**的斷言？是否有 mutation 寫成恆真？
Task 2.5 的差集報表以「兩欄的每一項都須在 SPEC 中被預期」為驗收——這個判準可執行嗎，還是實務上會被放寬？

### Q6 — 依賴與順序

Phase 0 → Phase 2 是唯一宣告的依賴。是否存在**未宣告的 forward dependency**？
Phase 3 的 Task 3.2（`.part`）是否會影響 Phase 0 記錄的內容或 Phase 2 的判定？
Phase 4 對 Phase 0–3 的驗收欄回頭抽驗，這是否構成循環依賴？

### Q7 — 可以進 TODO 生成嗎，還是有 BLOCKING 必須先修？

## 產出

canonical 四欄 findings + **Verdict**。**禁改碼**（只產 review 檔）。
**勿寫 `## RECONCILE-STAMP` 標題**（見前置說明）。收尾清 /tmp workdir（保留 claude-501）。
