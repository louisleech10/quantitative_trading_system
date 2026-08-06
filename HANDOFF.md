# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-06 | **Branch**: main（`af12438`，本地＝遠端）
**狀態**: ✅ 38 張票裁定定版（三家戳記 `df82cd54`）→ 下一步＝**`票 B-39`**

## ▶ 接手第一件事：`票 B-39`（id-like heading 誤判）

**它排第一是委員兩家一致的裁定**——擋著所有委員輪，本日已作廢 4 輪。

- 票：`handoffs/20260801-GOV-AMEND-BACKLOG.md` 的 `## B-39`
- SPEC 草案：`docs/GOVB39_IDLIKE_HEADING_SPEC.md`（三支檢查器 rc=0，**未經審查**）
- 根因：`completeness_check.sh:60` `HEADING_LINE_RE='#{2,6}'` 把 id-like 子標題送進 finding 通道；
  同檔 `:913` body-hash 用 `##(?!#)` ⇒ **同檔兩處定義不一致**
- 🔴 **不得寫成「禁 `###`」**（主委犯過；那是把摩擦轉嫁給每位委員卻不修根因）

## 執行順序（三家戳記定版）

```
1. 票 B-39  id-like heading 誤判      ← 現在這裡
2. 阻塞鏈   B-38 / B-15 / B-19 / B-31   （B-32 已 DONE，勿沿用）
3. 群集 ID 登記（併 B-26）＋ 探針 owner（併 B-13/B-36）
4. B3R      詞法層重寫（規格 → 原型 → 差分 → 落地）
5. B4 → B5 → B6 → B7
```

**B3 不再獨立驗收，由 B3R 吸收**（codex 裁定）。

## 🔴 工作區有未 commit 的 B3 修補（**不要 commit**）

**已追蹤（10 個 `M`）**：

```
scripts/_gate_lex.sh
scripts/extract_phase2_expected_flips.py
scripts/gate_check.sh
tests/governance/fixtures/gate_decision_corpus.txt
tests/governance/fixtures/gate_decision_corpus.txt.sha256
tests/governance/fixtures/phase2_expected_flips.txt
tests/governance/fixtures/phase2_expected_flips.txt.sha256
tests/governance/test_gate_decision.py
tests/governance/test_gate_deny_fields.py
tests/governance/test_gate_lexical_contract.py
```

**未追蹤（1 個 `??`）**：`docs/GOVB0_FRICTION_AMENDMENTS.md`（C5 決策的延伸檔）

保留至 B3R。**風險未經證明**：仍帶 E-1 換行繞道與 E-2 大輸入 O(n²)（500K→30s）。
⚠️ **不得宣稱現況安全**——「10K→0.09s 故非即時風險」已被 codex 推翻並撤回。

🔴 **接手時的第一個動作**：`git status --short` 應**恰好**是上述 9 `M` + 1 `??`
（外加 `.claude/gate/*.log` 的正常追加）。**多出任何檔案代表有人動過，先查清再繼續。**

## 使用者 2026-08-06 定的判準（治理 epic 全域適用）

```
淨摩擦 = 新增的每次成本 × 發生次數 − 省下的重工成本 × 避免的次數
```

- **不只用來選票，也是「每張票怎麼修」的約束**（否則發散）
- **可讀性不是驗收標準**；**溯及既往預設關閉**
- **優先找通則，別為每種失誤各開一張票**（`B-40` 即因此當天收掉）
- 使用者授權：**有信心自己做完的就自己做完，不需互相詰問的不必 call 委員**

## 本日新增／修正的機制

| 檔 | 做什麼 |
|---|---|
| `session_name_check.sh` | session／task-id 命名規約；接進 `committee_run.sh`（**檔案不存在則跳過**，理由見檔內） |
| `test_session_name_guard_wired.py` | 擋「刪檔即失效」；斷言存在＋可執行＋確實被呼叫 |
| `reconcile_cluster_attribution_check.sh` | 群集引用 ID 對回附錄斷言；接進 `reconcile_build.sh`（只印不擋） |
| `reconcile_stamps_check.sh` | **每家族取最後一筆戳記**（最新蓋掉舊的）＋ 同行混用狀態詞 fail-closed |
| `status_marker_check.sh` | 任務 ID 須 `b`+8 位英數**且檔案真存在** |
| `plain_docs_sync_check.sh` | 日誌納管＋進度單一出處守衛 |

⚠️ **說明檔的更新必須是最後一個 commit**——先提交說明檔再改腳本會被時序判準判過期。

## 本日主委錯誤（同型 9 次，供下個 session 警惕）

**「驗了 A 就當作 B 也成立」**：封存只驗 1/20 消費者／看 C5 當 C4／小輸入宣稱整體安全／
關鍵字計數當事故證據／一個案例失敗當全體失敗／codex 說關就當兩家都說關／
照工具訊息字面轉述未複驗。**其中 6 次由委員抓到。**

⇒ 對策已落地：`reconcile_cluster_attribution_check.sh` 首次使用即抓到 2 條掉項。

## ▶ 派工前的固定前置（本日踩過才寫下）

```
1. bash scripts/debt_ledger.sh --has-open        # 單獨跑並讀輸出，勿塞進背景指令
2. bash scripts/session_name_check.sh --session <名> --task-id <大寫同名>
3. bash scripts/doc_format_precheck.sh <brief>
4. python3 scripts/verification_claim_check.py --files <brief>
5. 上游收斂檔須已三家 APPROVED（否則委員依 Rule 12 拒絕作業）
```

**第 5 條本日被 codex 擋過一次**：拿未核可的收斂檔當下一輪的開票依據。

## 收斂檔的固定收尾

```
1. bash scripts/reconcile_cluster_attribution_check.sh <synth.md>   # 掉項/錯位自檢
2. bash scripts/completeness_check.sh --lock <sources.lock>
3. python3 scripts/verification_claim_check.py --files <synth.md>
4. bash scripts/reconcile_body_hash.sh <synth.md>                   # 供戳記 brief
5. 戳記過後：bash scripts/gate.sh register-output <task-id> <synth.md>
```

**第 1 條是本日新增**，首次使用即抓到 2 條掉項；**第 5 條本日漏做過一次**（provenance pending）。

## 坑（沿用）

`rc` 禁經 pipe｜禁 `cd <專案路徑>` 前綴｜中文路徑 `git -c core.quotepath=false`｜
`rm` 在 deny 用 `git rm`｜commit 訊息用 `-F 檔案`｜brief 兩支檢查器一次驗｜
**前置檢查要單獨跑並讀到輸出**（塞進背景指令會看不到結果，本日踩過）
