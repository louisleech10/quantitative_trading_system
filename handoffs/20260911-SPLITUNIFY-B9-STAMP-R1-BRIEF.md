# SPLITUNIFY b9 — D-002 v13 補戳記 ＋ TODO §C-9 新增段審查

brief-kind: closure
task-id: 20260911-SPLITUNIFY-B9-STAMP-R1
findings-round: STAMP

🔴 **這是戳記輪：只讀、只核可或只拒簽。禁改碼、禁動 tracked 檔（戳記 append 除外）、禁在本 repo commit／push、禁跑 `tests/governance` 全套。**
（`brief-kind` 用 `closure` 而非 `stamp`：`brief_conformance_check.sh:425` 要求 `stamp-target` 須 `handoffs/` 前綴，
而本輪標的是 `docs/` 下的 SPEC；同情境之既有作法見 `handoffs/20260912-SPLITUNIFY-D001-STAMP-BRIEF.md`。）

## 任務

兩件事，**都要做**：

### (A) 對 `docs/SPLITUNIFY_SPEC.D-002.md` 補 `RECONCILE-STAMP`
- **stamp-target**：`docs/SPLITUNIFY_SPEC.D-002.md`
- **body sha256**（實跑 `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` 取得）：
  `06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77`
- 審完後 append 到該檔 `## 戳記` 區，逐字格式：
  `RECONCILE-STAMP: <family> APPROVED 2026-09-13 sha256:06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77 task:20260911-SPLITUNIFY-B9-STAMP-R1`
  （判 REJECTED 者把 `APPROVED` 換成 `REJECTED` 並在同行尾以 `—` 接原因。）
- 🔴 **本檔十三輪從未有任何委員戳記**，這是補簽，不是重審規格內容。R12 停輪判準已於
  `handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md` 觸發並經三家確認；**不要重開規格審查**。

### (B) 審查 `docs/SPLITUNIFY_TODO.md` 之**新增段** `§C-9`（Task 9.1–9.5）
- 該段由主委（claude）本輪撰寫、**未經任何委員審過**；實作者不自審，故請你審。
- 標的範圍：`§B` 批次表之 `B9A`–`B9F` 六列 ＋ `§C-9` 全節。**其餘 TODO 內容不在範圍**。

---

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **current block**：
  - `docs/SPLITUNIFY_SPEC.D-002.md`：只讀 §P（`sed -n '172,253p'`）、§V（`sed -n '254,312p'`）、§N（`sed -n '317,326p'`）
  - `docs/SPLITUNIFY_TODO.md`：`§B` 批次表（`sed -n '55,80p'`）＋ `§C-9`（`grep -n '^## §C-9' -A250 docs/SPLITUNIFY_TODO.md`）
- **本輪 diff**：`git diff -- docs/SPLITUNIFY_TODO.md CLAUDE.md docs/MULTI_AGENT_ORCHESTRATION.md`
- 🔴 **不在審查範圍**：`docs/SPLITUNIFY_SPEC.D-002.md` 之 `HISTORY-BEGIN`～`HISTORY-END` 與
  「## 沿革與追溯索引」節，以及逐字標記「作廢／前版／舊敘述／原寫」之字面。
  **finding 之 source anchor 落在歷史段者不受理**（`completeness --single` fail-closed 拒收整份交件）。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: `docs/SPLITUNIFY_SPEC.D-002.md` 目前零戳記 → `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` 三家皆列「缺 APPROVED 戳記」。派工後預期值: 三家 append 後同一命令 rc=0。
fact-verified: b9-consult-r2 三家裁定已執行 → `git status --porcelain` 對 `momentum/Analysis/event_samples/split_projection.py`／`pipeline.py`／兩測試檔／`handoffs/20260911-splitunify-b9-probe-multitf.py` 皆**無**條目（已 REVERT 至 HEAD）；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` 實跑 **87 passed、0 failed**。
fact-verified: `§C-9` 之驗收命令**逐檔明列路徑、無聚合期望數** → 主委已逐條自查；`grep -c 'failed <=' docs/SPLITUNIFY_TODO.md` 對 §C-9 為 0。
fact-verified: `docs/SPLITUNIFY_TODO.md` 兩道產出端閘皆過 → `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_TODO.md` rc=0；`bash scripts/spec_xref_check.sh --synth handoffs/reconcile/20260911-splitunify-b9-consult-r2/synth.md docs/SPLITUNIFY_TODO.md` rc=0（18 個概念皆同步）。

assumed: `§C-9` 的六批切法（`B9A`–`B9F`）粒度**恰當**。**我的否證觀測（已先跑）**：SPEC §P 只給 Phase 9A／9B 兩層、**沒有**批次粒度指示（`grep -n "Batch\|批" docs/SPLITUNIFY_SPEC.D-002.md` 在 §P 內零命中）⇒ 六批是我自產。**我沒查**：六批各需一輪三家 review ＝ 六輪成本，是否該合併（例如 `B9D`＋`B9E` 併一批，因兩者可並行且互不依賴）。← **請直接攻這條**，給出你認為的批數與理由。

assumed: `Task 9.2a` 把 `test_multi_feature_tf_opposite_sides_must_fail_closed` 標 `xfail(strict=True)`、留到 `Task 9.2b` 才解除，是**正確**的處置。**我的否證觀測（已先跑）**：consult-r2 三家裁定該測試是「fixture 錯＋行為未實作」三重問題，其中 fixture 屬 9.2a、行為屬 9.2b ⇒ 跨兩個 Task。**我沒查**：`strict=True` 的 xfail 在 `Task 9.2a` 修完 fixture 後會不會**提前變成 XPASS 而紅**（若 fixture 修正後該測試因別的原因意外通過）。← **請直接攻這條**。

## 攻擊面（兩欄；我沒查的請你查）
| 面向 | 已排除（附查法） | 我沒查 |
|---|---|---|
| `§C-9` 驗收命令是否會誤跑全套 | 逐檔明列路徑，無裸 `pytest -k`（主委已具名駁回 grok consult-r2 原文之無路徑版本，理由寫在 consult-r2 synth） | 每條命令的**測試檔路徑是否真的存在**——請逐條 `ls` 驗；我只驗了 `test_pattern_bridge.py`／`test_metrics_glossary.py`／`test_baseline_oracle.py` 三個 |
| `§C-9` 具名測試函式名是否與 §V 之 ASSERT 一一對應 | — | **逐條比對**：§V 的每條 ASSERT 是否都能在 §C-9 找到承接的測試函式名；反向亦然（§C-9 有而 §V 無者是我自創，須具名） |
| mutation 覆蓋 | `M-SU-D2-01`..`34` 共 34 條，§C-9 逐 Task 列出所屬 | **是否有 mutation 落單**（34 條中哪幾條在 §C-9 完全沒被任何 Task 認領）——請機械計數 |
| `Task 9.4` 之修改檔具名 | 已具名到 `types.ts:1582`／`:2257`、`EventTablesPanel.tsx:361` 與六支既有前端測試；API 端 `grep -rn "n_train" api/ --include='*.py'` 對事件批 summary 零命中 | 那六支前端測試的**行號**是否仍正確（我用 grep 取得，可能已漂） |
| 依賴序 | 三家 consult-r2 ＋ 主委獨立版四方一致 | 我把 `9.3` 的「動工前重掃 register」寫成前置條款，但**沒定義重掃的產出物該放哪**——請指出 |
| CLAUDE.md／ORCH 之「雙家族」字面更正 | 本輪已改為指向 §1 現行分工行（三處：`CLAUDE.md:30`、ORCH `:41`、ORCH `:195`） | 是否還有第四處漏改——請 `grep -rn "雙家族\|兩家\|2 個正式" CLAUDE.md docs/ AGENTS.md .cursorrules` 自證完備 |

## 必答（逐條 verdict；成對，不得只答一半）

1. **(1a)** 對 `docs/SPLITUNIFY_SPEC.D-002.md`（body sha256 `06b2d4cb…`）：`APPROVED` 還是 `REJECTED`？
   **(1b)** 若 `APPROVED`，指出 v13 裡**最可能在 `Task 9.1` 實作當下就變紅**的那一條條文（具名到節與句），以及變紅時該改碼還是改規格。若 `REJECTED`，逐條列阻擋項且每條須能在**一次修訂**內關閉。
2. **(2a)** `§C-9` 的六批切法（`B9A`–`B9F`）：接受、還是該合併／再拆？給出你的批數與**理由**（不是偏好）。
   **(2b)** 你的批數若是錯的，主委會在第幾批、以什麼形式發現？給可執行觀測。
3. **(3a)** §V 的每條 ASSERT 是否都在 `§C-9` 有承接的具名測試函式？逐條比對後列出**落單的 ASSERT**（§V 有、§C-9 無）。
   **(3b)** 反向：`§C-9` 有而 §V 無的測試函式名（主委自創面），逐條列出並判「該補進 §V」或「屬施工細節、留 TODO 即可」。
4. **(4a)** 34 條 mutation 中有哪幾條在 `§C-9` **完全沒被任何 Task 認領**？請機械計數（貼命令與輸出）。
   **(4b)** 落單者該掛哪個 Task？若你認為某條本來就不該在 Phase 9 認領，說明它該在哪裡閉合。
5. **(5a)** `Task 9.2a` 之 `xfail(strict=True)` 處置：接受還是有更好的作法？
   **(5b)** 若接受，說明 `Task 9.2a` 完成後該測試**不會**意外 XPASS 的理由（給碼證）；若不接受，給替代作法。
6. **(6a)** 可以進 `Task 9.1` 實作嗎，還是有 BLOCKING 必須先修？
   **(6b)** 若無 BLOCKING，說明你**檢查了什麼**才敢說無（不接受「逐項核對後無問題」這種無標的說法）。

## 🔴 本輪格式硬約束（DOCROT／CXSTAMP 2026-09-13 上線；違反會被機械閘退件）
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**（缺則 `completeness_check.sh --single` fail-closed 拒收整份交件）：
   - `CODE-ANCHOR: <path>:<line>`（或 `<path>:<A>-<B>`）
   - `MUTATION: <可執行的破壞>`
2. **anchor 不得落在 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**——落在歷史區＝整份被拒。
3. **欄位內容必須與標籤同一行**（逐行判）。`**碼證**:` 後面接換行再條列＝空殼，會被退件
   （codex 於 CXSTAMP 已連續踩兩次；本條就是為此補的）。
4. **零 findings 時**須用 `templates/COMMITTEE_FINDING_TEMPLATE.md` 的零 findings sentinel 形態，
   且 sentinel 內同樣要有**斷言**與**碼證**，不得只寫散文。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` 空值或 finding ID 清單。
6. 戳記 append 到 stamp-target 的 `## 戳記` 區，**不算**交件檔的 heading（交件檔仍須自帶至少一個 canonical heading）。

## 🔴 本輪不得以之為 REJECT 理由（consult-r2 已裁）
- §V 之 `V8_BASELINE_SHA256=` 64-hex 錨點**尚未寫入**：SPEC 自標「凍結當下才生效」，屬 `Task 9.5` 施工面，
  **不是**本輪可一次修訂關閉的 SPEC body 缺陷。（composer 在 consult-r2 曾以此列為阻擋條，經收斂改為「維持 defer
  但 stamp brief 須明示」——本段即該明示。）
- `docs/SPLITUNIFY_TODO.md` 缺 `Task 9.1`–`9.5`：**本輪已補**（見任務 (B)），該阻擋條已消失。

## 產出
- 交件檔：canonical 四欄 findings（或零 findings sentinel）+ `VERDICT`。**禁改碼、禁改 SPEC、禁改 TODO**。
- 戳記：append 到 `docs/SPLITUNIFY_SPEC.D-002.md` 之 `## 戳記` 區。
- 收尾清 /tmp workdir（保留 claude-501）。
