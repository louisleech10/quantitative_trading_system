# 票 2 實作主委驗收 finding C-3(BLOCKING,斷路器換手)
Task-id: p2debt-t2 | Chair: Claude(Fable 5) | Date: 2026-07-11

## 現象(斷路器:主委已自修 2 輪仍紅)
C-2 修復鏈:Run C `monkeypatch.chdir` 破壞 cwd 相對依賴,逐個現形:
1. R1(主委修):symlink 順序 bug(`work` 未 mkdir 先 symlink)→ 修好,現形下一個。
2. R2(主委修):`FEATURE_KLINE_CACHE_DIR="data_cache/feature_klines"`(ic_analysis_service.py:41)相對路徑
   → 補 symlink `work/data_cache/feature_klines` → repo 同名(唯讀輸入)→ 修好,現形下一個。
3. R3(本 finding):**harness fixture 自己**也 cwd 依賴——
   `tests/fixtures/ic_persist_redirect.py:69 _repo_root()` 用 `subprocess git rev-parse --show-toplevel`,
   chdir 到 tmp 後 cwd 非 git repo → rc 128 → `digest_data_cache()`(post)炸。
   receipt:/tmp/t2-v5-check3.log(1 failed 2 passed;失敗點=test L74 `after = digest_data_cache()`)。

## 重要:Run C 核心已通
- baseline 三跑(A/A/C)完成、`DIGEST_DIFF_EMPTY[V5]=1`;只剩 harness 的 post-digest 炸掉。
- 前兩修已落地 test_ic_persist_redirect_golden_ab.py(mkdir→symlink config→symlink feature_klines)。

## 修法要求(換手執行端)
不再打地鼠。要求:
1. **盤點** Run C 執行路徑(test 檔+tests/fixtures/ic_persist_redirect.py+conftest plugin)所有 cwd 相對依賴,列清單。
2. `_repo_root()` 改 cwd 無關:anchor `Path(__file__).resolve()` 上溯或 `subprocess.run(..., cwd=Path(__file__).parent)`;
   結果 lru_cache 亦可。禁改 momentum//api/ 生產碼。
3. 修後跑 `bash scripts/run_ic_persist_hermetic.sh --set V5`(禁 `| tail`),須 `3 passed`+`DIGEST_DIFF_EMPTY[V5]=1`;
   卡死標 DELEGATED 交主委代跑。
4. 允許檔:tests/fixtures/ic_persist_redirect.py、tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py、
   tests/conftest.py(僅必要)。

## 歸屬/SCAR 素材
C-2 歸屬節已預言「hermetic chdir 隔離須盤點所有相對路徑依賴」,但修復仍走逐個現形×3 輪。
規則提案:凡 chdir 型 hermetic 測試,落地前必附 cwd 依賴盤點清單(config/data_cache/git/其他 subprocess)。
