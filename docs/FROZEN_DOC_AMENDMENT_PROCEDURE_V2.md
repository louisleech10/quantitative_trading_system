# 凍結文件修訂程序 v2.0

**狀態：草案，尚未生效。** `docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md`（v1.0）**在本檔取得三家戳記前仍全文有效**。

| 項 | 值 |
|---|---|
| 設計依據 | `handoffs/20260803-FROZEN-PROC-V2-DESIGN.md`（rev6） |
| 對抗審 | R1–R5，findings **26 → 28 → 25 → 16 → 6**；收斂檔 `handoffs/reconcile/20260803-frozen-proc-v2-r{1..5}/synth.md` |
| 生效條件 | 依 v1.0 §5：三家完整對抗審（已完成）＋ 使用者裁定 ＋ 三家 `RECONCILE-STAMP` |
| 本版模式 | **`whole-body`**——本程序檔自身**不**做分節簽名（雞生蛋；見 §7 階段 0） |

> **為什麼有 v2.0**：v1.0 只提供兩條修訂路徑——寫延伸檔（便宜，但讀者從此要讀 N+1 個檔），
> 或整份重開（貴，且**先前所有延伸檔一次作廢**）。痛在兩端：碎片化，與懸崖式的成本落差。
> v2.0 讓已遷移的文件**就地修訂、只重簽動到的節**，成本連續正比於改動範圍。
>
> **為什麼設計了五輪**：R2 確診初版是「**加機制型**」修訂——為補洞新增三個元件，被三家全數打穿。
> 改採**刪機制**方針後才收斂。**累計刪除 5 個元件、新增 0 個。**
> 這條經驗本身寫進 §0.2，因為它比條文更容易重犯。

---

## §0 範圍與方法（**先讀這節，它決定哪些 finding 不受理**）

### 0.1 只擋意外，不防蓄意

| | 在範圍內 | 不在範圍內 |
|---|---|---|
| 要擋的 | 漏記、抄錯、忘了同步、改了沒人知道、半套自動化 | 有人蓄意偽造 git 物件、繞過檢查器、竄改歷史 |
| 依據 | 這些**在本 repo 實際發生過** | 這些**一次都沒發生過** |

⇒ 凡屬「蓄意繞過」類，一律列入 §9 記錄，不在本程序內解決。

### 0.2 修訂本程序的方法論（**v2.0 新增，出自 R2 的病理診斷**）

> **凡新增元件，必須具名說明「為何無法以刪除達成」。**

v1.0 的前身六版為追求「防蓄意」膨脹到 6 輪、30+ 次派工，其中 50% 是純程序開銷；
v2.0 的 rev2 又重蹈一次（新增 baseline registry／`expires` 三段式／raw-byte escaping，全被打穿）。
**病根都是「修一個洞 → 加一個機制 → 新機制自己是新的攻擊面」。**

---

## §1 兩種文件狀態

每份受本程序約束的文件，**恰屬其一**（檔級、互斥）：

| 狀態 | 標記 | 修訂方式 |
|---|---|---|
| **`whole-body`**（含未標記的 legacy） | 檔頭 `STAMP-MODE: whole-body`，或登記於 grandfather registry | 沿用 v1.0 的 **D 延伸／R 重開**二分（§2） |
| **`section-map`** | 檔頭 `STAMP-MODE: section-map` | **就地修訂 ＋ 只重簽 `R-SCOPE`**（§3），**不再產生延伸檔** |

🔴 **禁止「算得出任一 hash 就算過」**：不得因解析失敗就靜默 fallback 到另一模式。
`STAMP-MODE` 位於檔頭且納入簽名範圍 ⇒ **模式翻轉本身是 fail-closed 的**。

---

## §2 `whole-body` 模式的修訂（沿用 v1.0，兩處修正）

### 2.1 D 延伸 / R 重開

| 類別 | 定義 | 做法 |
|---|---|---|
| **D 延伸** | 不推翻既有設計的修訂——含錯字、交叉引用、補充 | 寫延伸檔並取得三家戳記。**對原檔的唯一允許改動＝§2.3 的索引行** |
| **R 重開** | 既有設計被證偽 | 原檔重跑完整對抗審，原戳記作廢，**該原檔的所有延伸檔一併失效** |

**判定**：主委在 brief 明示類別與理由；任一委員可推翻；**爭議一律預設 R**。
**沒有第三類，沒有免審類別。**

> **v2.0 明確保留兩條 v1.0 安全閥**（設計階段曾提案收窄，三家否決）：
> ① R 仍**全量作廢**延伸檔，不做「只作廢重疊者」 ② 爭議仍**預設 R**，不開「爭議→使用者裁定」的降級口。

### 2.2 延伸檔必填

路徑：`docs/<原檔 basename>.D-<NNN>.md`，`<NNN>` 從 `001` 起，**不重用**。

```
# <原檔名> 延伸 D-<NNN>

BASE: <原檔路徑> @ <commit-sha>
PREDECESSOR: <前一份生效中的延伸檔路徑，或 none>
改什麼: <一句話>
為什麼: <一句話，或指向 reconcile 路徑>

## 觸及面宣告
新增: <原檔中實際存在的 heading 逐字，或 none>
覆寫: <同上，或 none>
依賴: <同上，或 none>

## 內容
<實際的修訂內容>
```

- `BASE` 的 commit-sha 用 `git rev-parse HEAD` 取，**寫下當時的值**
- 觸及面宣告的錨點**必須是原檔中實際存在的 heading 逐字**；無則寫 `none`，**不得留空**
- **若發現與原檔互斥 ⇒ 那不是 D，是 R**

### 2.3 生效集合與索引行（**v2.0 改為機檢，見 §5 的 C4**）

- 每份 D 須在 `PREDECESSOR` 指明它接在哪一份之後（第一份寫 `none`）
- **兩份 D 的已申報觸及面重疊（覆寫同一 heading）⇒ 不得平行生效，須升 R**
- 原檔檔頭索引行：`延伸: D-001 <路徑>, D-002 <路徑>`（**這是 §2.1 允許的唯一原檔改動**）
- R 一旦裁定 → 所有延伸檔失效，**且須同時清空索引行**

---

## §3 `section-map` 模式的修訂

### 3.1 節切分

- **掃描單位**：行首 `#{1,6}` 加至少一個空白的 ATX heading
- **fenced code block（` ``` ` 與 `~~~`）內的行不視為 heading**
- 🔴 **簽名區分界用同一支 fence-aware scanner**：簽名區＝**fence 外**第一個 `^##\s*戳記` 起至檔尾
  〔實證：v1.0 唯一的 `^## 戳記` 在第 66 行，落在 L50–69 的 fenced 模板內
  ⇒ **現行 `reconcile_body_hash.sh` 對 v1.0 本身就已取錯本體範圍**。既存缺陷，非本程序引入〕
- **`§META`**＝檔首至第一個 heading 前的 bytes，恆為第一個 entry（即使長度 0）
- **節邊界**＝自 heading 行（含）至**下一個任意層級 heading 行之前**（不含）
  ⇒ **父節不含子節 bytes**。🔴 工具輸出與 stamp brief **必須標明「本節 only，不含子節」**
- **簽名區之後不得有任何其他內容**

### 3.2 `section_id`

```
section_id = sha256( 祖先 heading path 的 length-prefixed bytes ) 的 64 字元小寫 hex || "::" || occurrence
length-prefix: 每段輸出 "<byte 長度>:" + 原始 bytes；串接不插入分隔符
```

- id 恆為 `[0-9a-f]{64}::[0-9]+` ⇒ heading 含 TAB／換行／逗號／NUL／非 UTF-8 時**欄位邊界問題不存在**
- I/O 走 **bytes 路徑**，不經文字解碼
- **NFC／NFD 不是碰撞，是靜默改名**（hash 不同 ⇒ 舊簽名失效 ⇒ fail-closed）
- **人類可讀路徑放顯示欄，不進 hash、不進比對**
- checker 須顯式檢查 duplicate `section_id` 並 FAIL

### 3.3 簽名表與顯示契約

簽名區內，每列一筆，TAB 分隔：

```
SIG	<section_id>	<section_hash>	<family>	<YYYY-MM-DD>	task:<harness-task-id>
SIGINV	<inv_digest>	<family>	<YYYY-MM-DD>	task:<harness-task-id>
SIGREJ	<section_id|*>	<family>	<YYYY-MM-DD>	task:<harness-task-id>	<理由>
```

- `section_hash = sha256(該節原始 bytes)`，**不做任何正規化**
- `inv_digest = sha256( join("\n", [section_id ...依文件順序]) )`——**只含 id 不含 hash**
  ⇒ 改內容不動 inventory；**新增／刪除／改名／重排**才動
  （若無此項，**刪一節後其餘簽名仍全部有效，刪除會靜默通過**）
- hash 對不上當前狀態的列＝**過期列**，不計入有效簽名，checker 須具名報出過期列數
- `SIGREJ` 未被同家族**更晚日期**的 `SIG` 覆蓋 ⇒ FAIL

🔴 **顯示輸出契約**（防「可讀性被 hex 吃掉」）：
`section_sig_check.sh` 與所有 stamp brief **必印** TSV
`<section_id>` TAB `<heading_path>` TAB `本節 only（不含子節）`；
`R-SCOPE` grammar ＝ `hex_id` **或** `hex_id(顯示路徑)`，**機械比對只取 hex**。
🔴 **不得**把 raw heading bytes 塞回 SIG 列。

### 3.4 有效性述詞（**兩個，不可混用**）

```
VALID_content(file_bytes) ⟺
    STAMP-MODE 逐字為 section-map（全檔恰一行）
  ∧ 覆蓋守恆 I-1 成立（見下）
  ∧ 無 duplicate section_id
  ∧ row uniqueness：每個 (family, section_id) 至多一筆有效 SIG；每家至多一筆有效 SIGINV
  ∧ ∀ f ∈ roster: ∃ SIGINV 列 (f, d) 其中 d == 當前 inv_digest
  ∧ ∀ s ∈ 當前 map, ∀ f ∈ roster: ∃ SIG 列 (f, s.id, h) 其中 h == s.section_hash
  ∧ 無有效 SIGREJ

VALID_admit(file) ⟺ VALID_content(file) ∧ 當前候選 SIG 列的 live provenance 通過
```

**不變式 I-1（覆蓋守恆）**：map 內所有節依文件順序 concat，**必須逐 byte 等於**
「檔首 → 簽名區 heading 前」的原始 bytes。checker **每次執行都重算並比對**。

| 用途 | 用哪個 | roster 來源 |
|---|---|---|
| **baseline 歷史掃描**（§3.5） | **`VALID_content`**。🔴 **禁止**對歷史 commit 呼叫 live `check-stamp` | `git show C:scripts/governance_families.json` 的 `review_families` |
| **採計新簽名／發 token** | **`VALID_admit`** | **當前工作區**的同一檔 |

讀取失敗／格式錯／`review_families` 不可解 ⇒ **fail-closed，不准 fallback**。

〔為何拆：`verify_task_provenance.py` 讀的是**工作區 live** audit log（無 commit 參數），
若 VALID 含 provenance，「當場驗歷史全簽」**不可按 commit 重放**——新 clone／audit 輪替時永遠找不到 baseline。
為何釘 roster 時點：否則日後增刪家族會讓**同一份歷史 bytes** 的判定翻轉。〕

### 3.5 baseline

```
baseline(target) = 沿候選序由近而遠，第一個使 VALID_content(target@commit) 成立的 commit 之檔案內容

候選序 = git rev-list --first-parent HEAD -- <canonical_path>   （由近而遠）
merge 第二親：不掃描
rename：不做 --follow ⇒ 新 path 視為無歷史 ⇒ 空 baseline ⇒ 全部節 added
shallow／歷史走不完：具名 FAIL，訊息指明需 --unshallow
🔴 禁止實作自選 git log --all
```

🔴 **legacy／`whole-body` 檔在歷史中不構成 baseline 候選**；其 baseline 為空
⇒ 全部節皆 `added` ⇒ **首次遷移須簽全檔**。

**採計順序本身是規則（不可調換）**：

```
1. 解出 baseline（用 VALID_content）—— 失敗 ⇒ FAIL，不得回退到候選檔內的 SIG 列
2. 以 baseline vs 當前磁碟內容 計算 changed_set（兩側同一支 body_bytes()）
3. 驗 changed_set ⊆ R-SCOPE —— 不成立 ⇒ 拒發 token
4. 通過後才以 VALID_admit 採計候選檔內的新 SIG 列
```

⇒ 步驟 1–2 的輸入**完全不含**候選檔簽名區，也不含任何可寫狀態
⇒ **先寫簽名再交件無法縮小審查範圍**。

**成本契約**：walk 集合限 path history；**進程內 cache** `commit→VALID_content`；
歷史掃描**不得**做 live audit I/O；**禁止靜默截斷歷史**。
〔實測：P16（431 行）path-commits=4、walk 0.046–0.296s、per-VALID 0.76ms；
最壞長歷史檔（`ROADMAP.md`，81 commits）19.35s——非凍結文件。gate 非 hot loop，成本可接受。〕

### 3.6 `changed_set` 與 `R-SCOPE`

```
added    = 當前 map 有、baseline 無
modified = 兩者皆有但 section_hash 不同
deleted  = baseline 有、當前 map 無  ⇒ 以 deleted:<baseline 的 section_id> 表示
changed_set = added ∪ modified ∪ deleted ∪ (inv_digest 改變 ? {§INV} : ∅)
```

- 修訂 brief **必填** `R-SCOPE: <hex_id | hex_id(顯示路徑) | deleted:hex_id>[, ...]`
- `R-SCOPE` **必須逐一列出 `deleted:<id>`**；只列 `§INV` 一律 FAIL
  〔否則刪一整節時，**沒有任何人被要求閱讀被刪掉的內容**〕
- `changed_set ⊆ R-SCOPE` 且 `dependency_closure(changed_set) ⊆ R-SCOPE`，不成立即拒發 token

### 3.7 依賴邊與閉包

**唯一的依賴邊來源 ＝ 節內文的 `§` 錨點引用。**

```
詞界：§[A-Z0-9]+ 之後不得為 [A-Za-z0-9]
resolve(§T, map) = fence 外 heading 行中，於 ATX 標記後以 §T 起始
                   且 §T 之後不為 [A-Za-z0-9] 者，恰一個匹配的 section
  0 匹配 或 >1 匹配 ⇒ 該引用邊硬 FAIL
輸出必須印  §T → <heading path> → <hex section_id>
```

🔴 **全程序詞界只有這一版。** 〔設計階段曾寫成「後不接**小寫**」，
實測 `P16_COMMITTEE_DEBT_SPEC.md:92` 的「見 `§R`」**同時命中** `## §RISK` 與 `## §R`
——因為 `§RISK` 的 `I` 是大寫。改為 `[A-Za-z0-9]` 後四檔實測全部唯一（0/55/0）。〕

⇒ 歧義時**逼作者改引用或改 heading**，而不是補宣告。

| 項 | 規則 |
|---|---|
| 圖的基準 | **baseline 圖 ∪ current 圖**（刪節的邊只存在於 baseline） |
| 邊的方向 | `§` 錨點引用視為由**引用節**指向**被引用節** |
| **出站**閉包 | **硬** |
| `deleted` 節的 **inbound** | **硬**——有人依賴你刪掉的節，契約必然斷 |
| `modified` 節的 **inbound** | **advisory 報告**（見 §8 殘餘風險 3） |

🔴 **`§` closure 的邊界（三句，不得省略）**：
① `§` graph **僅涵蓋單一檔案內**的 heading 依賴
② **跨檔依賴不在 machine closure 內**——paired SPEC/TODO、`SPEC ref:`、Task／Phase 執行序**皆非** `§` 錨點邊
③ 涉及多檔時**由 brief 的 `CROSS-FILE:` 欄明列**；**任何處不得宣稱 `§` closure 覆蓋跨檔依賴**

```
brief 必填一行：  CROSS-FILE: <path>[, <path>...]   |   none
機械觸發：本次修訂的 target path 集合基數 ≥ 2（＝ R-SCOPE 各 section_id 所屬檔 ∪ stamp-target）
          且 CROSS-FILE 缺行或為 none  ⇒  FAIL
```

### 3.8 D／R 分類在本模式下的地位

已遷移檔的修訂＝**就地改 ＋ 重簽 `R-SCOPE`**，不再產生延伸檔。
成本連續正比於 `R-SCOPE` 大小 ⇒ **不再有「叫它 D 就便宜、叫它 R 就貴」的二分懸崖**。

⚠️ **但分類判斷本身不消失**：它現在表現為**依賴閉包爭議**（要不要把某節納入 `R-SCOPE`）。
**§2.1「爭議一律預設 R」照舊適用**（＝爭議時取較大的 `R-SCOPE`）。

---

## §4 grandfather registry

`scripts/stamp_legacy_registry.json`，每筆**只含四欄**：

```json
{"target":"docs/X.md","base_sha256":"<凍結當時 body hash>","owner":"<家族|使用者>","reason":"<一句話>"}
```

- 只有登記在案的檔可用 legacy（無 `STAMP-MODE`）路徑
- `base_sha256` 與磁碟不符 ⇒ FAIL

🔴 **`base_sha256` write-once**：僅在收錄時寫入；之後**只允許整列刪除**（與 mode 翻轉同 commit）。
對已存在列的 `base_sha256`／`target` 任何修改 ⇒ FAIL。
**同一 `target` 一旦刪列，不得再次加入。**

**強制手段（兩層）**：

```
① 相對 git 父 commit 的 registry JSON 列 diff  —— 擋「同 commit 改 base_sha256／改 target」
② 沿 git rev-list --first-parent HEAD -- scripts/stamp_legacy_registry.json 掃歷史 blob
     —— 該 target 曾出現過即禁止再加（tombstone ＝ 歷史出現的事實）
     —— 與 §3.5 baseline 共用同一支 first-parent walker
```

**父端沒有 registry 檔 ⇒ 視為空表，允許首次整檔建立**（明文，**不得靜默**）。
🔴 **不得為此另造 tombstone 狀態檔**——tombstone 是 git 歷史裡既有的事實。

🔴 **退場條件＝結構性，無計時器**：

> **任何對 legacy 檔的修訂，必須先完成遷移。** 未被修改的 legacy 檔**永久可讀，成本為零**。

**誠實表述**：這是**永久 grandfather，不是 bounded migration**。
一份只被下游引用、從不修訂的 legacy 檔會永遠停在 `whole-body`——讀者成本與 v1.0 相同。
〔設計階段曾提「30 天到期」三段式，因「只讀 vs 新操作」無法機械劃界而**整條刪除**。〕

---

## §5 提案 C：延伸檔一致性機檢（**`whole-body` ＋ D 延伸的護欄**）

| 層 | 規則 | 強度 |
|---|---|---|
| C1 | 觸及面宣告的 heading ⊆ BASE 實有 heading 逐字 | **硬** |
| C2 | `PREDECESSOR`／`BASE` 鏈完整、無環、BASE commit 存在 | **硬** |
| C3 | 任兩份生效中 D 的**已申報** `覆寫` 集合相交 ⇒ FAIL | **硬**（只涵蓋已申報者） |
| C4 | 原檔檔頭索引行 ＝ active-D set 的全等投影 | **硬** |
| C5 | `## 內容` 中出現的 heading 逐字 ⊆ 宣告三欄聯集 | **advisory** |

**C4 契約**：
- **active-D SoT ＝** glob `docs/<base>.D-[0-9][0-9][0-9].md` 且該延伸檔戳記有效者。**唯一來源**
- 檔頭索引行 ＝ 該集合的**全等投影**；C4 驗「投影 == SoT」（非兩來源互比，故無 precedence 問題）
- grammar：`^延伸: (D-[0-9]{3} \S+)(, D-[0-9]{3} \S+)*$`；集合為空時**該行必須不存在**

〔**實證動機**：`docs/P16_COMMITTEE_DEBT_SPEC.md` 全檔 **0 次**出現 `D-001` 或 `延伸:`，但 D-001 已生效
⇒ v1.0 §3.3 要求的索引行**從未寫入**，**所有機檢全綠**。程序凍結後**一天內**就發生。〕

**存活至**：`該 BASE 已 section-map ∧ 所有生效 D 已退場 ∧ 索引為空 ∧ 無待結算 provenance`。

🔴 **誠實邊界：C 不能證明「宣告不實」。** C3 只對已申報的覆寫集合成立；
C5 只能抓「內文寫出 heading 逐字但沒宣告」。**改了語意但沒寫出 heading 字面的失效模式仍靠委員對讀。**

**掛點**：`scripts/dext_touchset_check.sh`，由**產出端**呼叫
——① `doc_format_precheck.sh` 的 `dext` 分支（寫檔當下）② `gate.sh` 引用 D 延伸時。

---

## §6 檢查器政策（**取代 v1.0 §6「本程序不新增任何檢查器」**）

> 本程序允許**具名、有界、意外向**的一致性檢查器，逐支列於本節：
> `dext_touchset_check.sh`（§5）、`section_sig_check.sh`（§3、§4）。
> **禁止**無邊界的「防蓄意」掃描擴散——該類提案一律依 §0.1 列入 §9 記錄，不實作。

〔v1.0 §6 末句與 §5 的 C 直接互斥，故本輪同步改寫。v1.0 §3.1「用既有工具，不新增檢查器」一併作廢。〕

### 6.1 現有工具已涵蓋的部分（不重造）

| 意外類型 | 工具 |
|---|---|
| 收斂漏項 | `completeness_check.sh` |
| 未取得簽核 | `reconcile_stamps_check.sh` |
| 委員輪次未結案 | `debt_ledger.sh` ／ `debt_clear.sh` |
| 起草端結構缺陷 | `draft_selfcheck.sh`（**advisory，不得掛 gate**；對延伸檔會穩定誤報，**不要對延伸檔跑**） |

### 6.2 取得戳記前必須先做

若該修訂是委員審查的產物：
1. 各家產出**逐字保存**於 `handoffs/reconcile/<session>/sources/`，用 canonical 四欄格式
2. `bash scripts/completeness_check.sh --lock <session>/sources.lock` **rc=0**
3. 零 finding 的家族須產**恰一條 `P3-00` sentinel**（不得空手）
4. 然後才 append 戳記

〔理由：只要求三家戳記而不要求保存各家產物與 completeness，**手動綜合漏掉一家的 finding 仍可取得三戳記**。
這已發生過兩次（手動 reconcile 漏 grok `T1-01`、IC merge 漏約 15 項），屬「不用蓄意就會發生」。〕

### 6.3 provenance 與 authority 分工

🔴 **前置缺陷（`GOV-DOCS-STAMP-PROVENANCE`，本程序階段 1 的硬前置）**：
`gate.sh` 的 `register-output` **只接受 `handoffs/` 內檔案**，`docs/` 一律拒絕；
而戳記通過 provenance 需要一筆指向該檔的 `committee_output` 事件
⇒ **任何放在 `docs/` 的簽名都無法通過機檢**（`P16_COMMITTEE_DEBT_SPEC.D-001.md` 因此把戳記外置）。

**裁決（兩案都做）**：

**主案**——`register-output` 增列白名單：`docs/` 下**已宣告 `STAMP-MODE`** 的檔可註冊。落地契約：
① brief／dispatch 必須帶**唯一且 canonical 的 `stamp-target`**
② `register-output` 須比對 **target ／ task ／ family ／ 當前 bytes** 四者一致
③ `STAMP-MODE` 須**逐字**為 `section-map` 或 `whole-body`，且路徑在 registry 或已遷移表內
④ **禁止泛化 `docs/**`**——白名單以檔為單位
⑤ docs 檔、audit event、mode／簽名變更**同一 commit 或有可驗 receipt**

**輔案**——`.git/info/exclude` 由 `handoffs/*` 收窄為 `handoffs/*` ＋ `!handoffs/reconcile/**/synth.md`。
〔理由：主案只解 in-file 簽名的 provenance；**不解**既有收斂檔 clone 不可驗——
實測磁碟 69 份 `handoffs/reconcile/*/synth.md`，git 追蹤 **0 份**。〕

🔴 **authority 分工**（兩述詞**定義上不相交**，故無互相蓋章的半綠）：

| 對象 | 唯一權威 |
|---|---|
| **檔案有效性**（`VALID_admit`） | **in-file 簽名 ＋ audit provenance**。收斂檔缺失**不影響**它 |
| **R 輪收斂完整性** | **版控內的收斂檔**（由 `completeness_check` 與債本線獨立強制） |

🔴 **明文禁止**：不得以主案全綠宣稱「既有收斂鏈已可 clone 驗證」。

---

## §7 遷移階段與驗收

| 階段 | 內容 | DoD |
|---|---|---|
| **0** | 本條文取得三家戳記 ＋ 使用者裁定 | §6.3 裁決寫死；**本程序檔自身維持 `whole-body`**（雞生蛋） |
| **1** | §6.3 前置 ＋ 工具實作 ＋ dual-read 測試 | consumer manifest **全表**綠且**列數機械相等**；末段對本程序檔跑只讀 parser canary ＋ 覆蓋等價 dry-run |
| **2** | pilot A＝`docs/DECOUPLE_SCAN2_SPEC.md`（73 行）＋ paired TODO（77 行） | 無既有 D 延伸，先驗純 schema 正負例 |
| **3** | pilot B＝`docs/P16_COMMITTEE_DEBT_SPEC.md`（431 行）＋ 既有 `D-001`（238 行） | 驗 grandfather 與延伸退場 |
| **4** | 本程序檔自身遷移 | 🔴 **gate ＝ 階段 2 或 3 至少一次真遷移 PASS**；canary **必要但不充分** |
| **—** | 其餘 SPEC/TODO（top-level **75**；含子目錄 **96**） | **不強制回溯**；下次修訂時才遷移 |

**lazy migration 的定位**：是**分階段安全 rollout 策略**，不是已證明的長期最低成本。
dual-read 退場條件：最後一份 `whole-body` 遷移後刪除 legacy 分支。

### 7.1 consumer 閉包 ＝ 腳本生成的 manifest，**禁手寫**

**閉包 ＝ ①grep 命中 ∪ ②產出端 hook ∪ ③dual-read 直接輸入 ∪ ④本程序新增元件**

| 類 | 內容 |
|---|---|
| ① | `grep -rl 'reconcile_body_hash\|RECONCILE-STAMP\|body_hash\|STAMP-MODE' scripts` **當場生成** |
| ② | `doc_format_precheck.sh`、`brief_conformance_check.sh`、`verdict_filled_check.sh`、`gov_check.sh` |
| ③ | `governance_families.json`（roster）、`stamp_legacy_registry.json`、audit event schema |
| ④ | `dext_touchset_check.sh`、`section_sig_check.sh`、stamp row validator（**不會被 grep 自動納入**） |

manifest 每列：canonical path／caller／input schema／output rc／hook 時點／pytest nodeid，
並須標註 production／legacy-only／non-production 的**分類規則**與可追溯來源。
**DoD**：manifest 列數 ＝ ①∪②∪③∪④ **機械相等**；未知分類或缺 nodeid ⇒ FAIL。

`scripts/verify_spec_stamp_delta.sh`（27 行、路徑與 sha 前綴硬編）＝**legacy-only**，
**不得**當通用 migration engine；DoD 須明列退場時點。

### 7.2 legacy inventory（**四個分解數字，各附 selector**）

| selector | 值 | 語意 |
|---|---|---|
| `rg -l '^RECONCILE-STAMP:' docs --glob '*.md'` | **0** | canonical **in-file stamp row**（因 §6.3 缺陷，全部外置） |
| `rg -l '^## 戳記' docs --glob '*.md'` | **2** | 戳記**區段標題** |
| `find docs -maxdepth 1 -name '*.D-[0-9][0-9][0-9].md'` | **1** | D 延伸檔 |
| `rg -l 'RECONCILE-STAMP' docs --glob '*.md'` | **31** | **文字提及**（含引用、說明、範例） |

🔴 **不得用單一數字代表「帶戳記的文件數」**——設計階段對此錯了三次。本表為階段 1 manifest 的 input。

---

## §8 誠實邊界（**逐條；引用本程序時不得省略**）

1. **不防蓄意**（§0.1）。有寫入權者可自算 hash 自寫簽名列；後盾是 harness task log 與 audit.log 的獨立佐證。
2. **§5 的 C 不能證明宣告不實**；D-002 型失效模式仍靠委員對讀。
3. 🔴 **地板 ≠ 審查充分**：`modified` 節的 inbound 只出 advisory。
   **具體反例**：baseline 圖 `Q -> P`，P 的正文只把 `MUST` 改成 `MAY`，`R-SCOPE` 只列 P
   ⇒ **gate 仍放行，Q 未被要求審查**。
   **裁定：維持 advisory**（改硬會使 P16 級 `§` 引用爆炸）。
   **配套**：brief 模板**必須把 reverse advisory 清單列為委員必答項**。
   🔴 **本程序任何處不得出現暗示 closure 已完整的措辭。**
4. **語意依賴但未寫出 `§` 錨點**的邊，機械抽不到 ⇒ 靠委員判斷。
5. **搬移型改動成本不降反升**（內容從 A 節剪貼到 B 節，兩節 hash 皆變 ⇒ scope 膨脹而安全未增）。
   move 偵測**列 §9 記錄，不實作**。
6. **父節不含子節**：簽父節**不**代表簽了子樹。
7. **NFC／NFD** 視覺同形但 `section_id` 不同 ⇒ 靜默改名 ⇒ 舊簽名失效（fail-closed，可接受）。
8. `§META` 過肥的檔（如 P16 檔首約 84 行沿革）改一字即全 roster 重簽 META
   ⇒ 遷移指引 **advisory** 建議把沿革移出；**不進硬檢**。
9. **rename 不做 `--follow`** ⇒ 改名後全檔重簽一次。

---

## §9 已知殘留（**記錄，不修**）

依 §0.1，下列問題已知存在且不在本程序範圍。日後真的發生再處理。

| 殘留 | 說明 |
|---|---|
| 戳記區可夾未簽核散文 | body hash 只算簽名區之前；實測 19 份既有 artifact 中 1 份真的有 |
| git 取樣點可被環境覆寫 | `GIT_INDEX_FILE`／`--work-tree`／sparse-checkout／symlink／LFS filter |
| 版本字串會腐爛 | 「基於 SPEC v2.9」這種引用無法機械驗證 |
| 起草端字面檢查可繞過 | `draft_selfcheck.sh` 的檢查皆可用改寫措辭繞過 |
| `gate.sh --reconcile` 不一定驗戳 | 現碼只在同時帶 `--spec` 時才跑 `reconcile_stamps_check` |
| `waived:` 型 reconcile 跳過檢查 | `gate.sh` 直接跳過 completeness 與戳記 |
| **stamp row 產出端無硬檢** | `cx_run.sh` 的 `_maybe_register_stamp_output` 條件不符時是**合法 no-op 回 0**；正確 `## 戳記` ＋ 錯誤 hash 的戳記行在 `--single` 下 **rc=0**；人工／外部編輯器 append 不觸發 hook。修法＝抽 stamp row validator 掛產出端，**與 §3 同批做** |
| move 偵測 | 見 §8.5 |

**上表任一項若真的造成事故** → 屆時開票處理，並把事故寫進 `docs/SCAR_LEDGER.md`。

---

## §10 本程序自身的修訂

- **本程序的修訂一律走 R**（完整三家審 ＋ 使用者裁定），不得自判 D
- 理由：若讓本程序自己判類別，修訂者可用較輕類別逃避重審
- **且須遵守 §0.2**：凡新增元件，必須具名說明為何無法以刪除達成

## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。
