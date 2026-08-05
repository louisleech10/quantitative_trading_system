# 第 0 批 SPEC R5 — 確認輪

brief-kind: review

target: docs/GOVB0_FRICTION_SPEC.md（R5 版）

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — **請完整讀取並照做**，
包含 canonical finding heading 格式、§0 挑戰前提、Verdict 段。
本 brief 只**加碼收斂本輪範圍**，不取代該範本的任何格式要求；兩者衝突時以範本的**格式**為準、以本 brief 的**範圍**為準。

## §0 前提宣告（主委攤開，**錯前提請直接當 finding 打回**）

**已查證**（每條附查證方式，可自行復跑）：

- fact-verified: R4 收斂檔已三家 APPROVED 且本體雜湊相符 → `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r4/synth.md` rc=0，sha `ae304eeb…f88b3fa`
- fact-verified: R4 的 8 條 findings 全數歸戶、無漏 → `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r4/sources.lock` rc=0（codex 3/3、composer 5/5）
- fact-verified: SPEC Task 數 11 == §V 宣稱值 → `grep -c '^\*\*Task ' docs/GOVB0_FRICTION_SPEC.md` → `11`
- fact-verified: SPEC FACT-RECEIPT 數 10 == §A 宣稱值 → receipt `govb0-r4-g3-factcount`
- fact-verified: §N 已含 `票 B-36` ID 錯位殘留段 → receipt `govb0-r4-g5-b36-residual`
- fact-verified: Task 3.3 驗證段已含 `PROVISIONAL` 狀態斷言 → receipt `govb0-r4-g6-provisional`
- fact-verified: 委員債務無 OPEN → `bash scripts/debt_ledger.sh --has-open` rc=0

**假設**（未查證，**請優先攻這幾條**）：

- assumed: **G-1 的 heredoc 五條規則只有文字，尚無原型實作驗證過其可執行性**。
  探針 `handoffs/govb0_probes/b15probe5.sh` 的 26 組語料**不含 heredoc 向量** ⇒
  「五條規則足以機械執行」目前**純屬紙上推導**。這是本輪最脆弱的前提。
- assumed: **G-2 的八條狀態斷言覆蓋全部失效路徑**。此為主委讀 R4 兩家 finding 後自行歸納，
  未經第三方窮舉；可能存在未被列舉的併發窗口。
- assumed: heredoc 在本專案實際派工路徑中的出現頻率**足以支撐 P0 定位**。
  若你認為實際極罕見，可主張把 G-1 降級——但須附出現頻率的查證。
- assumed: 主委「R4 八條已全部修畢」的宣稱中，G-1／G-2 兩條**無機械 receipt**，僅有 SPEC 文字。

## 本輪定位：**確認輪，不是第五次全面審查**

R4 的 **8 條 findings 已全部修畢**。本輪只做一件事：
**逐條確認每條是否真的關閉、且關閉方式可機械驗收**。

🔴 **不重開已裁決事項**。R1～R4 四輪已定案的設計選擇（見下 §不受理範圍），
除非你能指出**具體失效路徑**（不是「可以更好」），否則不受理。

**四輪 findings 趨勢**：19（5 P0）→ 17（**7 P0**）→ 11（3 P0）→ **8（2 P0）**。
R4 收斂檔已三家 `RECONCILE-STAMP APPROVED`（sha `ae304eeb…f88b3fa`），
本輪 (a)/(b) 表態時三家一致選 **(a) 開 R5**，故有此輪。

## 出場判準（**本輪唯一終止條件，逐字**）

> **findings ≤5 且新 P0 機制缺口 <2 ⇒ 進 TODO 生成。**

- 「新 P0 機制缺口」＝ SPEC 缺少某個**必要機制**、致實作者無法機械驗收；
  **不含**措辭改善、補充範例、命名一致性等。
- 若你判定本輪應**不再開 R6**，請明說；若判定要開，**必須指名是哪一條機制缺口**。

## 逐條確認清單（**這就是本輪的全部工作**）

### 🔴 A. 兩個 P0 群集 — 需要你實質對抗確認

| 群 | R4 findings | 宣稱修法 | 你要確認的 |
|---|---|---|---|
| **G-1** | `CODEX-R4-P0-01`／`COMPOSER-R4-P1-03` | 契約第 10 項補 **heredoc 五條機械規則**：起點＝`<<[-]?\s*(['"]?)IDENT\1` 後的下一個換行／delimiter 去引號／終點＝行首恰為 delimiter（`<<-` 允許 tab 縮排）／多 heredoc **依序消耗**／未閉合 ⇒ fail-closed。並列 **5 組驗收語料** | 這五條是否**足以機械執行**（實作者照著寫得出來、且 TP/TN 可判定）？是否存在 heredoc 向量**繞過**這五條而使真派工漏掃？ |
| **G-2** | `CODEX-R4-P0-02`／`COMPOSER-R4-P2-02` | **owner-safe release**（釋放前比對 attempt id，不符不得釋放）／wrapper 被 SIGKILL 依 stale 回收／外層 timeout **不直接刪 lock**／跨裝置 rename 失敗仍走 `_emit_family_result` 並 owner-safe 釋放／「存活中」判準改為 **lock 檔 ∪ attempt 進程**。驗收由 3 條擴為 **8 條逐路徑狀態斷言** | 八條斷言是否**覆蓋全部失效路徑**？是否仍存在「舊 attempt 解掉新 attempt 的鎖」或「併發重派」的殘存窗口？ |

🔴 **請對 G-1／G-2 各給出至少一個具體反例向量**（可證偽），或明確聲明「找不到反例」。
**只寫「看起來沒問題」不算完成本輪任務。**

### B. 四條已有機械 receipt — 只需確認 receipt 與 SPEC 現況一致

主委實跑產出，receipt 已進版控（`handoffs/run_receipts/`）：

| 群 | finding | receipt id | 實跑結果 |
|---|---|---|---|
| G-3 | `CODEX-R4-P2-01` | `govb0-r4-g3-factcount` | `grep -c '^- FACT-RECEIPT:'` → `10`，== §A 宣稱值 |
| G-4 | `COMPOSER-R4-P1-01` | `govb0-r4-g4-composer-ids` | Task 2.1 處為 `P1-02`、Task 3.3 處為 `P1-01` |
| G-5 | `COMPOSER-R4-P1-02` | `govb0-r4-g5-b36-residual` | `grep -n 'B-36'` → `:492`／`:495`／`:497` 有「ID 錯位無機械防線」殘留段 |
| G-6 | `COMPOSER-R4-P2-01` | `govb0-r4-g6-provisional` | `grep -n 'PROVISIONAL'` → `:421` 改法、`:436` 驗證段狀態斷言 |

**G-5／G-6 的 receipt 是依你們在 R4 戳記輪的指正補做的**——當時 composer 與 grok 各自獨立指出
「這兩條現在就能出便宜 receipt，標『不自證』是程序偏懶」。已採納。

⚠️ **請驗證 receipt 是否名實相符**（行號會隨修訂漂移，請以內容而非行號判斷）；
若你認為某條 receipt **證明力不足以支撐「已修」**，請指名並說明還需要什麼。

## 🔴 不受理範圍（`E-SCOPE`，四輪已定，本輪不得重開）

四項：截斷 oracle（`票 B-35`）／`B-34` 語意閉合／`B-24` 機械強制面／`B-15` FP-2 定位。
三家已於 R2 戳記輪表態接受，R3／R4／R4-STAMP 三輪皆維持 `OUT-OF-SCOPE`。

**另外，下列一律不受理**（依「95% 解法就收」原則，使用者已核可）：
1. **防蓄意繞過**類 findings——本批目標是**擋意外**，蓄意繞過另立票；
2. **措辭／可讀性／命名一致性**改善；
3. **既有票已涵蓋**的問題（請改為指名該票，不列為本 SPEC 的 finding）；
4. **要求新增機制**以覆蓋 `E-SCOPE` 四項的任何提案。

命中上述任一項請標 `OUT-OF-SCOPE` 並**不計入 findings 數**。

## 已知具名殘留（**不是 finding，不必再提**）

- **「ID 錯位」無任何機械防線**：`completeness_check --lock` 與主委自檢都只驗「ID 是否出現」，
  掛錯列時兩者皆 rc=0。已裁定併入 `票 B-13`，修法在產出端，且產出端只能擋「漏」不能擋「錯位」。
- **timeout 定稿門檻未達**：每家族需 **≥50 筆** ＋ **≥3 個不同 session／UTC 日期**；
  未達則標 `PROVISIONAL` 且 Task 3.3 不得宣稱完工（此即 G-6 的驗收斷言）。

## 🔴 補派輪追加：codex 已提出兩個**實跑的**反例，請正面裁決

本輪 codex 已交件，判 `G-1`／`G-2` **NOT-CLOSED**，並附**實際執行過**的反例。
**這兩條是本補派輪的首要任務**——請逐條表態 **同意（NOT-CLOSED）／反駁（CLOSED）**，並附你自己的實跑證據。

### codex 反例 1（`CODEX-R5-P0-01`，針對 G-1）

**斷言**：契約第 10 項的起點 regex 為 `<<[-]?[[:space:]]*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\1`，
只接受**識別字**作 delimiter。但 **`EOF-1` 是 shell 合法 delimiter**（非蓄意破壞語法）。

**攻擊鏈**：delimiter 用 `EOF-1` ⇒ regex 不匹配 ⇒ **不開 span**；
接著掃描器在 body 內遇到 `<<INNER`（`INNER` 是識別字）⇒ **在錯誤位置開了 span**；
該 span 一路吞到行首為 `INNER` 的那行 ⇒ **把 `EOF-1` 終止行與其後的真實外部派工整段吃掉**。

**codex 實跑結果**：`bash -c` 執行 `HEREDOC_SHELL_RC=0`、輸出含 `ATTACK_EXECUTED`；
同語料餵給依契約寫的最小掃描器 → `CONTRACT_SHAPE_SCAN=ALLOW`。**即 fail-open。**

⚠️ **你在前一版已考慮過非識別字 delimiter（`<<1`），判定「不開 span ⇒ body 仍受命令位置掃描 ⇒ 最多誤擋」。**
codex 的反例與此**不同**：關鍵在 **body 內含第二個合法 marker**，會把 span 開在錯的位置。
**請針對這個巢狀情況重新判定**，不要只重述前一版結論。

### codex 反例 2（`CODEX-R5-P0-02`，針對 G-2）

**斷言**：SPEC 定義了 owner-safe release 與存活判準，但**未要求取得 lock 必須是原子 exclusive claim**。
碼證：`rg -n 'O_EXCL|flock|TOCTOU|exclusive|原子.*鎖|原子.*lock' docs/GOVB0_FRICTION_SPEC.md` → **rc=1**（無匹配）。

**攻擊鏈**：兩個 dispatcher 皆在 precheck 時看到「無存活 lock」⇒ 皆通過 ⇒ 皆啟動 CLI。
owner-safe release 只防「舊 owner 釋放新 lock」，**無法阻止兩個 owner 同時通過空檢查**。

**codex 實跑結果**：barrier 模擬中 A/B 都先看到 absent，stdout 出現
`A:START`、`B:START`、`TOCTOU_SIM_BOTH_PRECHECKS_PASSED=yes`。

⚠️ **你在前一版判定此為「實作細節／低機率競態，標準 lockfile 實作可互斥」。**
請重新考量：本專案的鐵律是「**工具必須自帶強制機制，不准靠紀律和記憶**」，
SPEC 若不明文要求原子取得，就是把正確性寄託在實作者剛好選對做法。
**若你仍主張 CLOSED，請說明 SPEC 現行哪一條文字強制了原子性。**

### 本輪 brief 的一處自我更正

前一版 §0 寫「委員債務無 OPEN → rc=0」。你上一版指出實測 **rc=1**，**觀察正確但推論不成立**：
`committee_run.sh` **派工這個動作本身就會開債**，所以任何 brief 只要宣告「無 OPEN 債」，
在委員審查當下必定為 rc=1。這是流程固有競態，非事實錯誤。**此條不必再列為 finding。**

## 硬性要求

1. **禁改碼、禁改 SPEC**。你只交報告，主委負責修。
2. **rc 一律直接取，禁經 pipe**（`cmd | tail; echo rc=$?` 讀到的是 `tail` 的 rc）。
3. 禁 `git checkout`／`git restore` 任何 tracked 檔；不要 commit、不要 push。
4. findings 一律用 `## <家族大寫>-R5-P<嚴重度>-<序號>` 作為 heading（機器要吃），
   內含 **斷言／碼證／來源摘要** 三段，並標 `[BLOCKING]`／`[MAJOR]`／`[MINOR]`。

   🔴 **`##` 這一層只准用於 canonical finding ID heading**（`Verdict`／`§0` 等範本既有段除外）。
   **逐條確認結果（G-1～G-6）請一律用 `###` 或表格**，**不得**寫成 `## G-1（…）— CLOSED`。
   原因（2026-08-05 本輪實測）：`completeness_check.sh` 會把每個 `##` heading 當成 finding ID 解析，
   `G-1（...）— **CLOSED**` 不符 schema ⇒ **整份判 format-failed**、該輪帳無法銷、後續派工全被擋（`票 B-31`）。
   ⚠️ 本規則是修補**本 brief 前一版的缺陷**：前一版同時要求「canonical `##` finding ID」與
   「G-1～G-6 各一段」，兩者衝突，composer 因此整份格式失敗需重派。
5. 每條 finding 須附**可執行的修法**，不得只說「應該要更嚴謹」。

## 產出

逐條確認結果（G-1～G-6 各一段，明確標 **CLOSED／NOT-CLOSED**）、
G-1／G-2 的反例向量或「找不到反例」聲明、對四條 receipt 的證明力判定、
以及對「是否需要 R6」的表態（含出場判準的逐項核算）。
收尾清 /tmp workdir（保留 claude-501）。
