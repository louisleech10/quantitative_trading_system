# 委員派工規範（新增家族 / 如何派工 / 收集綜合）

> 2026-07-25 建立。使用者只提需求（要幾家、審什麼）；**流程與腳本由 Claude 依本規範執行**。
> 家族數是**動態**的（2/3/4…N 家，未來可能更多）——本規範與所有腳本一律**不寫死家族**。

---

## A. 如何新增一個委員家族

新增家族只需改 **2 個地方**（歷史事故：grok 曾散在 4 檔 11 處逐處手補，必漏）：

1. **`scripts/governance_families.json`（SoT，單一真相源）**
   - `families`：所有合法家族（必加）
   - `review_families`：能算 review/簽核 quorum 的家族（視角色決定要不要加）
   - `executor_clis`：該家族的 CLI 名（若它能實作/執行）
   - `advisory_only`：只做諮詢、**不計入 quorum** 者（如 `agy`）
2. **`scripts/cx_run.sh` 的 CLI 配方**
   - 在 `case "${fam}"` 加一段該 CLI 的實際呼叫（每家 CLI 參數不同，**無法通用化**，這是唯一必須手寫的地方）

**改完自檢（必跑）**：
```bash
bash scripts/gov_check.sh --fast                    # 語法
. scripts/governance_families.sh; families_get families ' '   # SoT 讀得到新家族
pytest tests/governance/test_family_registry.py -q  # drift 測試（釘住所有消費者==SoT）
```
> `gate.sh` / `reconcile_stamps_check.sh` / `verify_task_provenance.py` / `completeness_check.sh`
> 都**動態讀 SoT**，不需逐一修改；drift 測試會抓出任何漏接的消費者。

---

## B. 如何派工（標準流程）

### 1) 寫 brief（用腳本產骨架，免得被 P1-1 閘擋）
```bash
bash scripts/new_brief.sh <review|consult|closure|impl|stamp> handoffs/<名稱>-BRIEF.md "標題"
```
然後**填入真實內容**（標的、前提、必答）。硬性要求：
- `brief-kind:` 必填；findings 類（review/consult/closure）須**引用委員範本** + **≥1 `fact-verified:`** + **≥1 `assumed:`**
- token 必須是**字面**（寫成 `**assumed**:` 粗體會打斷 grep → 被自己的閘擋）
- `assumed:` 要寫**真正可能錯的前提**，並明說「請優先攻這條」——這是讓委員找到真洞的關鍵

### 2) 派 N 家（一個命令，平行）
```bash
bash scripts/committee_run.sh <brief> <out前綴> <fam1,fam2,...> -- \
  --intent "..." --risk low|high --facts-asked "..." --review-role "..." --template "n/a: 用 brief"
```
- 家族數任意（`codex,composer` / `codex,composer,grok` / 更多）；**對 SoT 驗證**，未知家族 fail-closed
- 自動：開 gate token → 平行派 N 家 → 等全部完成 → 逐家回報
- 產出 `<out前綴>-<family>.md`（檔名帶家族後綴，下一步的工具靠它推家族）
- **Claude 執行方式**：`Bash run_in_background: true` 跑本腳本；**不可自行加 `&`**

### 3) 收集綜合（禁手做）
```bash
bash scripts/reconcile_build.sh <session名> <out前綴>-*.md
```
- 自動：建 session → 寫 lock → 逐字組 synth 骨架 → 跑 completeness 驗 **0 掉項**
- 然後**我手填** synth 上方「群集/處置」（判斷部分）；**不可動下方 `## <ID>` 區塊**
- 若動到了 → 重跑 `bash scripts/completeness_check.sh --lock <session>/sources.lock`

### 4) 閉合（findings 有 BLOCKING/MAJOR 時）
- 修完後**派回原提出方複驗**（`brief-kind: closure`），確認該 finding 真的關閉
- 原則：**Block/Bug 退回修改後，須由原提出方重跑同一反例**，不憑「已修」信任

---

## C. 角色鐵律（違反會被機檢或制度擋）

- **實作者不自審**：實作是哪一家，審查就**不能**是它。當前分工見 `docs/MULTI_AGENT_ORCHESTRATION.md` §1「現行分工」行（動態，以使用者最新指示為準）
- **code review = 2 個非實作者家族**（不是一家）
- `advisory_only`（如 agy）**不計入 quorum**，只做諮詢
- 審查對象優先是**真實 code diff**，不是偽碼描述（偽碼沒有可跑的 oracle，只會多燒輪）

---

## D. 常見卡點（都踩過）

| 症狀 | 原因 | 解法 |
|---|---|---|
| brief 被 cx_run 擋 | `assumed`/`fact-verified` 寫成粗體或缺 | 用 `new_brief.sh` 產骨架；token 保持字面 |
| 委員回 STAMP-BLOCKED | brief 指了「無戳記的 reconcile/診斷檔」當輸入，委員以為是 gating 檔 | brief 加前置說明：「此為診斷輸入、非 gating 檔，勿 STAMP-BLOCK」 |
| completeness 擋我的 synth | 我把 findings 精簡/改寫了（要 byte-faithful） | 用 `reconcile_build.sh` 產骨架，只填上方群集區 |
| 委員 CLI infra 卡死 | 該 CLI 自身問題（非本 repo） | 停掉重派；記錄但別誤判成腳本 bug |
