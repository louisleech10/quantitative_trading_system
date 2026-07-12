# P2DEBT T2 C3FIX result (Codex)
Task-id: p2debt-t2-c3fix | Date: 2026-07-11

## Run C cwd 相對依賴盤點
- `test_ic_persist_redirect_golden_ab.py`: `golden.FEATURES_PATH` / `META_PATH` 源自 `Path("tests/golden/...")`；Run C chdir 前以 `.resolve()` 固定成 repo 絕對路徑，chdir 後再 monkeypatch 回 golden module。
- 同測試: 生產設定預設讀 `config/...`；`work/config -> <repo>/config` symlink 提供 cwd 相對設定輸入。
- 同測試 + `api/services/ic_analysis_service.py`: `FEATURE_KLINE_CACHE_DIR="data_cache/feature_klines"`；`work/data_cache/feature_klines -> <repo>/data_cache/feature_klines` symlink 提供唯讀真 kline。
- 同測試: OFF persist 的 `data_cache/{features,reports,models}` 是刻意 cwd 相對，先建立於 `work/`，使 sacrificial 輸出留在 tmp_path。
- `tests/fixtures/ic_persist_redirect.py`: `_repo_root()` 原本執行 `git rev-parse --show-toplevel` 且繼承 chdir 後 cwd，非 git repo 時 rc 128；本次改為 `Path(__file__).resolve().parents[2]`。
- fixture 其他 `Path(...).resolve()`（redirect/model/reporter）刻意依 active cwd 判斷原 production path；Run C gate OFF，不參與 post digest repo-root 定位。
- `tests/conftest.py`: `FEATURE_KLINE_CACHE_DIR` / `FEATURE_KLINE_H5_PATH` 為 cwd 相對；Run C 所需部分由 feature_klines symlink 滿足。`pytest_collection_modifyitems` 的 `TEST_INVENTORY_PATH` 只在 `--collect-only` 執行，本次 V5 非該路徑。
- plugin `tests.fixtures.ic_persist_redirect_plugin`: patch-set session fixture 在 chdir 前建立；其 production prefix 經修後由 `__file__` anchor，無 git/cwd 依賴。

## Diff 摘要
- `tests/fixtures/ic_persist_redirect.py`: 移除 `subprocess` import；`_repo_root()` 改成 `Path(__file__).resolve().parents[2]`。
- 未改 `tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py`、`tests/conftest.py`；其工作樹既有變更屬本任務開工前狀態。
- 未改 `momentum/`、`api/`、測試斷言、數值 gate、schema 或輸出大小。

## 驗證
- PASS: cwd smoke，命令為 `venv/bin/python` inline script，先算 expected、chdir tempdir 後呼叫 `_repo_root()`；輸出 `CWD_INDEPENDENT_REPO_ROOT=1 root=/Users/louis/Desktop/quantitative_trading_system`。
- PASS: `PYTHONPYCACHEPREFIX=/tmp/p2debt-t2-c3fix-pycache venv/bin/python -m py_compile tests/fixtures/ic_persist_redirect.py`，exit 0。首次未指定 prefix 時因使用者 Library/Caches 不可寫而 PermissionError，改用可寫 `/tmp` 後通過。
- DELEGATED-TO-ORCHESTRATOR: `bash scripts/run_ic_persist_hermetic.sh --set V5`（無 pipe）在沙箱超過 60 秒仍執行中，遂以 Ctrl-C 終止，exit 1。已收集 3 items，停在首測執行期間；未產生 `3 passed` 或 `DIGEST_DIFF_EMPTY[V5]=1` 最終 receipt，故未驗收通過。主委需原命令代跑。

STATUS: DELEGATED-TO-ORCHESTRATOR
