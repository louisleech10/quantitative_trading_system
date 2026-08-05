# GOVB0 SPEC R5 確認輪 | family: composer | task-id: GOVB0-SPEC-R5B

> scope: 唯讀確認 `docs/GOVB0_FRICTION_SPEC.md`（R5 版）；禁改碼／禁改 SPEC。adversarial 對象：`handoffs/reconcile/20260805-govb0-spec-r4/synth.md`（sha `ae304eeb…f88b3fa`，三家 APPROVED）。

## Verdict：需修補後再審（R6）

本輪獨立實跑後，**同意 codex 對 G-1／G-2 的 NOT-CLOSED 裁決**；G-3～G-6 **CLOSED**。本輪新 findings = **2**、新 P0 機制缺口 = **2** ⇒ 不滿足出場判準（findings ≤5 且新 P0 **<2**）。**需要 R6**。

---

## §0 挑戰前提（brief 攤開的假設／事實）

| 標籤 | 內容 | 本輪判定 |
|---|---|---|
| fact-verified | R4 收斂三家 APPROVED | **確認**：`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r4/synth.md` → PASS rc=0 |
| fact-verified | Task 數 11 | **確認**：`grep -c '^\*\*Task '` → `11` rc=0 |
| fact-verified | FACT-RECEIPT 數 10 | **確認**：`grep -c '^- FACT-RECEIPT:'` → `10` rc=0 |
| fact-verified | template_check PASS | **確認**：`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → PASS rc=0 |
| assumed → refuted | G-1 五條規則足以機械執行、無漏掃 | **推翻**：`EOF-1` delimiter + body 內 `<<INNER` 可讓 identifier-only 掃描器 fail-open（見下） |
| assumed → refuted | G-2 八條斷言覆蓋全部併發失效路徑 | **推翻**：precheck→launch 窗口無原子 exclusive claim（見下） |
| brief 更正 | 「委員債務無 OPEN」在派工當下必 rc=1 | **接受 brief 自我更正**；流程固有競態，**不列 finding** |

---

## COMPOSER-R5-P0-01

**斷言**: G-1 契約第 10 項起點 regex 僅接受識別字 delimiter；對 shell 合法但 regex 不匹配的 delimiter（如 `EOF-1`），掃描器不開外層 span，卻會在 body 內把 `<<INNER` 誤開為內層 span，吞掉終止行與其後真實外部派工 ⇒ fail-open。

**碼證**: SPEC Task 2.0 §10 `:194` 起點為 `<<[-]?[[:space:]]*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\1`。獨立探針 `/tmp/govb0-r5b-composer/g1_spec_faithful.py`（依 SPEC 在**行內**搜尋 `<<`，非僅行首）：
- 語料 `cat <<EOF-1` + body 含 `<<INNER` + `EOF-1` 後 `printf ATTACK_EXECUTED` + 終止 `INNER`
- `bash -c` 輸出含 `ATTACK_EXECUTED`；`CONTRACT_SHAPE_SCAN=ALLOW`；`G1_BYPASS=yes`
- 同結構將 `printf` 換為 `codex exec -s workspace-write x` ⇒ `CODEX_VARIANT_SCAN=ALLOW`
RECHECK: `python3 /tmp/govb0-r5b-composer/g1_spec_faithful.py`（探針已於收尾前刪除；可自 `handoffs/20260805-GOVB0-SPEC-R5B.md` 內嵌腳本復原）

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#778f73cae23a

[BLOCKING] 信心度=High。本輪**修正 R4 立場**：先前以「非識別字 delimiter 不開 span ⇒ 最多誤擋」論述 G-1 CLOSED，**未覆蓋巢狀 marker 攻擊**；codex `CODEX-R5-P0-01` 攻擊鏈可獨立重現。`<<1` 與 `EOF-1` 同屬「第一個 marker 不匹配」類，但 body 內第二個**可匹配**的 `<<IDENT` 才是漏掃關鍵。修法：任一 shell 合法 `<<` 若 delimiter 無法按契約解析 ⇒ **整段 fail-closed**；或擴 delimiter grammar 至 shell word 並做 quote removal；immutable corpus 增 `EOF-1`／quoted `EOF-1`／body 假 marker／delimiter 後外部派工 TP+TN 與 mutation。

---

## COMPOSER-R5-P0-02

**斷言**: G-2 定義 owner-safe release 與存活判準，但未要求 `<out>` lock 的**原子 exclusive claim**；兩個 dispatcher 可在「無 lock／無 attempt」precheck 後同時通過並啟動 CLI，八條狀態斷言未封閉此 TOCTOU。

**碼證**: SPEC Task 3.2 lock 生命週期 `:356-373` 有 ownership／release 比對／存活聯集，但全文無 `O_EXCL`／`flock`／`mkdir` lock dir／TOCTOU 等原子取得要求（`rg` 同 codex → rc=1）。獨立探針 `/tmp/govb0-r5b-composer/g2_toctou_probe.py`：A/B 皆先見 absent → barrier 同步 → 皆寫 lock 並 `START`；stdout `TOCTOU_SIM_BOTH_PRECHECKS_PASSED=yes`。RECHECK: 兩個同 `<out>` dispatcher 在 precheck 後 barrier，必須恰一個 CLI start、另一個 rc≠0。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#778f73cae23a

[BLOCKING] 信心度=High。owner-safe release 只防「舊 owner 釋放新 lock」，**不能防雙 owner 同時通過空檢查**。先前「標準 lockfile 實作可互斥」論述把**實作細節**當成 SPEC 已強制，違反專案鐵律「工具必須自帶強制機制」。修法：CLI launch 前以每 `<out>` 原子 exclusive create（`O_CREAT|O_EXCL` 或等價 `mkdir` lock directory）取得 ownership，失敗者重讀 lock 後拒絕；新增 deterministic barrier race test；process-discovery／lock-create 任一錯誤 fail-closed。

---

## 逐條確認（G-1～G-6）

### G-1（`CODEX-R4-P0-01`／`COMPOSER-R4-P1-03`）— **NOT-CLOSED**

五條規則對 identifier delimiter 的標準形態可實作，但**未覆蓋合法非識別字 delimiter + body 內第二 marker** 的漏掃路徑（見 `COMPOSER-R5-P0-01`）。

**反例向量（可證偽，已實跑）**：

```text
cat <<EOF-1
<<INNER
placeholder
EOF-1
codex exec -s workspace-write x
INNER
```

- shell：`printf` 變體已執行外部命令；`codex exec` 變體 `CONTRACT_SHAPE_SCAN=ALLOW`
- 機制：外層 `<<EOF-1` 不匹配 identifier regex ⇒ 不開 span；`<<INNER` 在錯誤位置開 span ⇒ 吞掉 `EOF-1` 終止行與外部派工

**對 codex `CODEX-R5-P0-01` 表態**：**同意 NOT-CLOSED**（獨立探針 `G1_BYPASS=yes`）。

---

### G-2（`CODEX-R4-P0-02`／`COMPOSER-R4-P2-02`）— **NOT-CLOSED**

八條斷言覆蓋 R4 四路徑（舊解新鎖／SIGKILL stale／外層 timeout／刪 lock 進程存活／rename 失敗），但**未明文約束 precheck→launch 的原子取得**（見 `COMPOSER-R5-P0-02`）。

**反例向量（可證偽，已實跑）**：雙 dispatcher 同見 absent → 雙 `START`（`TOCTOU_SIM_BOTH_PRECHECKS_PASSED=yes`）。

**對 codex `CODEX-R5-P0-02` 表態**：**同意 NOT-CLOSED**。

---

### G-3（`CODEX-R4-P2-01`）— **CLOSED**

`grep -c '^- FACT-RECEIPT:' docs/GOVB0_FRICTION_SPEC.md` → `10` rc=0，與 §A「10 條」一致。receipt `govb0-r4-g3-factcount` 證明力足夠。

---

### G-4（`COMPOSER-R4-P1-01`）— **CLOSED**

`grep -n 'COMPOSER-R3-P1-0' docs/GOVB0_FRICTION_SPEC.md` → Task 2.1 語境 `:239` 為 `P1-02`、Task 3.3 語境 `:417` 為 `P1-01`。receipt 與現況名實相符。

---

### G-5（`COMPOSER-R4-P1-02`）— **CLOSED（已接受殘留，非 finding）**

`grep -n 'B-36'` → `:492`／`:495`／`:497`；§N 含「ID 錯位」「無任何機械防線」。依 brief 不重開。

---

### G-6（`COMPOSER-R4-P2-01`）— **CLOSED（SPEC 契約層）**

`grep -n 'PROVISIONAL'` → `:421`（改法）／`:434-437`（三項狀態斷言）。receipt 證明力足夠；TODO 尚未生成屬出場未過後預期，不宣稱實作已完成。

---

## 出場判準核算

| 項目 | 值 |
|---|---|
| 本輪新 findings（計入） | **2** |
| 新 P0 機制缺口 | **2**（G-1 非 identifier delimiter fail-closed；G-2 原子 exclusive lock acquisition） |
| findings ≤5 | ✓ |
| 新 P0 <2 | ✗（2 < 2 為 false） |
| 是否開 R6 | **是** — 僅需關閉上述兩個具體機制缺口並附 heredoc bypass + barrier race 測試；不重開 E-SCOPE／措辭／已知殘留 |

---

## §1 必查（確認輪縮寫）

1. 矛盾/互斥：G-1/G-2 如上；其餘無  
2. 漏項/端到端：G-1 delimiter grammar、G-2 atomic claim 缺 SPEC 明文  
3. 不可測驗收：兩缺口皆有可執行修法與探針  
4–11：無新增（或 OUT-OF-SCOPE）

## 被當成事實的未驗證假設（§0）

- 「heredoc 五條已原型驗證」— **仍為假設**；且本輪探針證偽其充分性  
- 「八條斷言已窮舉併發路徑」— **已證偽**（TOCTOU 未列）

---

ASSUMPTIONS_VERIFIED: reconcile_stamps rc=0；Task=11；FACT-RECEIPT=10；template_check rc=0；G-1 探針 G1_BYPASS=yes + codex variant ALLOW；G-2 TOCTOU both START；G-3～G-6 receipt 與現況一致；SPEC 無 atomic lock 關鍵字
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r4/synth.md` rc=0；`grep -c` Task/FACT-RECEIPT；`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` rc=0；`python3 /tmp/govb0-r5b-composer/g1_spec_faithful.py` rc=0；`python3 /tmp/govb0-r5b-composer/g2_toctou_probe.py` rc=0；`grep -n` B-36/PROVISIONAL/COMPOSER-R3-P1-0
FAILURES_SEEN: 首版 bash 探針 regex 語法錯誤 rc=2，已改 Python 重跑通過
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）

產出檔: handoffs/20260805-govb0-spec-r5-composer.md

RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa task:GOVB0-SPEC-R5B

STATUS: DONE
