
# 票 B-39 SPEC 草案 R1 審查（雙家族）

brief-kind: review

**受審**：`docs/GOVB39_IDLIKE_HEADING_SPEC.md`（DRAFT R1，主委起草）
**票**：`票 B-39 GOV-IDLIKE-HEADING-FALSE-POSITIVE`
**上游**：`handoffs/reconcile/20260806-govamend-x-consult-r1/synth.md` 群集 `G-2`

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。
finding heading 逐字格式 `^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$`，本輪用 `R23`。
零 findings 請明寫 `FINDINGS_COUNT: 0`。

## 標題規則

`##` 標題限：`Verdict`／`§0 前提宣告`／`逐項核對表`／`出場判準核算`／canonical finding ID。
**`###` 可用**，但請避免讓子標題長得像 canonical ID（大寫＋連字號＋數字，
例 `### OUT-OF-SCOPE`、`### G-1`）——**這正是本票要修的誤判**，在修好之前請自行避開。
不受理項目請寫在 `## 逐項核對表` 內。

## §0 前提宣告

**已查證**（主委實跑）：

- fact-verified: `scripts/completeness_check.sh:60` `HEADING_LINE_RE='^[[:space:]]*#{2,6}[[:space:]]...'`；
  同檔 `_check_body_hashes` 的 `H2_LINE_RE` 為 `##(?!#)` ⇒ **同檔兩處對「標題」定義不一致**。
- fact-verified: SPEC 三支檢查器皆 rc=0（`doc_format_precheck`／`template_check spec`／`verification_claim_check`）。
- fact-verified: 本日 3 輪因此作廢，皆可由 audit／runlog 定位。

**假設**（請攻）：

- assumed: `GROK-R21-P0-01` 的三探針結論（id-like 才擋、中文子標題通過）**主委未自行復現**，
  直接採信寫入 SPEC §A。
- assumed: SPEC §V 的六項驗收**足以涵蓋**修法的所有風險面。主委未逐項推敲有無遺漏。

---

## 攻擊標的

### 一、修法會不會過寬（**最高優先**）

SPEC §0.B-1 訂「放寬不得漏收畸形 canonical-like heading」，
§V-4 用 `## CODEX-R99-P9-01`（`P9` 非法）當防退化樁。

**請構造更刁鑽的畸形**試圖穿過 allowlist，例如：
大小寫混合、家族名不在 SoT、`R` 後接非數字、多餘尾綴、全形字元、前後空白。
**穿得過即 BLOCKING。**

### 二、§V 六項是否足夠

**請攻**：有沒有**應該驗而沒驗**的？特別是——

1. `####`／`#####` 更深層級的行為未定義
2. 結構標題 allowlist 本身**寫死 vs 可設定**，SPEC 未表態
3. `--single`（交件當下）與 `--lock`（收斂時）**兩條路徑是否都涵蓋**

### 三、與 `B-38` 的相互影響

SPEC Task 1.1 的「覆蓋風險」欄宣稱：`B-38` 若採 `FINDINGS_COUNT: 0` 明示欄修法，
會動到同一函式的相鄰分支，故**兩者須可各自獨立測試**。

**請判定**：這個宣稱成立嗎？兩票的修法**有沒有真的會互相踩到的地方**？
若有，SPEC 該怎麼寫才能避免第二張票落地時把第一張的保護弄壞？

### 四、淨摩擦試算是否誠實

SPEC §C 的 C-5 附了淨摩擦試算（新增每次成本＝一次字串判定；
已避免次數＝3 輪作廢）。

**請驗**：這個試算有沒有**低估成本或高估收益**？
特別是「一次字串判定」是否真的無新增 I/O、是否會影響 latency canary。

## 🔴 不受理範圍（寫在 `## 逐項核對表` 內）

1. `B-38`（零 findings 判 vacuous）——同族不同根因，另票。
2. 群集 ID 登記（`B-26` 缺口）——另票。
3. 委員範本措辭。
4. 既有收斂檔——forward-only，一律不改。
5. 全票重裁的裁定結果——另輪已收斂。

## 出場判準

> **findings ≤5 且 BLOCKING = 0 ⇒ SPEC 可定版，進實作派工。**

## 硬性要求

1. **禁改碼、禁改測試、禁改 SPEC**。只交報告。
2. **rc 一律直接取，禁經 pipe**。
3. 🔴 **禁 `git checkout`／`git restore`／`git clean` 任何 tracked 檔**；誤動請回報。
4. 不要 commit、不要 push；**禁碰 `data_cache/`**。
5. ⚠️ 工作區有未 commit 的 B3 修補（含已知卡死路徑）；測大輸入請自行加 `timeout`。

## 產出

四個攻擊標的的逐項判定（含構造的畸形樣本與實跑 rc）、
`## 出場判準核算`、對 §0 兩條假設的攻擊結果。
收尾清 /tmp workdir（保留 claude-501）。
