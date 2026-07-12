# DOCDRIFT D1+D2 Code Review — Composer

Task-id: docdrift-review | Reviewer: Composer | Date: 2026-07-12  
Scope: `git diff` on CLAUDE.md / ARCHITECTURE.md / DEVELOPMENT_GUIDE.md / ROADMAP.md / AGENTS.md / .cursorrules / check_decoupling*.sh（排除 HANDOFF.md、.claude/settings.json）

---

## ① Diff 是否忠實落地 canonical 決策

**AGREE（主線）** — 六項 reconcile 決策大多已落地：

| 決策 | 證據 | 判定 |
|------|------|------|
| 1. canonical 7 條 = CLAUDE.md（R5=Config、R6=pytest 獨立） | `CLAUDE.md` 加 canonical banner + 表；`ARCHITECTURE.md` §152–174 改寫 R5/R6 | AGREE |
| 2. singleton/callback → Rule 8/9，誠實記殘留 | `CLAUDE.md` L112 Rule 8「現況仍有殘留」；`ARCHITECTURE.md` L171 ⚠️ | AGREE |
| 3. 兩 scanner 編號對照 | `CLAUDE.md` L115、`ARCHITECTURE.md` L174、兩腳本註解頭 | AGREE |
| 4. 全 agent pointer 指 CLAUDE.md | `.cursorrules` L6、`AGENTS.md` L6、`DEVELOPMENT_GUIDE.md` L4 | AGREE |
| 5. D2 假宣稱/過時修補 | §60 里程碑、`factory map` 標示意+78 個、`FF UI` 部分已建、DEV_GUIDE §54 多 agent | AGREE |
| 6. Rule 4 據實 + ROADMAP 債票 | `ARCHITECTURE.md` L162 ⚠️ 1 違規；`ROADMAP.md` P2 票 | AGREE |

**CHALLENGE（未完整落地「據實現況」精神）** — reconcile 只明列 Rule 4，但主表 **R2/R3 仍寫 ✅ 0 violation**，與 scanner 不符（見②③）。決策 1 的「改正 ARCHITECTURE 舊錯表」只修了 R5/R6/singleton，**R2/R3 假綠未收**。

---

## ② 殘留假綠（singleton / callback / Rule 4 / 0 violation）

**驗證命令**：
```bash
# singleton/callback「已修復」
rg -i 'singleton.*已修復|callback.*已修復|無 Mutable global singleton|無 callback/closure bypass' \
  --glob '*.md' --glob '!docs/Archived/**' --glob '!handoffs/**' .

# Rule 4 假綠
rg 'Rule 4.*0 violation|Rule 4.*通過' docs/ ARCHITECTURE.md CLAUDE.md AGENTS.md .cursorrules

# scanner 實況
bash scripts/check_decoupling.sh 2>&1 | grep -E 'Rule [0-9]'
```

**實跑摘要（2026-07-12）**：
```
✅ Rule 1 PASS
❌ Rule 2 FAIL (5 violations)
❌ Rule 3 FAIL (12 violations)
❌ Rule 4 FAIL (1 violation)
✅ Rule 5/6/7 PASS
```

| 檢查項 | 結果 | 判定 |
|--------|------|------|
| singleton 宣稱「已修復」 | 作用域內僅「勿宣稱已修復」警示句，無假綠 | **AGREE** |
| callback 宣稱「已修復/通過」 | Rule 9 寫「✅ 由 scanner lambda 檢查強制」— 與當日 R6(lambda) PASS 一致 | **AGREE** |
| Rule 4 宣稱 0 violation | 主表 + §1437 已改 ⚠️ 1 已知違規 | **AGREE** |
| 其他 0 violation 假綠 | `ARCHITECTURE.md` L160–161：R2/R3 仍 **✅ 0 violation**，與 scanner **FAIL** 矛盾 | **CHALLENGE** |

Brief 驗收寫「check_decoupling.sh 僅 Rule 4 紅」— **與本次實跑不符**（R2/R3 亦紅）。可證偽：重跑上述 scanner 命令。

**結論②**：narrow scope（singleton/callback/Rule4）**已清**；但 ARCHITECTURE 主表 **R2/R3 殘留假綠**，整體 **CHALLENGE**。

---

## ③ 新引入 / 殘留自相矛盾

| 矛盾點 | 證據 | 判定 |
|--------|------|------|
| canonical R5/R6 vs §399–407 演進表 | L405 Config、L406 Test 配置隔離 — 與 CLAUDE 一致 | **AGREE** |
| §541「Rule 6 = Pipeline 獨立可測」 | 語意偏模組可測性，非 canonical R6（pytest 不依賴 run_api） | **CHALLENGE**（輕微；建議改寫或加「此處 R6 指可測模組性，canonical R6 見 CLAUDE」） |
| Rule 6「pytest tests/momentum/ 獨立跑」vs phase4 實際範圍 | `check_decoupling_phase4.sh` L59 只跑 `tests/momentum/Strategy/`；ARCHITECTURE L164 / CLAUDE R6 寫全 `tests/momentum/` | **CHALLENGE** |
| 主表 R2/R3 綠 vs scanner 紅 | 見② | **CHALLENGE**（嚴重） |
| IC 模組小節 §1437–1445 | Rule 4 已交叉引用全庫 1 違規；singleton 有 Rule 8 警示 | **AGREE** |

---

## ④ DEV_GUIDE 分層 vs `docs/IC_API_TEST_LAYERING.md`

**AGREE（核心對齊）**：
- DEV_GUIDE §238–264 明確 pointer 至 `IC_API_TEST_LAYERING.md`，列出 L0/L1/L2。
- 生產路徑禁假數據、**數據正確性/IC/PIT 必真 kline**、L0/mutation/perf 合成合法 — 與 TEST_LAYERING 鐵律 + LEGIT-SYNTHETIC 判準一致。
- 未把數據正確性測試放水。

**CHALLENGE（L1 缺口）**：
- `IC_API_TEST_LAYERING.md` L16–17：**L1** = 走 IC service ingest、不斷言 IC 數值，仍須 **真 kline session fixture**。
- `DEVELOPMENT_GUIDE.md` L346 寫：「若只測路由/schema/護欄行為/效能 → 合成恰當」— 未區分 **L0（不 ingest）** 與 **L1（ingest 但不斷言 IC 值）**；依字面可能誤導 L1 用合成 → 重犯 Phase 1 違憲型。
- **可證偽建議**：DEV_GUIDE 測試規範加一句：「走 IC service ingest（L1）→ 必 `ic_api_real_kline` 類 fixture，即使只斷言 schema/HTTP。」

---

## ⑤ Pointer 錨點穩定性

| Pointer | 錨點存在？ | 淘汰檔？ | 判定 |
|---------|-----------|---------|------|
| `CLAUDE.md` §The 7 Decoupling Rules | `rg '^## The 7 Decoupling Rules' CLAUDE.md` → 命中 L97 | — | **AGREE** |
| `docs/IC_API_TEST_LAYERING.md` | 檔案存在 | — | **AGREE** |
| `docs/MULTI_AGENT_ORCHESTRATION.md` | DEV_GUIDE §54 引用 | — | **AGREE** |
| ARCHITECTURE 文檔同步 L536 | 改指 CLAUDE/AGENTS/.cursorrules；註明 copilot-instructions 已淘汰 | 無指向淘汰檔 | **AGREE** |
| CI 可 grep 檢 | 錨點字串固定、可 `rg`；**diff 未加 CI job** | — | **AGREE**（可後續加腳本，非本次 BLOCK 主因） |

---

## ⑥ Scanner 註解是否正確

**`check_decoupling.sh` — AGREE**：
- 註解 L8–13 與腳本一致：R1–4/7 = canonical；腳本 R5 = `api.core.config` grep（L121–131）；腳本 R6 = lambda monkeypatch grep（L134–145）= named Rule 9。
- grep 邏輯 **零改**，僅註解頭。

**`check_decoupling_phase4.sh` — AGREE（附註）**：
- 註解 L5–8 正確：R6 = pytest；與 `check_decoupling.sh` R6 語意不同。
- 註解寫「抽驗 R1/2/3」— 與實作一致（僅 Strategy/Optimization 子目錄 + 單檔 protocol/factory 探針），**未誤稱全庫 R1–3**。
- **附註**：若 ARCHITECTURE 將 phase4 等同「全庫 R6 綠」，則是 **文件過度推論**，非註解錯誤。

---

## 其他觀察（非 BLOCK 主因）

- `momentum/factories.py` `^def create_` 計數 = **78**，與 ARCHITECTURE 註解一致。
- `AGENTS.md` L86–96 仍保留完整 7 條表（無 Rule 8/9）；頂部 pointer L6 已聲明 CLAUDE 權威 — **可接受**，但長期漂移風險，建議改為單行 pointer（非本次必改）。
- diff 含 `.claude/gate/audit.log` — 不在 brief 審查範圍，忽略。

---

## 總結

| # | 判定 |
|---|------|
| ① | AGREE 主決策；CHALLENGE R2/R3 未據實 |
| ② | AGREE singleton/callback/Rule4；CHALLENGE R2/R3 假綠 |
| ③ | CHALLENGE R2/R3、Rule6 範圍過宣、§541 語意 |
| ④ | AGREE 主軸；CHALLENGE L1 未顯式 |
| ⑤ | AGREE |
| ⑥ | AGREE |

**建議修復（由 Claude 落地，非本 review 改檔）**：
1. `ARCHITECTURE.md` 主表 R2/R3 改為據實（參 scanner 計數或「見 check_decoupling.sh」動態表述）。
2. `DEVELOPMENT_GUIDE.md` 測試規範補 L1 真 kline 要件。
3. Rule 6 描述與 phase4 實際範圍對齊（或註明 phase4 為抽驗子集）。

VERDICT: BLOCK(ARCHITECTURE 主表 R2/R3 仍宣稱「✅ 0 violation」與 2026-07-12 `check_decoupling.sh` 實跑 R2=5/R3=12 矛盾，屬 docdrift 核心要修的殘留假綠；次要：DEV_GUIDE 未顯式覆蓋 L1 真 kline、Rule6/phase4 範圍過宣)
