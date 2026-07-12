# 票 2 實作主委驗收 finding C-2(BLOCKING)
Task-id: p2debt-t2 | Chair: Claude(Opus 4.8) | Date: 2026-07-11

## 現象
harness C-1 修好後,主委代跑完整 hermetic all(claim p2debt-t2-impl-final3):
V1 9 passed / V2 2 passed(皆 DIGEST_DIFF_EMPTY=1)→ **V5 `1 failed, 2 passed`**,SCRIPT_RC=1,V6/V7 未跑(set -e)。

## 根因(receipt log t2-hermetic-all3.log)
- 失敗測試:`test_ic_persist_redirect_golden_ab.py::test_golden_redirect_on_off_sha256`(Run C=OFF 模式)。
- traceback:`ic_config_schema.py:428 load_ic_config → _read_yaml(Path("config/ic_config.yaml"))` → `FileNotFoundError`。
- 機理:Run C 設計用 `monkeypatch.chdir(tmp/work)` 給 OFF 模式犧牲根;但生產碼以**相對路徑** `config/ic_config.yaml` 載入 config,cwd 一改就解析到 `tmp/work/config/ic_config.yaml`(不存在)。
- 非 data_cache 洩漏:`DIGEST_DIFF_EMPTY[V5]=1`,且 V1 同測試(cwd 未改)通過。

## 修法要求(派 codex)
Run C OFF 模式須在 chdir 後仍能載入 config。最小修法(擇一,不改生產碼相對路徑語意):
1. Run C setup 在 chdir 前將 repo `config/` symlink/複製進 `tmp/work/config/`(保留 OFF 模式 ./data_cache 相對解析語意);或
2. 設定 config 路徑環境變數/絕對化(若 load_ic_config 支援 override)——先查 ic_config_schema.py 是否有 env/參數 override,無則用法 1。
允許檔:僅 tests/ 內 Run C 測試/fixture(勿改 momentum/ 生產碼)。
修好後完整重跑 `--set all`(禁 | tail),V1-V7 全綠+各 DIGEST_DIFF_EMPTY=1;卡死標 DELEGATED 交主委代跑。

## 歸屬
Run C hermetic-cwd 設計(SPEC §G,grok NEW-R3-2 提出+codex R4 用 chdir 落實)未預見相對 config 路徑在 chdir 下失效——SCAR 素材:hermetic chdir 隔離須盤點所有相對路徑依賴(config/data_cache/其他)。
