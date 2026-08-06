# 探針 fixture — 真實 format-failed 形態（缺 source digest）

來源：2026-08-06 `GOVB39-B1-CONSULT` R1，composer 產出因每個 P0/P1 finding 缺
`**來源摘要**:` 欄而 `result_state=format-failed`，導致整輪 abandon 重派。

本檔逐字保留該形態（內容已改為中性探針值），供 `test_cxrun_selfcheck_prompt.py`
驗證「交件前自檢確實攔得下這種真實發生過的失敗」。**勿修成合規**——它必須維持 rc=1。

## COMPOSER-R1-P0-01

**斷言**: 探針用 finding，刻意缺 `**來源摘要**` 欄。
**碼證**: `scripts/completeness_check.sh` 的 P0/P1 digest 檢查。
[BLOCKING] 信心度=High。本檔為 fixture，非真實 finding。
