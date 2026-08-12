# 平台機制證據登記表（唯一來源）

FACT-KEY: governance-mechanism
LAST-RULED: 2026-08-13
RULED-BY: 三家委員 consult（`handoffs/reconcile/20260813-govwl03-x-consult-r1/synth.md`）

---

## 本檔要治的病

治理文件寫「這樣改：用某個平台機制達成某件事」，**寫的當下沒有人跑過那個機制**。
出生事故就是這樣來的——SPEC 寫了兩個平台機制當作防線，實跑後發現一個在本機根本不存在、
另一個在本機不可調整。錯誤活過了三輪審查，因為散文裡的機制名看起來就像已經成立的事實。

**本檔把「宣稱用了某個平台機制」從散文變成資料列**，每列必須帶下列兩者之一：

| 證據前綴 | 意思 | 機械檢查 |
|---|---|---|
| `receipt:<路徑>` | 有實跑，證據在這個檔裡 | 該檔**必須實際存在**，否則當場 fail-closed |
| `assumed:<理由>` | 沒實跑，這是顯式假設 | 理由不得為空 |

`assumed:` 是**允許**的。本機制不強迫每個機制都先跑過——它強迫的是
**「沒跑過」這件事必須寫出來、而且可以被機械盤點**（掃生成區塊即得全部未驗機制清單）。
出生事故的真正病灶不是「沒實跑」，是「沒實跑卻讀起來像已經成立」。

## 兩道機械檢查

1. **資料列封閉驗證**（在 `emit`／`--check`／`--write` **三條路徑**上）：
   狀態須在 `_schema.mechanism_status_enum` 內；`平台機制` 須在 `_schema.mechanism_tokens`
   封閉表內；`機制ID` 不得重複；`證據` 須符合上表兩種前綴之一，且 `receipt:` 指向的檔須存在。
   〔三條路徑都掛：只掛 `--check` 時單獨刪 schema 欄即靜默停用，`WL-02` 已實際踩過〕
2. **opt-in 宿主之改法子樹掃描**（在 `--check`）：
   `_schema.mechanism_scope` 明列之檔，其 `- 改法` 子樹內若出現封閉表的平台機制，
   而該機制未登記為現行 ⇒ fail-closed。

改法＝改 `scripts/fact_keys.json` 的 `governance-mechanism`，再跑
`bash scripts/gen_fact_key_blocks.sh --write`。

## 🔴 具名殘留（**交付物不得省略本節**）

1. 🔴 **現樹訊號近零，價值在面向未來。** 施工前實測：五個 opt-in 宿主的改法子樹
   平台機制命中＝**0**（133 行子樹）。本規則**不清理現況**，它攔的是**日後**寫進這些宿主的
   未驗機制。把它當成「已經防住了什麼」是錯的宣稱。
   〔`GROK-R1-P2-02` 實測：封閉表下六檔候選＝0；全檔掃亦僅 3 處非改法敘事〕
2. 🔴 **membership 只靠 opt-in 登記。** 不在 `mechanism_scope` 的檔**完全不掃**，
   即使它寫滿未驗機制。這是刻意的——三家否決了「凡含 FACT-RECEIPT」（回掃 53 檔、
   溯及既往，違反使用者定死之「修正只考慮以後」）與「凡新建 GOV\*」（未封閉 glob）。
   〔`CODEX-R1-P1-02`〕
3. 🔴 **token 表是封閉字面表，不在表內的機制不被偵測。** 用字面表而非 PATH 探測是刻意的：
   本機 `setsid` 不在 PATH，以「可執行檔名」做候選**反而會漏掉出生事故本身**
   〔`GROK-R1-P1-03`／`CODEX-R1-P1-03` 各自實跑 `command -v` 得非零〕。
   代價＝新平台機制須先進表才受管。擴表須改 `_schema.mechanism_tokens`，是**加法**不是黑名單。
4. 🔴 **`receipt:` 只驗檔案存在，不驗內容真的記載了那次實跑。**
   指向一個存在但無關的檔會通過。該層仍靠 review。
5. 🔴 **子樹起點釘死 `- 改法`。** 用標題、表格儲存格或純行內敘述寫改法者不被涵蓋。
   這是為了避開主委原提案的形態——全檔搜「改法」二字經三家實測誤擋率 80–93%，
   誤擋物幾乎全是文件路徑、finding ID、旗標與驗證指令〔`COMPOSER-R1-P0-01`／
   `COMPOSER-R1-P1-01`／`GROK-R1-P1-01`〕。**不得以放寬 token 黑名單修補**——
   那正是本專案反覆吃虧的形態。
6. 🔴 **本表是目錄／投影，不是實作行為的 oracle。** 改表不改碼、改碼不改表，本檔仍會綠。
   行為承重在 `對應測試`（判準 `C-013`–`C-016`），不在本表。

## 登記表

> 欄名見表頭（機械產物）。`實跑結論` 欄記「跑了得到什麼」，是自由文字、不機械驗；
> 真正咬人的是 `證據` 欄——寫 `receipt:` 就必須有檔可查。

<!-- BEGIN GENERATED: governance-mechanism -->
| 機制ID | 平台機制 | 適用範圍 | 證據 | 實跑結論 | 狀態 |
|---|---|---|---|---|---|
| M-001 | setsid | ASSERT 逐行執行後之程序群終止 | receipt:handoffs/reconcile/20260813-govwl03-x-consult-r1/synth.md | 本機不可用——不在 PATH（command -v 非零）；以 set -m 使背景 job 自成 pgid 取代 | 現行 |
| M-002 | ulimit | fork bomb 之第二道防線（壓低 per-user 程序上限） | receipt:handoffs/reconcile/20260813-govwl03-x-consult-r1/synth.md | 硬上限不可降——Invalid argument；只降 soft 必被子程序抬回，故不作為防線 | 現行 |
| M-003 | timeout | ASSERT 逐行逾時包裹 | receipt:docs/GOV_ASSERT_PATHA_NOTE.md | 可用，已上線於寫檔路徑之零執行改法 | 現行 |
| M-004 | flock | gate token 之併發互斥 | assumed:僅出現於敘事段落，尚未被任一改法採用，故未實跑 | 未實跑——列此以示 assumed 是顯式標記而非省略 | 現行 |
<!-- END GENERATED: governance-mechanism -->
