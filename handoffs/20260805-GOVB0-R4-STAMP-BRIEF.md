# 第 0 批 SPEC R4 收斂戳記

brief-kind: stamp

stamp-target: handoffs/reconcile/20260805-govb0-spec-r4/synth.md

## 任務

複核 `handoffs/reconcile/20260805-govb0-spec-r4/synth.md` 的**群集／處置段**是否忠實反映你 R4 的 findings，
確認無誤後 **append 一行 RECONCILE-STAMP** 到該檔的 `## 戳記` 區段。

**本輪為 R4 收斂的第一次戳記輪。**（R1／R2／R3 三輪的戳記輪皆已完成並三家 APPROVED。）
來源：codex 3 條 ＋ composer 5 條 ＝ 8 條，群集為 `G-1`～`G-6`。

## 🔴 揭露：你們交件後主委改動過本檔（**這是本輪首要複核標的**）

R4 收斂檔在你們交件後被 commit 擋住，主委為解阻塞做了三類修改。**請先審這三類，再審歸戶。**

### 修改 1：移除六處**假豁免** token

原稿在 `G-1`～`G-6` 每列處置欄及 `VERIFY` 區各寫了 `VERIFY-EXEMPT:doc-summary:govb0-r5-confirm`。

**事實**：`scripts/verification_claim_check.py:97-99` 的 `EXEMPT_RE` 只認六個類別
（`typo`／`doc-example`／`migration-note`／`template-drift`／`tooling-blocked`／`spec-ambiguity`）。
`doc-summary` **不在其中** ⇒ 該 token 正規表達式不匹配、**自始零效力**，等同未標記。
⇒ 原稿等於在六個位置寫下**看似有豁免、實際沒有**的標記。已全數移除。

**請攻**：此描述是否屬實（可自行讀 `EXEMPT_RE` 驗），以及移除後的替代寫法是否仍有掩飾成分。

### 修改 2：`G-3`／`G-4` 改引**真 receipt**，其餘四條明寫「不自證」

`G-3`（§A 計數）與 `G-4`（委員 ID 對調）本可機械複驗，故實跑並產 receipt：

| receipt id | 命令 | stdout |
|---|---|---|
| `govb0-r4-g3-factcount` | `grep -c '^- FACT-RECEIPT:' docs/GOVB0_FRICTION_SPEC.md` | `10`（== §A 宣稱值） |
| `govb0-r4-g4-composer-ids` | `grep -n 'COMPOSER-R3-P1-0' docs/GOVB0_FRICTION_SPEC.md` | Task 2.1 處 `P1-02`、Task 3.3 處 `P1-01` |

`G-1`／`G-2`／`G-5`／`G-6` **無可機械複驗的 receipt**，改寫為
「**證據狀態：待 R5 逐條複核**，本檔不自證」，**不援引任何豁免類別**。

**請攻**：這四條標為「不自證」是否等於把驗證責任推給下一輪而實質無人驗；
若你認為其中某條**現在就該有 receipt**，請拒章並指名該條與應跑的命令。

### 修改 3：行號引用改為 Task 定位（**同一病型第 8 次**）

R4 初稿 `VERIFY` 區寫「`:237` 為 `P1-02`、`:398` 為 `P1-01`」，實跑為 `:239`／`:417`——
SPEC 在 R4 定稿後又被修訂，行號漂移。已改以 **Task 編號**定位並記為 `票 B-17`／`B-13` 同族第 8 次現形。

**請攻**：本檔是否還有其他**易腐引用**（行號、檔案大小、未鎖定的計數）未被改掉。

## 你要確認的（逐條，不是形式蓋章）

### 1. 你自己 R4 的每一條 finding 都被歸入某個 G 群，且處置與你的主張一致

findings 在附錄逐字保留（byte-faithful），群集表在前段（`G-1`～`G-6`）。

🔴 **請逐條核對 ID 對應，不要只看語意**。R1／R2／R3 三輪的戳記輪，
**每一輪都有家族在這一步抓到主委把 finding 歸錯 ID**（累計 7 次，R3 那次是三家各自獨立指出）。

⚠️ **兩道機檢都抓不到「錯位」**：`completeness_check.sh --lock` 與主委自檢問的都是
「每個 ID **是否出現**在群集段」——ID 掛在**錯的列**時兩者皆 rc=0。
只有你們的**語意複核**抓得到。此殘留已寫入 `票 B-36`／`B-13`。

**本輪主委改用機械作法填表**：填群集表前先以 `awk` 自附錄抽「ID → 斷言首句」對照表，照表填。
**請驗證此法是否真的消除了錯位**，而非只是換一種出錯方式。

### 2. `E-SCOPE`（不受理範圍）維持不變

四項：截斷 oracle（`票 B-35`）／`B-34` 語意閉合／`B-24` 機械強制面／`B-15` FP-2 定位。
**你們已於 R2 戳記輪表態接受**，R3／R4 兩輪亦標為 `OUT-OF-SCOPE`。
本輪**不再重新徵詢**；若你改變立場，請拒章並寫明失效路徑。

### 3. 對「是否還需要 R5 確認輪」表態

四輪 findings 趨勢：19（5 P0）→ 17（**7 P0**）→ 11（3 P0）→ **8（2 P0）**。
R4 的 8 條**已全部修畢**（見上表與群集段）。

主委擬定的 R5 出場判準：**findings ≤5 且新 P0 機制缺口 <2 ⇒ 進 TODO 生成**。

**請表態二選一並說明理由**：
- (a) R5 確認輪**有必要**——指出你預期 R5 還會冒出什麼類型的 P0；
- (b) R5 **可省**，直接進 TODO 生成——則須說明「修改 1／2 的四條待驗項」由誰在哪一關驗。

⚠️ 選 (b) 者請注意：本 SPEC 的**憲法要求完整管線不得跳步**，
所以 (b) 不是「跳過審查」而是「把確認併入 TODO 審查輪」，請明說併入哪一輪。

## 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-05 sha256:ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa task:<派工注入給你的 task-id>
```

- `<你的家族名>` 以派工注入的家族名為準。
- `sha256` **逐字照抄上方**（`bash scripts/reconcile_body_hash.sh <該檔>` 對「`## 戳記` 之前內容」算出）。
- `task:` **逐字使用派工注入給你的 task-id**，brief 內任何範例一律不得採用。
- **只 append 到 `## 戳記` 區段之後**，**不得改動該檔任何其他位元組**（附錄為 byte-faithful 委員原文）。

🔴 **grok 的立場**：`reconcile_stamps_check.sh` 要求 `review_families` 全員，但 grok 是 implementer、
被角色閘擋在 R4 review 之外（`票 B-34`）。⇒ **grok 請以「第三方複核歸戶正確性」立場審**：
不是確認「我的 findings 有沒有被歸戶」（你沒有 findings），而是確認
「**群集表對附錄逐字 findings 的歸戶是否正確、處置是否忠實、上述三類修改是否有掩飾成分**」。

## 硬性要求

1. **只准動 `handoffs/reconcile/20260805-govb0-spec-r4/synth.md` 的 `## 戳記` 區段**，其餘逐位元組不變。
2. **驗收＝狀態，不是 rc**：貼出下列三者的**完整 stdout 與 rc**：
   - `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r4/synth.md`
   - `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r4/sources.lock`（須維持 0）
   - `python3 scripts/verification_claim_check.py --files handoffs/reconcile/20260805-govb0-spec-r4/synth.md`（須維持 0）
3. **rc 一律直接取，禁經 pipe**（`cmd | tail; echo rc=$?` 讀到的是 `tail` 的 rc）。
4. 禁 `git checkout`／`git restore` 任何 tracked 檔；不要 commit、不要 push。
5. 若你決定**不蓋章**，一樣要交產出說明理由，**不要留空檔**。

## 產出

改了哪一行（貼 diff）、三支檢查器的完整 stdout 與 rc、逐條確認 findings 歸戶的結果、
對**三類修改**的攻擊、對 `E-SCOPE` 的立場、以及對「是否還需要 R5」的 (a)/(b) 表態。
收尾清 /tmp workdir（保留 claude-501）。
