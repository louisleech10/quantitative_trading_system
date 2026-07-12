# P2DEBT-T5-ADV-grok — 雙家族 adversarial（起草者 Claude 迴避）

**task-id**: t5-adv-grok | **agent**: Grok | **date**: 2026-07-12  
**scope**: 只讀稽核 + 可證偽重放/mutation；**未改** production / golden 工作樹碼（重放走 pytest/獨立腳本，未跑會覆寫 baseline 的 freeze 主路徑）  
**input**: `handoffs/P2DEBT-T5-GOLDENPROV-SPEC-DRAFT-R1.md` + WT diff 4 檔 + RCA `IC1A-ALIGN-B2-GOLDEN-RCA-{codex,composer}.md` + 854d444 + quarantine/original_regen

---

## VERDICT: **BLOCK**

不可把目前工作樹 4 檔當「已閉合可 commit 的 provenance 重凍」。flag-off 寫死方向本身是修真債，但 **刪稽核欄 + 無 reuse fail-closed + 把 post-B2 新 oracle 洗成「只補 override」** 三項同時成立 → BLOCK。

---

## 獵點裁決

### (1) 重凍該做還是 revert？flag-off 是修真債還是引入錯？

| 層 | 裁決 | 證據 |
|----|------|------|
| **854d444 B2 重凍** | **該做（修真錯）** | Composer RCA：OLD rolling IC `concat` index-join **0 列**→summary 全 None；B2 修軸後 50/50 有 rolling；7 特徵首次落 icir。Codex 初判 FIX-CODE 主指 float64；commit 採 MIXED（保 index + 修 dtype）後重凍。 |
| **flag-off 寫進 freeze** | **修真債，非引入錯** | `ICConfig.ic_train_test_split` 自 `d3b2dff` 預設 **True**；HEAD `freeze_baseline.py` **無** override → 裸跑會走 OOS 非 G-OLD。Golden 測試自始顯式 `split_on=False`（`test_ic_1a_cut1_golden.py:56-57,85`）。Composer RCA 亦寫 cut1 flag-off。原 854 腳本無 override 卻產出 full-sample = **隱形參數**（見 `ic1a_cut1_original_regen/README.md` 推論；原始執行 log 已滅）。 |
| **WT 這次 meta/sha 置換** | **不可原樣收** | 刪 `rebaseline_reason`/`rebaselined_at`；sha `963ba4f2…`→`fd932a6e…`；原 gitignored payload **滅失**（quarantine README）。現行 oracle **≠** 854 歷史重生件（見 CE3）。 |

**不是整包 revert**：revert 掉 flag-off 寫死會重新打開「腳本語意≠G-OLD」洞；也無法 `git restore` 回 963ba payload。應 **KEEP flag-off + 修 guard + 誠實補 provenance**，不是假裝 854 原件回來。

### (2) `fd932a6e…` 真能重放嗎？

| 命題 | 結果 | 命令/證據 |
|------|------|-----------|
| meta 聲稱 sha == 磁碟 baseline 檔 | **是** | `shasum -a 256 tests/golden/.../baseline_old_*.json` → `fd932a6e616dad7d…` 與 meta 一致；new → `35e15ce9…` |
| **file-byte 級**再 freeze 仍得同 sha | **否（結構性）** | payload 含易變 `generated_at`；CE2：只改該欄 → sha 變。freeze 用 `_sha256(file)` 含此欄。Draft §驗收「byte 級 == fd932a6e」**過度承諾**。 |
| **語意級**（pop `generated_at`）== 現行碼 | **是** | `pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -v` → **2 passed**（56s）。此為獨立重放 receipt（等同 freeze 的 service 路徑 + 顯式 flag）。 |
| 未在 WT 跑 `freeze_baseline.py` | 有意 | 會覆寫 baseline；語意重放已由 golden 覆蓋。 |

### (3) h5-reuse 是否無 fail-closed？

**是 — 確認無守衛。**

```text
if h5_existing.exists() and meta_existing.exists():
    sel = json.loads(meta_existing.read_text())["baseline_subset"]["selected_features"]
    return h5_existing, meta_existing, sel
```

無：config_hash 一致性、selected_features vs 當前 `sorted(names)[:max]`、h5 欄位/位元雜湊、max_features 語意核對。  
**CE1（可證偽）**：dirty meta `selected_features=['TOTALLY_WRONG_FEATURE_AAA',…]`（可再改 `config_hash=DEADBEEF…`）→ reuse 分支 **靜默 return 髒 sel**，不 raise、不重生。`MUTATION_SILENT_REUSE=True`。

### (4) 稽核理由是否誠實對應 diff？

| Draft/註解敘事 | 實際 diff | 誠實？ |
|----------------|-----------|--------|
| 補 flag-off 關閉隱形參數債 | freeze_old 加 `config_override:false`；meta request 加同欄 | **部分真** |
| （暗示）僅 provenance 收尾 | **刪** B2 的 `rebaseline_reason`/`rebaselined_at`；換 task_id；timeout 字串 1200→1800；new 修 reproduction 腳本名 | **不誠實刪史** |
| 新 sha 只因 flag-off 寫死 | 854 重生 norm=`2f3617b9…`（selection_scope=None）；WT norm=`85f65830…`（有 full selection_scope/FDR 結構）→ **post-B2 碼漂移新 oracle** | **敘事不足** |
| 加 h5-reuse 方便 | 兩邊 freeze 加 exists 短路 | **真，且引入 CE1 洞** |

---

## 可證偽反例（至少一；下列三條皆可獨立複驗）

### CE1 — 髒 inputs 靜默 reuse（BLOCKING）
1. 複製 `inputs/*_top50_meta.json`，改 `baseline_subset.selected_features` 為偽造名（或改內嵌 config_hash）。  
2. 執行 reuse 同構邏輯（或未來未修的 freeze）。  
3. **期望 fail-closed**；**實測** return 髒 features、不 raise。  
→ Draft §修法-2 必要；**現況未滿足**。

### CE2 — `baseline_sha256` 非 file-byte 可重放（BLOCKING vs draft 驗收措辭）
1. 對 baseline JSON 僅改 `generated_at`。  
2. 以 freeze 同款 canonic+sha256。  
3. sha **必變**。  
→ 不得把「重跑 freeze 得 fd932a6e 原檔 byte」當 gate；應改 **normalized sha（exempt generated_at）** 或 golden deep-equal receipt。

### CE3 — 現行 oracle ≠ 854d444 歷史重生（BLOCKING vs「只關隱形 override」話術）
```text
WT old file:   fd932a6e…  norm(exempt gen)=85f65830…  selection_scope 有 (split_label=full)
854 regen:     b31115d2…  norm=2f3617b9…              selection_scope=None
quarantine:    bc710cfe…  norm=e029e941…              （已宣告不可信自凍）
cross: r854==rc0b norm 2f3617b9…（receipts 吻合）
NORM_NE wt!=r854
```
命令：`shasum -a 256` 各檔 + python `json.loads→pop generated_at→dumps(sort_keys)→sha256`。  
→ 若 rebaseline_reason 只寫 flag-off、不寫「對齊當前 HEAD 輸出 schema/selection_scope 等」，即 **用窄理由洗寬漂移**。

---

## RCA / 854d444 對照摘要

- **Composer**：REBASELINE；主因 index 錯配；cut1 **flag-off**。  
- **Codex**：初判 FIX-CODE（float64）；dtype 與 index 可分。  
- **854d444 訊息**：MIXED + 重凍 + 寫 rebaseline provenance（HEAD meta 仍在；**WT 刪了**）。  
- flag-off 寫死 = 對齊測試與 G-OLD 契約，**不是** 854 引入的錯；854 錯在腳本未入帳 override + 後續 gitignore 滅件。

---

## 對 draft 的處置建議（非實作）

1. **KEEP** `config_override` 寫死（old=false / new=true）與 meta.request 對齊。  
2. **RESTORE/重寫** `rebaseline_reason`+`rebaselined_at`+unlock 鏈：須同時承認 (a) 隱形 override 入帳 (b) 原 963ba 滅失 (c) 新 oracle 對齊 **當前** 碼（norm≠854 regen）(d) 禁止只抄 B2 舊句或只寫 flag-off。  
3. **MUST** reuse fail-closed（config_hash / selected_features / 可選 h5 sha）+ mutation 測。  
4. 驗收改：**normalized** 重放或 `test_ic_1a_cut1_golden` 綠；**禁止**要求 raw `fd932a6e` 可再凍重現。  
5. quarantine / original_regen 留作審計鏈，勿與 WT 現行 oracle 混稱為同一 byte 史。

---

## VERIFY receipts（本 agent）

```text
ASSUMPTIONS_VERIFIED:
- schema default ic_train_test_split=True since d3b2dff
- HEAD freeze_baseline.py had no config_override; freeze_baseline_new already True in run
- WT meta deleted rebaseline_*; sha claims match on-disk gitignored baselines
- h5-reuse exists-only; dirty meta silent reuse
- WT norm ≠ 854 regen norm
- golden 2 passed ⇒ semantic replay current code == WT baselines (exempt generated_at)

TESTS_RUN:
- pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -v → 2 passed in 56.06s
- shasum -a 256 on WT/quarantine/original_regen baselines
- python normalized-sha + CE1 mutation + CE2 generated_at sha

FAILURES_SEEN: none material to verdict; standalone freeze wrapper aborted early in this env — golden path used instead (no WT overwrite)

SCOPE_CHANGES: none (read-only)

NUMERIC_OR_SCHEMA_IMPACT: none (no code edits)
```

**STATUS: DONE**（adversarial 產出完成；對 draft 的產品 verdict = **BLOCK**）
