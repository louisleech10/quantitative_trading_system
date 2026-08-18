#!/usr/bin/env bash
# plain_docs_render.sh — 把 白話說明/*.md（含 Archived/）生成 docs/site/*.html（人類閱讀介面）。
#
# 為何存在（使用者 2026-08-18 定，小任務 3b）：白話說明是給使用者看的，但 .md 在 GitHub 上讀表格／
#   狀態燈不友善、手機更差。決定＝**來源維持 .md 不動**（我、委員、所有守衛照讀 .md），另由本腳本生成
#   HTML（index、CSS、手機友善）。GitHub Pages 設「Deploy from branch: main, /docs」後網址＝
#   https://<user>.github.io/<repo>/site/ ；本機 `open docs/site/index.html`。
#
# 強制機制（本專案第 3 條治理原則：工具必須自帶強制，不靠紀律）：
#   掛 `scripts/git_hooks/pre-commit`——staged 含 白話說明/**.md 或本渲染器 ⇒ 重生成並 `git add docs/site`，
#   然後 `--check` 驗「每個 .md 都有對應且最新的 .html、0 死連結」，不符 ⇒ **擋 commit**（缺產出即擋）。
#
# 用法：
#   bash scripts/plain_docs_render.sh            # 生成／更新 docs/site/（冪等；同輸入 byte 級同輸出）
#   bash scripts/plain_docs_render.sh --check    # 只驗不寫；不一致或有死連結 ⇒ rc=1
#   bash scripts/plain_docs_render.sh --selftest # 在 tmp 造最小語料驗三件事：冪等／每 md 對應 html／連結改寫
#
# 憲法：bash 3.2；rc 直接取禁經 pipe；渲染邏輯全在 scripts/plain_docs_render.py（venv 現成 markdown_it）。
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 2
cd "$ROOT" || exit 2

PY="venv/bin/python"
RENDERER="scripts/plain_docs_render.py"
if [ ! -x "$PY" ]; then
  echo "[plain_docs_render] ERROR: venv/bin/python 不存在（渲染器依賴 venv 內 markdown_it）" >&2
  exit 2
fi
if [ ! -f "$RENDERER" ]; then
  echo "[plain_docs_render] ERROR: 渲染器缺失: $RENDERER" >&2
  exit 2
fi

case "${1:-}" in
  --selftest)
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    mkdir -p "$tmp/白話說明/Archived"
    printf '# 甲\n\n說明 [乙](乙.md) 與 [丙](Archived/丙.md)。\n\n| a | b |\n|---|---|\n| 1 | 2 |\n' > "$tmp/白話說明/甲.md"
    printf '# 乙\n\n回 [甲](甲.md)。\n' > "$tmp/白話說明/乙.md"
    printf '# 丙\n\n回 [甲](../甲.md)。\n' > "$tmp/白話說明/Archived/丙.md"
    "$PY" "$RENDERER" --repo "$tmp" --src "$tmp/白話說明" --out "$tmp/docs/site" >/dev/null 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || { echo "SELFTEST FAIL: 首次生成 rc=$rc"; exit 1; }
    for f in 甲 乙 Archived/丙; do
      [ -f "$tmp/docs/site/$f.html" ] || { echo "SELFTEST FAIL: 缺 $f.html"; exit 1; }
    done
    [ -f "$tmp/docs/site/index.html" ] && [ -f "$tmp/docs/site/style.css" ] || { echo "SELFTEST FAIL: 缺 index/style"; exit 1; }
    grep -q 'href="乙.html"' "$tmp/docs/site/甲.html" || { echo "SELFTEST FAIL: 站內連結未改寫成 .html"; exit 1; }
    grep -q 'href="Archived/丙.html"' "$tmp/docs/site/甲.html" || { echo "SELFTEST FAIL: Archived 連結未改寫"; exit 1; }
    grep -q 'href="../甲.html"' "$tmp/docs/site/Archived/丙.html" || { echo "SELFTEST FAIL: 上層連結未改寫"; exit 1; }
    grep -q 'class="table-wrap"' "$tmp/docs/site/甲.html" || { echo "SELFTEST FAIL: 表格未包 table-wrap"; exit 1; }
    before="$(cat "$tmp/docs/site/"*.html "$tmp/docs/site/Archived/"*.html | shasum -a 256)"
    "$PY" "$RENDERER" --repo "$tmp" --src "$tmp/白話說明" --out "$tmp/docs/site" >/dev/null 2>&1
    after="$(cat "$tmp/docs/site/"*.html "$tmp/docs/site/Archived/"*.html | shasum -a 256)"
    [ "$before" = "$after" ] || { echo "SELFTEST FAIL: 非冪等（二次生成內容不同）"; exit 1; }
    "$PY" "$RENDERER" --repo "$tmp" --src "$tmp/白話說明" --out "$tmp/docs/site" --check >/dev/null 2>&1 || { echo "SELFTEST FAIL: --check 對最新產出應 rc=0"; exit 1; }
    printf '# 乙\n\n改了。\n' > "$tmp/白話說明/乙.md"
    "$PY" "$RENDERER" --repo "$tmp" --src "$tmp/白話說明" --out "$tmp/docs/site" --check >/dev/null 2>&1
    rc=$?
    [ "$rc" -eq 1 ] || { echo "SELFTEST FAIL: 來源改了但 --check 未報過期（rc=$rc，應 1）"; exit 1; }
    printf '# 乙\n\n[死](不存在.md)\n' > "$tmp/白話說明/乙.md"
    "$PY" "$RENDERER" --repo "$tmp" --src "$tmp/白話說明" --out "$tmp/docs/site" >/dev/null 2>&1
    rc=$?
    [ "$rc" -eq 1 ] || { echo "SELFTEST FAIL: 死連結應使生成 rc=1（rc=$rc）"; exit 1; }
    echo "SELFTEST PASS: 冪等／每 md 對應 html／連結改寫／過期偵測／死連結偵測 皆成立"
    exit 0
    ;;
  --check)
    "$PY" "$RENDERER" --check
    exit $?
    ;;
  "")
    "$PY" "$RENDERER"
    exit $?
    ;;
  *)
    echo "用法: bash scripts/plain_docs_render.sh [--check|--selftest]" >&2
    exit 2
    ;;
esac
