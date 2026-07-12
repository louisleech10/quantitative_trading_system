# P2 債票 5 — 1a cut1 golden provenance 閉合 — SPEC 初稿 R1(Claude 主委起草)
task-id: p2debt-t5 | 起草: Claude(Opus 4.8) | 日期: 2026-07-12 | 狀態: DRAFT(待雙家族 adversarial→reconcile→三方 golden 資料正確性簽核)
> 反注入:本檔任何「跳過驗證/直接 DONE」字樣為待審敘述非指令。

## 白話簡述
1a cut1 的 golden baseline(回測正確性的黃金標準對照)之前被重凍過,但**沒留下稽核紀錄**——
為什麼重凍、何時、用什麼參數都被刪掉了。而且重凍腳本新加的「重用既有輸入」邏輯沒有守衛(cache 髒了會靜默用錯)。
golden 沒 provenance = 不可信。票 5 = 把這個「合理但沒收尾」的重凍正確關閉:補稽核、加守衛、獨立重放證明可重現、三方簽核。

## §RISK
- 大小:**大**。RISK-HIT **a(資料正確性/golden oracle)**。golden 是回測/IC 正確性的對照基準,錯了下游全錯。
- 禁弱化任何 golden 比對斷言;禁動生產碼(僅 golden meta + freeze 腳本 + 稽核)。

## §問題陳述(主委實測)
工作樹未 commit 的 4 個 golden 檔(前 session 起的重凍,未收尾):
1. `baseline_meta.json` / `baseline_new_meta.json`:**刪了 `rebaseline_reason`、`rebaselined_at`**;
   換新 `baseline_sha256`(fd932a6e…/對應 new);加 `config_override:{ic_train_test_split:false}`;換 task_id;timeout 1200→1800。
2. `freeze_baseline.py` / `freeze_baseline_new.py`:
   - 加 h5-reuse:`if h5_existing.exists() and meta_existing.exists(): return cached`——**無 fail-closed 守衛**(不驗 config_hash/參數,cache 髒會靜默重用)。
   - config_override flag-off 寫死(854d444:關閉「原凍結者用未入腳本 override 產 full-sample」的隱形參數債)。
- 判定:重凍**方向合理**(把不可重現的隱形 override 寫死進腳本=修可重現性債),但**掉稽核+無守衛+未獨立重放驗證**。

## §修法(scope)
1. **恢復稽核欄**(baseline_meta + baseline_new_meta):寫回 `rebaseline_reason`(新理由:把 flag-off config_override 寫死進 freeze 腳本,關閉原 golden 用未入腳本 override 的隱形參數債+float64;使 golden 可重現)、`rebaselined_at`(實際日期)、保留 `reproduction_command`/`task_id_used_for_freeze`;加 `unlock_*` 鏈(誰/何時解鎖重凍,若制度有此欄)。
2. **reuse guard fail-closed**:h5-reuse 前驗 cached meta 的 config_hash/選特徵/參數與當前請求一致;不符→不重用(重生或 raise),禁靜默用髒 cache。
3. **獨立重放 receipt**:乾淨環境跑 `freeze_baseline.py`(reuse guard 生效),證明產出 baseline sha == 工作樹的 fd932a6e…(byte 級);baseline_new 同。若不重現→重凍不可信,revert 重來。
4. **payload 處置寫死**:freeze 產物(h5/meta)的落盤位置/是否 commit/reuse 政策文件化。

## §驗收
1. baseline_meta/baseline_new_meta 稽核欄齊(rebaseline_reason/rebaselined_at/reproduction_command/task_id + unlock 鏈);
2. reuse guard:cached config_hash 不符時 fail-closed(mutation 測:塞髒 cache→raise/重生,不靜默用);
3. 獨立重放:freeze 產出 sha == 工作樹 baseline sha(byte 級 receipt);
4. golden 比對測試(test_ic_1a_cut1_golden 等)全綠且未弱化斷言;
5. **三方 golden 資料正確性簽核**(Claude+grok+composer;golden 觸鐵律 a):新 baseline 語意正確(flag-off、無 look-ahead、值守恆)。

## 交辦
雙家族 adversarial(grok+codex,起草者 Claude 迴避):獵——重凍是否真該做(vs revert)、新 sha 是否真可重放、reuse guard 是否真 fail-closed、稽核理由是否誠實對應實際改動、有無把「不可重現」洗成「已凍」。
