# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任（Fable/Opus）；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：開工 GAP-1（DSR/PBO/MinBTL 策略層防偽）

前情：**IC 健檢 epic 已於 2026-08-17 全鏈路收工**（六批實作＋三家 review 全 CLOSED＋三家戳記＋債清，
全部已 push；細節看 `白話說明/IC健檢施工進度.md` 與 git log `feat(ic-hc)` 系列，本檔不重述）。

GAP-1＝**大任務，走完整管線**：
1. 開工前先稽核本檔＋ROADMAP vs repo 實況（鐵律）。
2. 偵察＝Claude＋三委員平行（鐵律）；起點材料＝`docs/IC_QUANT_GAP_REGISTRY.md` #1
   ＋`handoffs/GAP1-KICKOFF-SEED.md`（三件套定義/設計要點/可複用資產/N 帳本難點）。
3. Claude 起草 SPEC → 三家 adversarial → 複驗＋戳記 → 白話閘給使用者 → TODO 同流程 → 實作。

## 現在的狀態

| 事實 | 怎麼查 |
|---|---|
| 待推筆數 | `git log --oneline origin/main..HEAD \| wc -l`（收工時=0） |
| 量化主線下一步 | `docs/ROADMAP.md` 狀態表（GAP-1 首位） |
| 既有紅（勿誤認新紅） | 產品套件 14 條（A/B 隔離證明）＋治理段5 4 條（f50f9d0f 舊契約遺留） |
| 待手清雜物 | 清單在 `handoffs/GAP1-KICKOFF-SEED.md` 末節 |

## ⚠ 最常咬人的操作紀律（完整清單在 CLAUDE.md Gotchas，本檔不重述）

- 🔴 `git add` 逐檔列出；rc 直取禁 pipe；commit 訊息 `-F` 寫檔（`.claude/tmp/`）＋VERIFY receipt
- 🔴 改檔用 Edit/Write；`docs/API_SPECIFICATION.md` **實務不可編輯**（檔名撞 SPEC 格式快閘）
- 🔴 凡動 `scripts/` 的 commit，四份治理白話檔同 commit 更新（sync 守衛自指循環）
- 🔴 新增 `白話說明/*.md` 須同步在 `plain_docs_sync_check.sh` `_watched_for` 加 WATCHED
