# SPLITUNIFY b9 — 對 stamp-r2 收斂檔補三家戳記（進 Task 9.1 之授權依據）

brief-kind: stamp

stamp-target: handoffs/reconcile/20260911-splitunify-b9-stamp-r2/synth.md

## 任務

**只做一件事**：審閱 `handoffs/reconcile/20260911-splitunify-b9-stamp-r2/synth.md`，判 APPROVED 或 REJECTED，並 append 戳記。

- **body sha256**（實跑 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-stamp-r2/synth.md`）：
  `3f3d0d7936256c9b71ebce51cf286310c55fb432a760eb68bcb60602e0f3dacb`
- 逐字格式：
  `RECONCILE-STAMP: <family> APPROVED 2026-09-13 sha256:3f3d0d7936256c9b71ebce51cf286310c55fb432a760eb68bcb60602e0f3dacb task:20260911-SPLITUNIFY-B9-STAMP-R3`

## 🔴 本輪為何存在（這不是又一輪規格審查）

`gate.sh dispatch --risk high` 在發 **impl token** 前，機器強制要求 `--adversarial` 指向一份**已獲全數委員戳記**的 reconcile（制度出處：「reconcile／最終章程須委員 append RECONCILE-STAMP；gate 機器強制，無戳記拒發實作 token」）。
b9 的 `Task 9.1` 實作授權依據就是 stamp-r2 這份收斂檔，但它原本沒有 `## 戳記` 區 ⇒ 主委已補上該區段（**只 append 區段標題與說明，正文一字未動**），現在請三家補簽。

## 🔴 不在本輪範圍（請勿重開）
- `docs/SPLITUNIFY_SPEC.D-002.md` 正文與其戳記——該檔已於 stamp-r2 取得三家 APPROVED、`reconcile_stamps_check` **rc=0**（body `d42b3f14…`），本輪不動。
- r17 之共識決方向（`PROCEED`）、`C5-01`..`C5-29` 之 mutation 欄對應、mutation 條數（40）與 ID 連續性。
- `docs/SPLITUNIFY_TODO.md` 之 `Task 9.1`–`9.5` 內容——已歷 r13／r14／r15／r16／r17／stamp-r2 六輪審查。

## 審查標的（🔴 輸入邊界）
- **current block**：`handoffs/reconcile/20260911-splitunify-b9-stamp-r2/synth.md` **全檔**（該檔僅 41 行，含一條 finding 與裁定段）。
- **本輪 diff**：`git show 3e8eff32 -- docs/SPLITUNIFY_TODO.md`（該收斂檔之處置所對應的實際落地）
- 🔴 **anchor 不得落在** `docs/SPLITUNIFY_SPEC.D-002.md` 之 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: SPEC 已取得三家有效戳記 → `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` **rc=0**，三家全數 APPROVED 且雜湊相符。派工後預期值: 不變（本輪不動該檔）。
fact-verified: 收斂檔之處置已實際落地 → `docs/SPLITUNIFY_TODO.md` 之 `SU-RESID-C5-TARGETS` 段已由「20 列」改為 19；(乙) 段已逐字具名 `C5-15`／`C5-16`／`C5-17`／`C5-18`。
fact-verified: (乙) 四列之分類屬實 → 主委對四列各跑「有檔名？有行號？」兩道 `grep -c`，四列皆得「檔名=1 行號=0」。
fact-verified: 主委補 `## 戳記` 區時正文未動 → 該區段為檔尾 append，body sha256 涵蓋其前全部內容，值為 `3f3d0d7936256c9b71ebce51cf286310c55fb432a760eb68bcb60602e0f3dacb`。

assumed: 這份收斂檔**足以**作為 `Task 9.1` 實作之授權依據。**我的否證觀測（已先跑）**：它記錄了 codex 兩條 blocker 之閉合與三家戳記達成 rc=0，即「進實作」之最後一道前置。**我沒查**：`gate.sh` 對 `--adversarial` 標的除「有戳記 ＋ 有 Verdict」外是否還要求內容涵蓋本次實作範圍（本檔只有一條 P2 finding，內容與 `Task 9.1` 之施工面無直接關係）。← **請直接攻這條**：若你認為授權依據應改指 r17 收斂檔（內容才是共識決本體），請直說。

## 必答（逐條 verdict；成對，不得只答一半）

1. **(1a)** 對 body `3f3d0d79…`：`APPROVED` 還是 `REJECTED`？
   **(1b)** 若 `REJECTED`，逐條列阻擋項且每條須能在**一次修訂**內關閉。
2. **(2a)** 這份收斂檔作為 `Task 9.1` 之 impl 授權依據**適切**嗎？（見上 assumed）
   **(2b)** 若不適切，指出應改指哪一份、理由為何。
3. **(3a)** `Task 9.1` 之施工面（`build_event_keys` 回傳 tuple、`_derive_single_symbol` 原樣寫入 summary、`pipeline` caller 同批改）在現行 TODO 條文下是否**可直接開工**，還是仍有未解歧義？
   **(3b)** 若有歧義，逐條列出並給可直接貼進 TODO 的字面。

## 🔴 本輪格式硬約束
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**：`CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行的破壞>`。
2. **欄位內容必須與標籤同一行**（逐行判）。
3. **零 findings 時**須用 `templates/COMMITTEE_FINDING_TEMPLATE.md` 之零 findings sentinel 形態，且含**斷言**與**碼證**。
4. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` **空值或 finding ID 清單**，🔴 **不得填日期**，🔴 **只准填本家自己提出過的 ID**。
5. 戳記 append 到 stamp-target 之 `## 戳記` 區，**不算**交件檔的 heading——交件檔仍須自帶至少一個 canonical heading。

## 產出
canonical 四欄 findings（或零 findings sentinel）+ **Verdict** ＋ 戳記。
**禁改碼、禁改 SPEC、禁改 TODO、禁改收斂檔正文**（戳記 append 除外）。收尾清 /tmp workdir（保留 claude-501）。
