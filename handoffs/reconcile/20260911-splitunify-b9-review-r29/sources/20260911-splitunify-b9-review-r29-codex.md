## CODEX-R29-P1-01
**斷言**: assumed 1 不成立；`--accept-value-changes` 只驗 key 名，任意既有值仍可被明確旗標改寫。**來源摘要**: scripts/freeze_splitunify_golden.py#c8c5a46f6804; docs/SPLITUNIFY_SPEC.D-002.md#1d21d7384902
**碼證**: 無旗標 temp probe rc=1 且值不變；具名旗標 rc=0、`g4_per_symbol_n {'ETHUSDT': 13} -> {'ETHUSDT': 999}`；CODE-ANCHOR: scripts/freeze_splitunify_golden.py:616
MUTATION: temp-copy main golden，改 `actual["g4_per_symbol_n"]` 為 `{"ETHUSDT":999}`，執行 `main(["--write","--accept-value-changes","g4_per_symbol_n"])`；修法/可行性：改用 review-bound、不可由 CLI 自行新增的 exact old/new digest changeset，現有 `_changed` 可在 `write_text` 前逐項比對，並保留合法重凍的明示 changeset。
## CODEX-R29-P1-02
**斷言**: assumed 3 不成立；helper 改讀 SPEC 雖移除第二份常數，但 regex 接受 SPEC 任意位置且 SPEC 可與 v8/sidecar 同一變更同步替換，故並非獨立信任根。**來源摘要**: scripts/freeze_splitunify_golden.py#c8c5a46f6804; docs/SPLITUNIFY_SPEC.D-002.md#1d21d7384902
**碼證**: 原 v8 不變、SPEC 不變時 rc=1；temp SPEC 只在 HISTORY 放新 anchor、同步新 v8+sidecar 時 rc=0；CODE-ANCHOR: scripts/freeze_splitunify_golden.py:435
MUTATION: temp SPEC 的 HISTORY 寫入新 `V8_BASELINE_SHA256` 並同步替換 v8/sidecar，執行 `_assert_v8_baseline_intact()` 得 `N2_SAME_COMMIT_REPLACED_SPEC_RC 0`；修法/可行性：parser 限定 §V 範圍並拒絕外部 literal，真正同 commit 防護另加受保護簽章/不可變 ancestor attestation；anchor 讀取集中於 `_read_v8_anchor_from_spec`，一次修訂可加兩層測試。
## CODEX-R29-P1-03
**斷言**: assumed 2 不成立；`expected_decision_at_ms` 與實際 decision 共同由 `BASE`/`H1` 生成，整批共因位移仍會兩欄相等。**來源摘要**: scripts/freeze_splitunify_golden.py#c8c5a46f6804; tests/momentum/Analysis/test_splitunify_golden.py#21e737d7f23e
**碼證**: `BASE += 17` 後仍 `N3_BASE_SHIFT_AFTER_EQUAL True`、13 rows、delta `[17]`；CODE-ANCHOR: scripts/freeze_splitunify_golden.py:145
MUTATION: 將 `m.BASE` 平移 17ms，重建 index/plans/keys，觀察 `before_equal=True`、`after_equal=True`；修法/可行性：將 hand timestamps 改為不依賴 BASE/H1 的逐筆 immutable literals，現有 dict 對帳不變，該 mutation 即可轉紅。
## CODEX-R29-P1-04
**斷言**: write-once 首次建立未接到 `main`，且兩檔逐一 `O_EXCL` 會留下半套狀態；v8 缺失時 `--write` 直接 fail，不符合 TODO 9.5 首建成功邊界。**來源摘要**: scripts/freeze_splitunify_golden.py#c8c5a46f6804; docs/SPLITUNIFY_TODO.md#df8037f51f4a
**碼證**: clean helper first-create rc=0/pair=True，但 `main --write` 缺 v8 得 rc=1、`V8_CREATED False`；sidecar 預存時 helper rc=1 且 `V8_EXISTS True`；CODE-ANCHOR: scripts/freeze_splitunify_golden.py:522
MUTATION: temp golden 移除 v8/sidecar 後執行 `venv/bin/python scripts/freeze_splitunify_golden.py --write`，再以預存 sidecar 呼叫 `create_v8_baseline_write_once`；修法/可行性：在完整性 gate 前接明確 init-v8 分支，先驗兩檔皆不存在並以交易式 pair create/失敗回收，補 clean、partial、main-missing 三測試。
## CODEX-R29-P1-05
**斷言**: assumed 4 不成立；第九個同步缺口仍在：SPEC §V:270 說 fixture 全部 decision=cutoff，但現況有 `bnd_shift`；TODO 9.2a:570/574/590 仍要求已完成 B9C 的 node `xfailed`。**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#1d21d7384902; docs/SPLITUNIFY_TODO.md#df8037f51f4a; scripts/freeze_splitunify_golden.py#c8c5a46f6804
**碼證**: fixture probe 得 equal count 12、non-equal `['bnd_shift']`；TODO node 實跑 `1 passed` 而非要求的 `1 xfailed`；CODE-ANCHOR: docs/SPLITUNIFY_SPEC.D-002.md:270
MUTATION: 執行 `venv/bin/python -m pytest -q -rxX tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed`，觀察 `1 passed`；修法/可行性：SPEC 改寫為 12 equal + `bnd_shift` non-equal 的 active assertion，TODO 改為 B9C 完成後常規 `1 passed`，一次文件修訂可閉合。
VERDICT: blocked
BLOCKED-BY: CODEX-R29-P1-01,CODEX-R29-P1-02,CODEX-R29-P1-03,CODEX-R29-P1-04,CODEX-R29-P1-05
CLOSED: CODEX-R28-P1-01,CODEX-R28-P1-02,CODEX-R28-P1-03,CODEX-R28-P1-04
ASSUMPTIONS_VERIFIED: r28 四條原反例均 CLOSED（無旗標值閘 rc=1；anchor/檔案篡改 rc=1；+1ms gate 會列出 mismatch；TODO:273 現為 decision 越界 raise）；r29 assumed 1/2/3/4 均不成立；自立詞表 scan 逐段結論：SPEC C3/§G/§P/§V/§N 與 current contract 一致，§V:270 是唯一 stale contradiction；TODO §0/§B/Task1–2.3/3–4/9.1/9.2/9.2b–9.5/§D/§E 皆一致，Task9.2a:563–590 為唯一 stale xfail contradiction。
TESTS_RUN: `venv/bin/python scripts/freeze_splitunify_golden.py` → `GOLDEN OK`, rc=0；focused pytest golden+derive → 126 passed；r28 targeted → 4 passed；required node → 1 passed；doc_format SPEC/TODO rc=0、todo_spec_crosscheck rc=0、spec_v_task_ref rc=0；body hash after stamp → `52efba2e...`, rc=0；r29 temp probe outputs as above。
FAILURES_SEEN: 不存在的 `scripts/spec_todo_precheck.sh` → rc=127；首版 temp harness 僅因 `/tmp` 路徑 `relative_to(REPO)` traceback，repo 未變更，修正後 probes 完成；stamp checker rc=1 僅因本 task 尚待 register-output provenance，非產品測試 failure。
SCOPE_CHANGES: 僅新增本交件檔及在 SPEC `## 戳記` 末尾 append codex r29 stamp；未改程式、SPEC 正文、TODO、根 HANDOFF 或 data_cache；本輪 `/tmp/r29-*` workdirs 已由 TemporaryDirectory 自動清空，保留 `/tmp/claude-501`；既有 shared logs/sessions 未刪除。
NUMERIC_OR_SCHEMA_IMPACT: 本輪 review 未修改 runtime、golden、數值或 wire schema；提出的修法不代表已落地輸出變更。
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r29-codex.md
STATUS: DONE
