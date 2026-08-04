# 第 0 批 SPEC R2 閉合複核

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（**本輪 ROUND=R2**；見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）

- 🔴 **本輪 `brief-kind=review`，不需要戳記。產出中請勿出現 `## RECONCILE-STAMP` 這個標題。**
  原因＝`票 B-32`（`cx_run.sh:512` 無條件注入該詞，而 `completeness_check.sh:179` 判 `## RECONCILE-STAMP` 為非法 finding ID）。修法在本 SPEC 的 Phase 1，尚未實作。
- `handoffs/reconcile/*/synth.md` 是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK。
- **禁改碼**。探針一律隔離副本；禁變異 repo 內 `scripts/*.sh`／`tests/**`；禁 `git checkout`／`git restore`。
- **rc 一律直接取，禁經 pipe**。
- ⚠️ `.claude/gate/ts_stamp.log` 為 `Non-ISO extended-ASCII`＋NEL；預設 locale 下 `grep` 靜默返空。需分析時用 `LC_ALL=C grep -a`，**但勿 `export`**（會洩漏進其他檢查流程）。

## 審查標的

- **`docs/GOVB0_FRICTION_SPEC.md`（R2 版）** —— 本輪唯一標的。`bash scripts/template_check.sh spec …` rc=0。
- R1 收斂裁決：`handoffs/reconcile/20260804-govb0-spec-r1/synth.md`（19 findings，`completeness_check --lock` rc=0，D-1～D-13）
- R1 你自己的產出：`handoffs/20260804-govb0-spec-r1-<你的家族>.md`

## R2 相對 R1 的變更清單（逐條對應 D 群集）

| D 群 | 你們的 finding | R2 怎麼改 |
|---|---|---|
| D-1 | `CODEX-R1-P0-02`／`COMPOSER-R1-P0-01` | 新增 **Task 2.0 詞法契約**（5 項，含 `-c` 遞迴／帶引號路徑／路徑正規化／未閉合引號 fail-closed）；Task 2.1 改為依契約實作並附 `-c` 遞迴 mutation |
| D-2 | `CODEX-R1-P0-03`／`COMPOSER-R1-P0-02` | Task 3.2 全面改寫為 **attempt-scoped atomic publish**：attempt id ＋專屬 temp namespace ＋**prompt 與 wrapper 必須同時改**＋啟動前 stale `<out>` 檢查＋terminal marker 綁 attempt id；並發情境改為「兩者皆須保留可追溯」，不再以「後者覆蓋前者」為通過條件 |
| D-3 | `CODEX-R1-P0-05` | Phase 0 的「行為逐位元組不變」收窄為**判定行為不變**＝`(rc, kind)` 序列逐項相等；audit 加欄位明文排除在該不變式外。`match_rule` 封閉 enum ＋事件契約寫入 `scripts/audit_events.json`，SPEC 只 pointer |
| D-4 | `CODEX-R1-P0-04`／`COMPOSER-R1-P1-01` | Task 2.5 加 **immutable corpus**（語料檔進版控＋sha256 綁報表標頭）＋**舊版 gate snapshot 以固定 sha 存放**；驗收由「每一項都須被預期」改為「**列舉項為必要子集 ＋ 附加項逐項人工標註，存在非預期即 FAIL**」 |
| D-5 | `CODEX-R1-P1-09` | Phase 1 unknown `brief-kind` 統一為 **fail-closed 拒派**，刪除互斥的第二種行為 |
| D-6 | `CODEX-R1-P0-01` vs `COMPOSER-R1-P1-02/P1-04` | **裁 SPLIT**：刪除原 Phase 4。`B-24` 紀律面留本批（§V，零新增元件）；機械強制面移出獨立排期，grandfather 三要件（owner／UTC 到期／到期後 fail-closed）記入 backlog 拆分裁決節 |
| D-7 | `CODEX-R1-P0-07`／composer Q1 | 區間定為 **CLI process-group launch → return/kill**；值取兩家保守聯集（codex 50m／grok 70m／composer 75m／外層 90m），**標明為暫定，須以 Task 3.1 真實 duration 重算後才可填入 TODO** |
| D-8 | `COMPOSER-R1-P1-03`／`CODEX-R1-P0-07` | 已開 **`票 B-33 GOV-LOCALE-GUARD-DRIFT`**（MAJOR，排第 1 批之後），本批不併入，寫入 TODO §0 已知債 |
| D-9 | `CODEX-R1-P1-08`／`COMPOSER-R1-P2-03` | OPEN-3 補**補查條件**：Phase 0 後累積 ≥200 筆 `gate_deny` 或 ≥30 日（先到為準）以 `match_rule` 反查；零命中才除役且須記「觀測期無再現」 |
| D-11 | `COMPOSER-R1-P2-02` | Task 1.1 加**誠實邊界**：只保證 harness 端不再誘導，**不保證委員行為**；驗收禁以「委員這次沒寫」為斷言 |
| D-12 | `COMPOSER-R1-P2-01` | Task 0.1 「不可做」明文寫入：**`grep -Eo` 不得進判定前主路徑** |
| D-13 | `CODEX-R1-P1-06`／composer Q6 | §P 開頭新增**完整依賴圖**，含 R1 未宣告的 registry enum／舊版 snapshot／immutable corpus／`.part` prompt identity |

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: R2 SPEC 為 4 Phase／10 Task（原 5 Phase／11 Task，Phase 4 已移出），`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` rc=0
→ 主委實跑 2026-08-04。

fact-verified: `D-1` 的修法已有可用原型並經主委實跑——`.claude/tmp/b15probe3.sh` 對 9 條語料：
原型①（單純剝引號）在 `bash -c "codex exec x"`／`sh -c 'grok … -p x'` 兩條 **ALLOW（fail-open）**；
原型②（剝引號＋對 `(bash|sh|zsh) -c` 引數遞迴）**9/9 全對**
→ 主委實跑 2026-08-04。

fact-verified: `D-7` 的數據經主委獨立重算（`.claude/tmp/runlog_dur.sh`，n=462）：
codex max 45.1m／composer max 146.7m／grok max 64.6m；暫定值下三家誤殺各 `0/166`、`0/143`、`0/152`
→ 主委實跑 2026-08-04，未採信委員報告數字。

assumed: 13 項裁決**全部已在 R2 落實，且沒有引入新的矛盾**。← 請直接攻這條。

assumed: `D-6` 的 SPLIT 裁決（刪 Phase 4）沒有讓 `B-24` 的任何要求掉項。← 請攻。
特別是：紀律面留在 §V 而無檢查器，**是否等於回到你們 R1 判定「不滿足工具強制條款」的原點**？
主委的理由是「本批只承諾紀律，機械強制另批交付，且 grandfather 三要件已具名記錄不遺失」——請攻此推理。

assumed: Task 2.0 的詞法契約 5 項**涵蓋了所有會影響判定的詞法情境**。← 請攻，補出遺漏項。

## 必答（逐條 verdict；每條須附實跑 receipt 或明確碼證）

### Q1 — **你自己 R1 的每一條 P0／P1，逐條判定是否真關閉**

依章程 §B8：**由原提出方重跑同一反例確認**，不憑「已修」信任。
逐條輸出：finding ID ／ CLOSED 或 NOT-CLOSED ／ 重跑的反例與結果。
🔴 **NOT-CLOSED 者須指出 R2 的哪一句仍不足**，不接受「感覺還不夠」。

### Q2 — R2 是否引入**新的**矛盾或漏洞

特別檢查：
1. Task 2.0 契約與 Task 2.1–2.4 的實作要求是否一致（有無某 Task 的驗收與契約衝突）？
2. Task 3.2 的 attempt-scoped publish 是否與 Task 3.3 的逾時判定衝突（例如 publish 進行中逾時）？
3. Phase 0 的「判定行為不變」與 Task 2.x 的「判定必須改變」是否在同一測試語料上互斥？

### Q3 — `D-6` SPLIT 是否可接受

若你判定不可接受，請給出**可執行的替代方案**與其成本估計，而非只說「不夠」。

### Q4 — Task 3.3 的值定稿條件是否可執行

「TODO 中的 timeout 值與 Task 3.1 產出的 duration manifest 一致」——
Task 3.1 要跑多少次真實派工才夠？本 SPEC 沒說。請給可執行的樣本門檻。

### Q5 — §V 的 `票 B-24` 紀律面是否真的落實

逐 Task 檢查「驗證」欄：是否**每一條**都斷言執行後狀態，而非腳本 rc？列出任何仍是 rc 斷言者。

### Q6 — 可以進 TODO 生成嗎？

若仍為「需修補」，請**明列 BLOCKING 清單**（編號 ＋ 具體修法方向），不要只給結論。

## 產出

canonical 四欄 findings（ROUND=**R2**）+ **Verdict**。**禁改碼**。
**勿寫 `## RECONCILE-STAMP` 標題**。收尾清 /tmp workdir（保留 claude-501）。
