#!/usr/bin/env bash
# gen_fact_key_blocks.sh — 票 B-25 事實單一來源：生成器 ＋ 漂移檢查（Task 2.1）
#
# 模式：
#   （無參數）  將全部 fact-key 之 generated block 印到 stdout（決定性；供 sha 比對）
#   --check     重新生成並與宿主檔內既有區塊 diff；不一致 ⇒ rc≠0
#   --write     以重新生成的內容就地覆寫宿主檔內既有區塊（邊界標記須已存在）
#
# 環境變數：
#   GOVB1_FACTKEY_ROOT  宿主檔查找根目錄（預設 `.`）。供測試指向 fixture 目錄。
#                       只影響「去哪裡找宿主檔」，不影響註冊表位置。
#
# 註冊表＝與本腳本同目錄之 fact_keys.json；schema 定義寫在該檔 `_schema` 內（唯一定義處）。
#
# 決定性契約（缺一即 diff 恆紅 ⇒ 機制退化成噪音〔COMPOSER-R1-P2-03〕）：
#   · LC_ALL=C 固定 collation —— 禁依賴環境 locale
#     🔴 實測（2026-08-09，本機 macOS）：`a-y / B-x / _z` 三列
#        LC_ALL=C        → B-x _z a-y
#        LC_ALL=en_US.UTF-8 → _z a-y B-x
#        ⇒ 拿掉 LC_ALL=C 會使輸出隨環境改變，T-2.1-M1 據此可證偽。
#
# 🔴 FKPERF（票 HP-FKPERF／docs/FKPERF_SPEC.md Task 4.1）起，本檔為**薄包裝**：判定實作全數在
#   同目錄之 `_gen_fact_key_blocks.py`（單一 Python 程序，外部程序數與開檔數不隨 fact-key 數成長）。
#   第 2–20 行為 `--help` 之輸出來源（核心於前置檢查後原文印出），**勿改動其行數與內容**。
#   前置：缺 python3 ⇒ fail-closed（C-5）；其餘 fail-closed 點見核心。
#   回退走 git revert（不保留 bash 實作作為備援或切換旗標：雙實作即雙倍漂移面）。
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null 2>&1 \
  || { printf '%s\n' "gen_fact_key_blocks: 缺 python3 → fail-closed" >&2; exit 1; }
exec python3 "${SCRIPT_DIR}/_gen_fact_key_blocks.py" "$@"
