## Verdict：需修補後派工；R2 X1–X7 原議題均 CLOSED，但新增 CODEX-R3-P1-01，暫不能進 B1。

## CODEX-R3-P1-01

**斷言**: R2 X4 的 serializer gate 在 SPEC／TODO 未同步覆蓋三個入口；`scan_cube._dumps` 可讓非有限 ICIR 落成非標準 JSON，實作只照 TODO 會漏驗。
**碼證**: SPEC `EVTWARMUP_SPEC.md:80-81` 要求 `save_report`、`ic_reporter.py:726`、`scan_cube._dumps:71-73` 皆過 strict `parse_constant`；TODO `EVTWARMUP_TODO.md:46-48` 檔案／驗證只明列 `ic_reporter.py` 與 `save_report`。`build_cube` 以 `_dumps` 寫 `scan_cube.py:228,309`；實跑 `venv/bin/python -c 'import json; from momentum.Analysis.scan_cube import _dumps; text=_dumps({"icir":float("nan"),"ic_mean":float("inf")}); print("SCAN_CUBE_DUMPS="+text); json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))'` → `SCAN_CUBE_DUMPS={"icir":NaN,"ic_mean":Infinity}`、`ValueError: NaN`、rc=1。RECHECK：重跑同一命令並檢查 `scan_cube.py:68-73,228,309`。
**來源摘要**: docs/EVTWARMUP_SPEC.md#ef3c3c555571;docs/EVTWARMUP_TODO.md#5de8901b9f6e;momentum/Analysis/scan_cube.py#2b27c3d9e42f
[MAJOR] 信心度=10/10；未來 Agent 可能完成 reporter sanitizer 卻遺漏 Tier A／B scan cube，產生可被寬鬆 parser 接受、但 strict JSON gate 拒絕的產物。修法：在 TODO Task 2.1 明列 `scan_cube.py`（Tier A／B）與 `export_all` 的 producer／serializer 責任、非有限值轉 `null` 或 fail-closed 的單一政策，並為兩層落檔各加 strict parse gate；保持既有逐列／逐節 raw-copy invariant。

R2 disposition：X1 CLOSED；X2 CLOSED；X3 CLOSED；X4 CLOSED（原錯誤 allow_nan 事實已改列 FACT-RECEIPT）；X5 CLOSED；X6 CLOSED；X7 CLOSED。
必答 1b：有新矛盾，即 SPEC 三入口要求與 TODO 僅驗 `save_report`／未列 `scan_cube.py` 不一致（見 CODEX-R3-P1-01）。
必答 2a/2b：fallback rerun 會重算 consumed predicate，scan cube 每格獨立判定；文件指定的 stage3 後地板時序可行，且 (e′) 防止合法棄條件路徑誤標 `insufficient_test_events`。
必答 3a/3b：`_finite_or_neg_inf` 的 reporter 三處與 `get_top_features` 已列全；serializer 三入口只在 SPEC 列全，TODO／scan cube 尚未閉合。有限全域值的排序／golden 不變有明文 oracle，但未實作前不能宣稱已驗。
必答 4：無 ≥10× 不必要複雜度；必答 5：不可進 B1，先修 P1-01。
類別(1–11)：1=P1-01；2=P1-01；3=P1-01；4=無；5=無；6=無；7=無；8=P1-01；9=P1-01；10=P1-01；11=無。
§0：fact-verified＝三份 template_check rc=0；baseline probe rc=0、sha256 `af73d325e0c4` 且 golden=True；scan cube strict probe rc=1 並輸出 NaN/Infinity。assumed＝尚未有本票實作，因此完整真實 scan cube payload 的非有限值分布未驗；finding 僅主張序列化政策與 TODO 覆蓋不足。
TESTS_RUN：`bash scripts/template_check.sh spec docs/EVTWARMUP_SPEC.md` rc=0；同命令 TFWINDOW rc=0；`bash scripts/template_check.sh todo docs/EVTWARMUP_TODO.md` rc=0；`venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` rc=0／golden=True；上述 scan cube strict probe rc=1（預期暴露缺口）。
FAILURES_SEEN：scan cube strict probe 預期 rc=1；無測試治理套件。
SCOPE_CHANGES：唯讀審查；未改程式、SPEC、TODO 或 data_cache；產出=`handoffs/20260908-evtwarmup-x-review-r3-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT：本次未修改；指出 scan cube JSON null／strict gate 與既有 raw-copy invariant 的待明確化影響。
STATUS: DONE
