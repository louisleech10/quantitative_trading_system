# GAP-3 TODO 對抗審 R8（閉合輪）— grok

family: grok  
task-id: 20260820-GAP3-X-REVIEW-R8  
scope: `docs/GAP3_EVENT_TODO.md` @ `8b1047c2`（sha256 `b7bbe799d905…11684`）；權威 `docs/GAP3_EVENT_SPEC.md` FROZEN（sha256 `544c2922ef2e…23699`）；R7 裁決 `handoffs/reconcile/20260820-gap3-x-review-r7/synth.md`；禁改碼  
brief: `handoffs/20260820-gap3-todo-adv-r2-brief.md`  
brief-kind: closure

---

## 前提挑戰（§0）

| brief 前提 | 判定 | 本輪核對 |
|---|---|---|
| fact-verified: R7 synth completeness 全層 PASS＋債銷帳 | **fact-verified（採 brief；未重跑 `--lock`）** | 以 R7 synth 正文＋本輪 TODO 寫回對照為準 |
| fact-verified: v0.2 M1–M12 仍與 SPEC byte-identical | **fact-verified（本輪重跑）** | `diff <(sed -n '370,382p' docs/GAP3_EVENT_SPEC.md) <(awk '/^- \*\*mutation 條件\*\*/,/^  - M12/' docs/GAP3_EVENT_TODO.md)` → 空輸出，`diff_rc=0` |
| fact-verified: `doc_format_precheck.sh` TODO rc=0 | **fact-verified（本輪重跑）** | `bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md` → rc=0 |
| assumed: 12 群集寫回全部到位、無一漏寫或寫錯位置 | **攻後＝成立（本家義務兩條＋順掃 W1–W12/W14）** | 見下「原提出方閉合表」＋順掃表；W11/W12 於 B1.1/B1.0 改法＋驗證皆命中 |
| assumed: W7 五算子精確語意自洽（含 d=0 不計交叉、cross_count 0 合法） | **攻後＝成立** | 見下「W7 攻擊」；定義自洽，不升級 finding |

VERIFY（本輪實跑）:
```
shasum -a 256 docs/GAP3_EVENT_TODO.md
→ b7bbe799d9051e3e5b469d4e261167ee30041a10e2e4b7319f5d42a74aa11684
shasum -a 256 docs/GAP3_EVENT_SPEC.md
→ 544c2922ef2ea09fe21bd6fda514f07e51a7f90f7f78c6409bfe38a7ccd23699
git log -1 --oneline -- docs/GAP3_EVENT_TODO.md → 8b1047c2 docs(gap3): TODO v0.2——R7 對抗審寫回…
grep -n 't0_open\|decision_at ≤ t0' docs/GAP3_EVENT_TODO.md → L84（改法）、L90（驗證負例）
grep -n '批內單值\|單批 `direction`' docs/GAP3_EVENT_TODO.md → L63（改法）、L69（驗證⑦）
diff …SPEC 370-382… vs …TODO mutation… → empty, rc=0
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md → rc=0
```

---

## 1. 原提出方逐條 CLOSED？（brief 必答 1；grok＝2 條）

| 原 ID | RECHECK（原文命令） | 觀測 | 狀態 |
|---|---|---|---|
| GROK-R7-P1-01 | `grep -n 't0_open\|decision_at ≤ t0' docs/GAP3_EVENT_TODO.md` | **L84** 偽碼顯式 validator `decision_at ≤ t0_open_ms`＋failures reason=`no_boundary_match`（標 W11/GROK-R7-P1-01）；**L90** 驗證含該負例（竄改使 `decision_at > t0` ⇒ 斷言紅）。reason 字面 ∈ SPEC D2-4 枚舉聯集。 | **CLOSED** |
| GROK-R7-P1-02 | `grep -n '批內單值\|匯入批內單值' docs/GAP3_EVENT_TODO.md`（等價亦命中「單批 \`direction\`」） | **L63** 偽碼「單批 `direction` 唯一值檢…匯入批內單值」（W12/GROK-R7-P1-02）；**L69** 驗證⑦「單批 `direction` 混值（long＋short）⇒ 拒」。規則住契約檔 validator/_doc，未複列鍵表。 | **CLOSED** |

兩條原反例均在改法＋驗證雙落點；**0 NOT-CLOSED**。

---

## 2. v0.2 新引入問題？（brief 必答 2；本家順掃）

| 面 | 結果 |
|---|---|
| W1 SoT／層級宣告 | §0 頭＋B1.0/B2.4 genesis 註記＋「檔建立後以契約檔為準」在場；不重開 |
| W2 白名單 ⑦⑧ | L15 已列 factories／收尾文件；**非升級殘差**：括註仍寫「唯此六項」但正文已列 ①–⑧——數字標籤與 ⑦⑧ 正文足以指導執行端，不列 finding |
| W3–W6／W8–W10／W14 | 各群集關鍵字／Gate 命令／測試路徑探針命中（conditional_ic oracle、digest 篡改、failures 三元、expression_role、exit 輸入、ASSERT 全文、vitest `gap3`、scale receipt、`tests/momentum/feature_engineering/` 新建宣告）；`ls tests/momentum/feature_engineering` → 不存在（W14 前提仍真） |
| W7 五算子（重點攻） | **自洽**（見下）；邊界①短句「非 0」與 `cross_count` 例外之張力已由實作要點 2「除 cross_count 外…」消解 |
| M1–M12／doc_format | byte-identical＋precheck rc=0 |
| SPEC 衝突／越權 | 未見需擋凍結之新衝突；W7 為 V13 授權細化（SPEC 只命名算子） |

### W7 攻擊（d=0 不計交叉、cross_count 0 合法）

- **定義**：交叉＝`d_i=a_i−b_i` 嚴格變號且兩端皆非 NaN 非 0；窗＝閉區間 `[t−lookback+1,t]` 含當前根。
- **反例手推**：序列差 `+1,0,−1` → 兩步皆因含 0 端而不計交叉 ⇒ `cross_count=0`、`bars_since_cross=NaN`；乾淨翻轉 `+1,−1` → 計 1 次、若在 t 則 `bars_since=0`。與「d=0 不計」字面一致，非靜默漏洞。
- **cross_count=0**：計數語意（無事件＝0）vs 狀態語意（無事件＝NaN）已在算子條文明分；與 `bars_since_*`／`consecutive_run` 的 NaN 契約不互斥。
- **結論**：合理且自洽的 TODO 階段細化；**不升級 finding**（若日後要改「穿零也算交叉」須走 SPEC-AMENDMENT／契約，非本輪閉合阻塞）。

§1 十一類（本輪焦點＝R7 寫回閉合面）：矛盾／漏項／不可測／quant／過度工程／OOM／cache／API／測試／agent 可執行／短命工 → **無新 BLOCKING/MAJOR**。

---

## 3. 可以凍結嗎？（brief 必答 3）

**可以**——本家兩條原提出方 finding 皆 **CLOSED**；順掃未見須先修之 BLOCKING／NOT-CLOSED；M1–M12 仍 byte-identical；W7 攻擊後仍成立。同意 TODO FROZEN＋三家戳記流程（本交件蓋 APPROVED 戳記如下）。

---

## Verdict：可凍結（TODO FROZEN＋三家戳記）

R8 閉合：GROK-R7-P1-01／P1-02 同一反例重跑皆 CLOSED；v0.2 寫回未引入本家認定之新阻擋項；W7 定義攻擊後自洽。本家 **0 findings**（sentinel 如下）。

---

## GROK-R8-P3-00

**斷言**: 本輪逐項核對後無 finding；原提出方 GROK-R7-P1-01／P1-02 於 TODO v0.2 同一反例重跑皆 CLOSED（B1.1 `t0_open`／B1.0 批內單值皆落在改法＋驗證）；W7 五算子（含 d=0 不計交叉、cross_count 0 合法）攻擊後自洽；M1–M12 仍與 SPEC byte-identical；無新 BLOCKING／NOT-CLOSED 阻擋 TODO 凍結。

**碼證**: `grep -n 't0_open\|decision_at ≤ t0' docs/GAP3_EVENT_TODO.md` → L84＋L90；`grep -n '批內單值\|單批 \`direction\`' docs/GAP3_EVENT_TODO.md` → L63＋L69；`shasum -a 256 docs/GAP3_EVENT_TODO.md` → `b7bbe799d905…11684`（@`8b1047c2`）；`diff` SPEC§V370–382 vs TODO mutation → 空、`diff_rc=0`；`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md` → rc=0；W7 手推 `+1,0,−1`⇒cross_count=0／`+1,−1`⇒1；`ls tests/momentum/feature_engineering` → No such file（W14 前提）；順掃 W1–W12/W14 關鍵字均命中。

**來源摘要**: docs/GAP3_EVENT_TODO.md#b7bbe799d905; docs/GAP3_EVENT_SPEC.md#544c2922ef2e; handoffs/reconcile/20260820-gap3-x-review-r7/synth.md#651ae9db5d00; handoffs/20260820-gap3-todo-adv-r2-brief.md#ff0c1be239f2; handoffs/20260820-gap3-x-review-r7-grok.md#41f7dc4302a2

sentinel：0 findings（實質）；上列為 R8 原提出方兩條 RECHECK＋W7 定義攻擊＋12 群集順掃＋M1–M12／precheck 機械複驗摘要。

---

## 被當成事實的未驗證假設（§0 殘列）

| 宣稱 | 判定 |
|---|---|
| 12 群集寫回全部到位 | 本輪攻後改為 **fact-verified**（本家兩條 CLOSED＋順掃命中） |
| W7 五算子語意自洽 | 本輪攻後改為 **fact-verified**（手推＋條文互證） |
| M1–M12 byte-identical／doc_format rc=0 | **fact-verified**（本輪重跑） |
| R7 completeness＋債銷帳 | 採 brief fact-verified；**本輪未重跑** `--lock` |

---

## 戳記

RECONCILE-STAMP: grok APPROVED 2026-08-20 sha256:b7bbe799d9051e3e5b469d4e261167ee30041a10e2e4b7319f5d42a74aa11684 task:20260820-GAP3-X-REVIEW-R8

（sha256＝本輪核准標的 `docs/GAP3_EVENT_TODO.md` @ `8b1047c2` 全檔雜湊；brief 明示 synth 非 gating 戳記檔。）

---

## /tmp 收尾

保留 `/tmp/claude-501`。本輪未另建 workdir；未動 `cc-socks`／既有 push log。

## 產出檔

- `handoffs/20260820-gap3-x-review-r8-grok.md`（本檔）
- `handoffs/20260820-GAP3-X-REVIEW-R8.md`（交接）

ASSUMPTIONS_VERIFIED: TODO @8b1047c2 sha256 實跑；GROK-R7-P1-01/02 RECHECK CLOSED；W7 攻擊後自洽；M1–M12 diff 空；doc_format rc=0；W1–W12/W14 順掃命中  
TESTS_RUN: `grep` t0_open／批內單值；`diff` M1–M12 → empty rc=0；`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md` → rc=0；`shasum -a 256` TODO/SPEC；completeness 見下  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（禁改碼；僅審查產出）  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護；交接寫入 `handoffs/20260820-GAP3-X-REVIEW-R8.md`

STATUS: DONE
