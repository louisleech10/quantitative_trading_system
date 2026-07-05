# INSTREV Phase A 實作 — instrev-phasea-impl (Composer 2.5 / cursor-agent)

**Task-id**: instrev-phasea-impl  
**Scope**: Phase 1–5（Phase 6 記憶層不在派工 scope）  
**Date**: 2026-07-05

## 正在做
- Phase 1–5 全部完成；§B Gate 全過

## 待辦
- Claude：Phase 6 記憶層 pointer 化（repo 外）
- Claude：更新根 HANDOFF.md 宣告 Phase A 完成

## 阻塞
- none

## 本次決策
- 依 SPEC/TODO 逐 Task 實作；未擴 scope
- `docs/ARCHITECTURE.md:485` 等檔名級 copilot 引用未改（U-11 / Task 1.2 邊界）

## 踩坑提醒
- §B Gate `grep -cE` 錨點：工具表用「§1 現行分工行」措辭，勿再寫 `現行分工(` 第二處
- sync check 綠 ≠ A-12 token 已齊；以 MISSING_CONTRACT 迴圈為準（U-9 Phase B）

---

## 改動摘要

| Phase | 檔案 | 動作 |
|-------|------|------|
| 1.1 | `docs/SCAR_LEDGER.md` | 新建 12 條事故帳本 |
| 1.2 | `.github/copilot-instructions.md` | 739→8 行 pointer |
| 2.1–2.2 | `CLAUDE.md` | 216→128 行；敘事移 SCAR；決策表；10 分鐘輪詢；選層 pointer |
| 3.1–3.3 | `docs/MULTI_AGENT_ORCHESTRATION.md` | 單一現行分工行；中型不跳步；debug 2 輪 |
| 3.3 | `docs/MULTI_AGENT_BOOTSTRAP.md` L35 | debug 2 輪 |
| 4.1–4.3 | `AGENTS.md`, `.cursorrules` | HANDOFF 所有權；debug 2 輪；A-12 三 token |
| 5.1 | `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_GUIDE.md` | 檔頭 staleness banner 各 +2 行 |

---

## §B Gate 輸出（真跑）

```
=== §B Gate instrev-phasea-impl 2026-07-05T13:51:46Z ===

# bash scripts/check_agent_contract_sync.sh
=== 執行端合約一致性（AGENTS.md / .cursorrules）===
=== 全體關鍵概念存在性 ===
✅ 四源關鍵不變式一致（presence check）

# wc -l CLAUDE.md
     128 CLAUDE.md
# wc -l .github/copilot-instructions.md
       8 .github/copilot-instructions.md

# grep -n "3 輪\|≤3 輪" ...
(0 matches, exit 1)

# grep -rn "每 5 分鐘" ...
(0 matches)

# grep -cE anchor 現行分工
1

# ls docs/SCAR_LEDGER.md
docs/SCAR_LEDGER.md

# CLAUDE.md 12-token zero-deletion
(done — no DELETED_RULE = pass)

# A-12 contract tokens
(done — no MISSING_CONTRACT = pass)

# narrative moved (SCAR has / CLAUDE lacks)
(done — no SCAR_MISSING/NOT_MOVED = pass)
```

---

## 結構化收尾報告

```
ASSUMPTIONS_VERIFIED: SPEC §A receipt（copilot 無 scripts 依賴、sync baseline 四源一致）沿用；改後 bash scripts/check_agent_contract_sync.sh exit 0；§B Gate 全套真跑全過；CLAUDE 128 行 ≤140；copilot 8 行 ≤15
TESTS_RUN: §B Gate 全套（見上）；額外 grep 記憶/任務分派決策表/T-D/ARCH+DEV diff --stat 各 +2 行 — 全 pass
FAILURES_SEEN: none
SCOPE_CHANGES: docs/ARCHITECTURE.md L485 等檔名級 copilot 引用保留（Task 1.2 邊界，pointer 檔不刪）；templates/ 內若有 3 輪殘留未改（超 scope）
NUMERIC_OR_SCHEMA_IMPACT: none（純文件；無程式/數值/schema 改動）
```

---

## instrev-phasea-impl-fix1（2026-07-05）

### 正在做
- Codex code review 2 BLOCKING 已修

### 待辦
- Claude 驗收 fix1 diff

### 阻塞
- none

### 本次決策
- BLOCKING-1：§6/§7 主力措辭改中性，一律 pointer §1 現行分工行
- BLOCKING-2：CLAUDE.md 三方鐵律補回 4 項 load-bearing 義務（精簡措辭，零刪減義務）

### 自驗
```bash
grep -nE 'Codex 主力|預設 codex 主力' docs/MULTI_AGENT_ORCHESTRATION.md  # 空
grep -nE '任一方有疑|merge|split|洩漏|byte' CLAUDE.md  # L93 全命中
bash scripts/check_agent_contract_sync.sh  # exit 0
wc -l CLAUDE.md  # 128 ≤140
```

### 結構化收尾報告

```
ASSUMPTIONS_VERIFIED: git show HEAD:CLAUDE.md 三方鐵律段為義務來源；§1 現行分工行為唯一主力結論
TESTS_RUN: 上述 4 條自驗命令全 pass
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅 docs/MULTI_AGENT_ORCHESTRATION.md §6/§7 + CLAUDE.md 三方段）
NUMERIC_OR_SCHEMA_IMPACT: none
```

STATUS: DONE
