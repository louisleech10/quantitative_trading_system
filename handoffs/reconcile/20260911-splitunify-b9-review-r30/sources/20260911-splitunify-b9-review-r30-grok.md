# SPLITUNIFY b9 — review-r30（O1–O5 閉合再驗證 ＋ v24 重簽）— grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R30`  
**family**: grok  
**findings-round**: R30  
**brief-kind**: review  
**審查標的**: commit `fa0ca3f4`；current block＝O1–O5＋`SU-RESID-V8-ATTEST`（`handoffs/reconcile/20260911-splitunify-b9-review-r29/synth.md`）  
**禁改碼／禁改 SPEC 正文／禁改 TODO**（戳記 append 除外）。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 六路 736 passed | **fact-verified（子集）** | 本輪 `derive`＋`golden`＋`wiring` → **144 passed**；全六路未重跑（brief VERIFY-EXEMPT） |
| brief fact-verified: doc_format 兩份 rc=0 | **fact-verified** | SPEC／TODO 各跑一次 → 皆 rc=0 |
| brief fact-verified: 主委四探針 | **fact-verified（本家重跑）** | 見必答 1b；輸出特徵與 brief 相符 |
| brief fact-verified: r29 `state=CLOSED` | **fact-verified** | `debt_ledger.sh --list \| grep review-r29` → `state=CLOSED`（session `20260911-splitunify-b9-review-r29`） |
| brief fact-verified: body `bc4a2b3e…` | **fact-verified** | `reconcile_body_hash.sh` → 逐字相符；append 戳記後 hash **不變** |
| brief assumed 1: `SU-RESID-V8-ATTEST` 歸類正確 | 見必答 3① | |
| brief assumed 2: O1 digest 已擋「習慣性全列」 | 見必答 3② | |
| brief assumed 3: O3 不可變字面已除共因 | 見必答 3③ | |
| brief assumed 4: O5 已窮盡同型 | 見必答 3④／必答 4 | |

---

## 必答 1 — 重跑本家 review-r29 反例（§B8）

### (1a)

本家 review-r29 為**零 finding**（`GROK-R29-P3-00` sentinel），**無**可重跑之 P0／P1／P2 反例 ID。

| 項目 | 判定 |
|------|------|
| 本家 r29 finding 反例 | **N/A（零 finding）** |
| brief 要求之四探針（O1–O4 閉合驗證）＋ O5 fixture | **CLOSED**（見 1b） |

### (1b)

```text
# 探針① O1：只給鍵名 → 拒（格式不合）
./venv/bin/python scripts/freeze_splitunify_golden.py --write --accept-value-changes g4_per_symbol_n
# → rc=1
# GOLDEN REFUSE: --accept-value-changes 之項目 'g4_per_symbol_n' 格式不合
# ——須為 `<key>=<old8>:<new8>`（只列鍵名不算授權；fail-closed）

# 探針② O2：僅 HISTORY 有錨 → §V 讀取為 None
# （臨時 SPEC：剝 §V 錨、於 HISTORY-BEGIN 後塞假 64-hex；呼叫 _read_v8_anchor_from_spec）
# → O2_history_only_anchor_is_None True

# 探針③ O3：BASE += 17 ms
# → O3_normal_equal True；O3_BASE_plus17_mismatch_count 13
# → O3_hand_unchanged True；O3_actual_moved True
# 例：bnd_shift hand=1700000000000 actual=1700000000017

# 探針④ O4：兩檔已存在時 --init-v8
./venv/bin/python scripts/freeze_splitunify_golden.py --init-v8
# → rc=1
# GOLDEN V8 REFUSE: --init-v8 只用於首次建立，兩檔任一已存在即拒（write-once）
# 另：temp 刪兩檔後 create_v8_baseline_write_once rc=0，隨後 _assert_v8_baseline_intact rc=1（與 SPEC 錨不符）
# 半套（僅 sidecar 存在）create 亦 rc=1

# O5 fixture
# → O5_equal_count 12；O5_non_equal ['bnd_shift']
```

---

## 必答 2 — v24 body 重簽

### (2a)

**APPROVED**（body `bc4a2b3ea78fbb09a7989cbb4b36ce6e421ec9abe155d086ece8d21461b4457c`）。

戳記已 append（舊行保留）：
`RECONCILE-STAMP: grok APPROVED 2026-09-14 sha256:bc4a2b3ea78fbb09a7989cbb4b36ce6e421ec9abe155d086ece8d21461b4457c task:20260911-SPLITUNIFY-B9-REVIEW-R30`

### (2b)

N/A（未 REJECTED）。

---

## 必答 3 — 四條 assumed

### (3a)

① **`SU-RESID-V8-ATTEST` 歸類與邊界正確** → **成立**。

- 已關半：HISTORY-only 錨 → `None`（探針②）；既有檔 `--init-v8` 拒；半套拒；三層 intact 在 delete＋reinit 後對 SPEC 錨轉紅。
- 未關半：同 commit 同步替換 §V 錨＋v8＋旁檔＋helper，**任何倉內機制**都擋不住——這與殘留原文一致。
- **攻「是否掩護了不擴建工具即可做的一層」**：
  - `handoffs/run_receipts/` 留痕：攻擊者可在**同一 commit** 一併改 receipt，等價於再加一個可同步替換的檔，**不增加**同 commit 防護。
  - 倉外絕對路徑錨（本機檔）：不進 PR diff、不可審、機器綁定，比 git 歷史更弱。
  - `git show <prior>:` 祖先比對：沒有受保護 ref／簽章時，force／同批改 tag 仍繞得過；有保護則已落入殘留觸發條件（`commit.gpgsign`／branch protection）。
- 結論：歸類為 `user-ruling` 殘留**不是掩護**；誠實邊界（信任根＝code review＋git 歷史）成立。不升級 finding。

② **O1 digest 授權已擋住「習慣性全列上去」** → **成立**；**貼回錯誤訊息建議字串 ≠ 回到「只列鍵名」**。

- 只列鍵名：live rc=1，訊息指名格式不合（探針①）。
- **貼回 hint**：錯誤訊息印出的 `_hint` 綁的是**那一次**觀測到的 `old8:new8`。貼回＝在已看到實際新舊值之後，對**該次具體變更**做明示授權——這是 digest 閘的正當 UX，不是「未看值就授權任意新值」。
- 反證「等價於無閘」：同一 `old8` 配上**不同** new 值之 digest → 與授權不符會拒（本家以 `ETHUSDT:999` vs `888` 之 digest 不等驗證 `O1_pasteback_wrong_new_digest_mismatch True`）；列了未變鍵仍走 `_stale_allow` 拒。
- 誠實邊界：`--help` 仍寫 r28「逗號分隔之既有頂層鍵清單」（未提 digest）。讀 help 會寫錯格式，但閘本體 fail-closed，**無靜默放行**。屬 helper 說明落後，**非** SPEC／TODO 互斥；不升級 finding、不擋 B9D。

③ **O3 不可變字面已消除共因** → **成立（對 r29 攻擊向量）**。

- `_hand_decision` 區塊無 `BASE`／`H1` 引用；13 筆皆 `int` 字面（探針③前置）。
- `BASE += 17` → mismatch **13**／13；人手表不變、實際值移動（探針③）。
- **攻「字面當初用同一組常數算出再貼」**：那是**撰寫當下**的作者知識來源，與「執行期兩邊仍讀同一可變常數」不同類。任何人手 oracle 都曾被人腦對過 fixture；O3 要關的是**執行期共因位移仍綠**——已關。
- 可選第三形狀（非本輪必做）：人手時刻改從**更早已提交**之快照欄位抄入（與本次改 `BASE` 的同一 diff 脫鉤）。現行已足以擋 BASE 平移；不升級 finding。

④ **O5 修補已窮盡該類（審查範圍內）** → **成立**。見必答 4：自立詞表下 SPEC／TODO **live 互斥＝0**（第十處未發作）。

### (3b)

①②③④ 皆無須先修之阻擋修法。可選清理（非 BLOCKING）：更新 `--accept-value-changes` 之 argparse help 為 `<key>=<old8>:<new8>` 字面；`freeze_splitunify_golden.py:610` 註仍寫「人手常數由 BASE／H1 手算」可改為指向不可變字面——皆 helper 說明，閘已正確。

---

## 必答 4 — 契約面強制掃描（同型第十次？）

### (4a)

**本家詞表**（🔴 刻意不用主委／他家可見之主幹 token 組合；本輪自建三組）：

| 類 | 詞／結構 |
|----|----------|
| 空心／xfail 過期 | `空心通過`／`全部事件皆`／`decision == cutoff`／`1 xfailed`／`xfailed.*passed` |
| 層數／digest 舊形 | `三層`／`metadata\.split_unify`／`producer→summary→metadata`／`整鏈`／`只驗鍵名`／`任意新值`／`BASE \+ n`／`不可變字面` |
| 舊判側／OOB | `寫成第四條`／`不在 feature_index`／`⇒ purged`／`per-cutoff`／`集合成員給 purged`／`舊路徑判` |

**命令**（SPEC live＝`:1` 至 `HISTORY-BEGIN`＝`:346` 之前；TODO 全檔）：

```bash
HB=$(awk '/HISTORY-BEGIN/{print NR; exit}' docs/SPLITUNIFY_SPEC.D-002.md)
VOCAB1='空心通過|全部事件皆|decision == cutoff|1 xfailed|xfailed.*passed|三層|metadata\.split_unify|producer→summary→metadata|整鏈'
VOCAB2='BASE \+ n|只驗鍵名|任意新值|不可變字面'
VOCAB3='寫成第四條|不在 feature_index|⇒ purged|per-cutoff|集合成員給 purged|舊路徑判'
awk -v hb="$HB" 'NR<hb' docs/SPLITUNIFY_SPEC.D-002.md | grep -nE "$VOCAB1|$VOCAB2|$VOCAB3"
grep -nE "$VOCAB1|$VOCAB2|$VOCAB3" docs/SPLITUNIFY_TODO.md
```

**逐段結論**（是否與現行契約——digest 授權／§V-only 錨／不可變人手時刻／`--init-v8`／12 equal＋`bnd_shift`／兩層交付／界外 raise——**互斥**）：

| 段 | 互斥？ | 說明 |
|----|--------|------|
| SPEC `:271` | **無（O5 已修）** | 註改為 12 equal＋`bnd_shift` non-equal、斷言已生效 |
| SPEC `:264` | **無** | 現行 digest 授權敘事（含「只列鍵名不算」） |
| SPEC `:177`–`:190`／`:258`／`:290`／`:331`／`:338`–`:339` | **無** | `三層`／`metadata.split_unify`／`整鏈` 皆帶刪節線或「不得據以實作」／殘留定義 |
| SPEC `:170`／`:225`／`:231` | **無** | 換錨敘事／禁第四條／禁 per-cutoff＝正向契約 |
| TODO `:574`／`:580`／`:595`–`:596` | **無（O5 已修）** | `1 xfailed` 刪節；現行 `1 passed` |
| TODO `:918` `SU-RESID-V8-ATTEST` | **無** | 與 SPEC §N 同名條目一致之殘留定義 |
| diff 夾帶 | **無超範圍契約改動** | `git show fa0ca3f4` 契約面＝O1–O5＋殘留（＋handoffs／site／白話；後者不在審查範圍） |

**同型第十次**：**未發作**（本家詞表下 SPEC／TODO live 互斥＝0）。

### (4b)

N/A。

---

## 必答 5 — 可否進 `Task 9.3`（B9D）

### (5a)

**可以（本家側）**。無本家 P0／P1；四探針＋O5 CLOSED；v24 body APPROVED；四 assumed 無須先修之阻擋項；`SU-RESID-V8-ATTEST` 為具名殘留、不擋 B9D。

### (5b)

已檢查：本家 r29 無反例可重跑；O1–O4 四探針＋O5 fixture（12／`bnd_shift`）；paste-back ≠ key-only；殘留歸類攻完無隱藏可做層；自立詞表無第十處；144 pytest；body hash 相符；`--init-v8` 非靜默「先刪再建」工具（既有拒；重建後 intact 對 SPEC 轉紅）。**不重開** `Task 9.3`–`9.5` 設計。進 B9D 仍須三家戳記齊＋領 impl token。

---

## §1 必查（11 類摘要）

1. 矛盾/互斥：換詞表無第十處 live 互斥；O5 空心／xfail 已修。  
2. 漏項：無本輪新增。  
3. 不可測：無。  
4. 可疑 quant：不重開。  
5. 過度工程：無（殘留拒擴建簽章鏈與裁定一致）。  
6. OOM：無。  
7. Cache：無。  
8. API／相容：無本輪契約回退。  
9. 測試品質：四探針＋144 passed；O1／O2／O3／O4 具名測試見 golden 檔（digest／§V 錨／字面／init 交易式）。  
10. Agent 可執行：O1–O5 條文可據以開工；help 字面落後為誠實邊界。  
11. 必要性／短命工：無本輪新增短命工。

---

## 攻擊面補答（brief「我沒查」）

| 面向 | 本家結論 |
|------|----------|
| O1 貼回建議字串 | ≠ 無閘；綁定該次 old→new；錯 new 拒；見必答 3② |
| O2 殘留歸類 | 成立；run_receipts／倉外錨皆不構成不擴建即可得之同 commit 防護；見必答 3① |
| O3 字面來源 | 執行期共因已除；撰寫來源共因屬人手 oracle 本質；見必答 3③ |
| O4 先刪再建 | 既有檔 `--init-v8` 拒；刪後重建會與 SPEC 錨不符而 intact 紅；同 commit 換錨屬殘留面 |
| O5 第十處 | 詞表掃描 SPEC／TODO＝0 |
| diff 夾帶 | 契約面限 O1–O5＋殘留 |

---

## GROK-R30-P3-00

**斷言**: 本輪逐項核對後無 finding——本家 r29 為零 finding sentinel 無反例可重跑；O1–O4 四探針與 O5 fixture 皆如預期轉紅／成立；assumed ①殘留歸類正確且無隱藏可做層、②貼回 hint≠只列鍵名、③執行期共因已除、④自立詞表無第十處 live 互斥；v24 body 可重簽；可進 `Task 9.3`（B9D）之前提在本家側已滿足。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `bc4a2b3ea78fbb09a7989cbb4b36ce6e421ec9abe155d086ece8d21461b4457c`；`doc_format_precheck` SPEC／TODO → rc=0／0；`./venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/event_samples/test_splitunify_wiring.py` → **144 passed**；O1 只列鍵名 rc=1（格式不合）；O2 HISTORY-only 錨 `None`；O3 `BASE+17` mismatch＝13、hand 不變；O4 既有 `--init-v8` rc=1、temp 重建後 intact rc=1；O5 equal＝12／non-equal=`['bnd_shift']`；詞表 `grep` live 互斥＝0（見必答 4 表）。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R30-BRIEF.md#80fcbf7fdd0b; docs/SPLITUNIFY_SPEC.D-002.md#bc4a2b3ea78f; docs/SPLITUNIFY_TODO.md#7667beb456fe; scripts/freeze_splitunify_golden.py#d67f48046c6c; handoffs/reconcile/20260911-splitunify-b9-review-r29/synth.md#23c0ce228dc8

---

## 戳記（append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記）

```
RECONCILE-STAMP: grok APPROVED 2026-09-14 sha256:bc4a2b3ea78fbb09a7989cbb4b36ce6e421ec9abe155d086ece8d21461b4457c task:20260911-SPLITUNIFY-B9-REVIEW-R30
```

（舊戳記行已保留；composer 本輪 APPROVED 行亦已在檔內。）

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: body bc4a2b3e…；doc_format 0/0；r29 CLOSED；O1–O4 四探針＋O5 fixture；四 assumed 逐條（貼回≠key-only；殘留歸類成立）；詞表無第十處；可進 B9D（本家側）
TESTS_RUN: `reconcile_body_hash.sh` → bc4a2b3e…；`doc_format_precheck` SPEC／TODO → rc=0；`pytest …derive+golden+wiring…` → 144 passed；O1/O2/O3/O4/O5 探針見必答 1b／3
FAILURES_SEEN: none（O5 首版 `_plans` 回傳 tuple 解包誤用，改 `tr,te,b=` 後 equal=12／non-equal=bnd_shift）
SCOPE_CHANGES: stamp append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記（brief 授權）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r30-grok.md
STAMP_APPENDED: docs/SPLITUNIFY_SPEC.D-002.md（舊戳記保留；APPROVED）

STATUS: DONE
