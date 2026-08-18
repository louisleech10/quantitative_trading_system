"""plain_docs_render.py — 把 白話說明/*.md（含 Archived/）渲染成 docs/site/*.html（人類閱讀介面）。

由 `scripts/plain_docs_render.sh` 呼叫（勿直接跑）。設計原則：
- **來源維持 .md 不動**（我與委員、所有守衛仍讀 .md）；HTML 是純產物，勿手改。
- **冪等**：同一輸入 ⇒ byte 級相同輸出（無時間戳、無隨機；nav 由排序清單導出）。
- 連結：`x.md`／`Archived/x.md`／`../x.md` 若指向 白話說明 內既有 .md ⇒ 改為對應 `.html`；
  `../docs/<f>` ⇒ `../<f>`（site 位於 docs/site/，GitHub Pages 以 /docs 為根）；其他保持原樣。
- 標題加 GitHub 樣式 id（`#片段` 連結可用）；表格包 `.table-wrap`（手機橫向捲動）。
- `--check`：不寫檔，只驗「每個 .md 都有對應 .html 且內容與現渲染 byte 相同、站內連結不死」；不符 rc=1。

用法：venv/bin/python scripts/plain_docs_render.py [--check] [--src 白話說明] [--out docs/site]
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from markdown_it import MarkdownIt
from markdown_it.token import Token

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SRC = REPO / "白話說明"
DEFAULT_OUT = REPO / "docs" / "site"

# 首頁排序（先列這些；其餘依檔名排序）
INDEX_ORDER = [
    "README.md",
    "接下來要做什麼.md",
    "GAP-1施工進度.md",
    "IC健檢施工進度.md",
    "IC健檢偵察結果.md",
    "流程摩擦記錄.md",
    "治理進度日誌.md",
]

CSS = """\
:root{--bg:#fff;--fg:#1c1e21;--muted:#5f6368;--link:#0b57d0;--border:#e0e0e0;--code:#f4f5f7;--accent:#f6f8fa}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--fg:#e6e6e6;--muted:#9aa0a6;--link:#8ab4f8;--border:#2a2e35;--code:#181b21;--accent:#161a20}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC","PingFang TC","Microsoft JhengHei",Helvetica,Arial,sans-serif}
a{color:var(--link);text-decoration:none}a:hover{text-decoration:underline}
.top{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--border);padding:.5rem 1rem;display:flex;gap:1rem;align-items:center;font-size:.9rem;z-index:1}
.top .crumb{color:var(--muted)}
main{max-width:52rem;margin:0 auto;padding:1rem 1rem 4rem}
h1{font-size:1.6rem;line-height:1.3;margin:1rem 0 .75rem}h2{font-size:1.3rem;margin:2rem 0 .5rem;padding-top:.5rem;border-top:1px solid var(--border)}
h3{font-size:1.1rem;margin:1.5rem 0 .5rem}h4{font-size:1rem}
h1,h2,h3,h4{scroll-margin-top:3rem}
p,li{overflow-wrap:anywhere}
blockquote{margin:1rem 0;padding:.5rem 1rem;border-left:4px solid var(--border);background:var(--accent);color:inherit}
blockquote p{margin:.4rem 0}
code{font:.9em ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:var(--code);padding:.1em .35em;border-radius:4px}
pre{background:var(--code);padding:.75rem;border-radius:6px;overflow-x:auto;font-size:.85rem;line-height:1.5}
pre code{background:none;padding:0;white-space:pre}
.table-wrap{overflow-x:auto;margin:1rem 0;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;min-width:100%;font-size:.92rem}
th,td{border:1px solid var(--border);padding:.4rem .6rem;vertical-align:top;text-align:left}
th{background:var(--accent);position:sticky;top:0}
tr:nth-child(even) td{background:var(--accent)}
hr{border:0;border-top:1px solid var(--border);margin:2rem 0}
img{max-width:100%}
.index-list{list-style:none;padding:0}.index-list li{padding:.6rem 0;border-bottom:1px solid var(--border)}
.index-list .desc{color:var(--muted);font-size:.9rem;display:block}
footer{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--border);color:var(--muted);font-size:.85rem}
@media (max-width:600px){body{font-size:15px}main{padding:.75rem .75rem 3rem}h1{font-size:1.35rem}h2{font-size:1.15rem}table{font-size:.85rem}}
"""


def _slug(text: str) -> str:
    """GitHub 樣式標題 id：小寫、去標點（保留中日韓／字母／數字／連字號／底線）、空白→-。"""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s\-一-鿿㐀-䶿぀-ヿ가-힯]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text


def _md() -> MarkdownIt:
    return MarkdownIt("commonmark").enable("table").enable("strikethrough")


def _title_of(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip().strip("*").strip()
    return fallback


def _first_para(md_text: str) -> str:
    """首頁摘要：第一個「一般段落」（非標題／引用／表格／清單／程式碼）全文去 markdown 記號，截 120 字。"""
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s or s.startswith(("#", ">", "|", "```", "-", "*", "<", "1.")):
            i += 1
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("#", ">", "|", "```")):
            buf.append(lines[i].strip())
            i += 1
        s = " ".join(buf)
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
        s = s.replace("**", "").replace("`", "")
        return s[:120] + ("…" if len(s) > 120 else "")
    return ""


def _collect(src: Path) -> List[Path]:
    files = sorted(src.glob("*.md")) + sorted((src / "Archived").glob("*.md"))
    return [p for p in files if p.is_file()]


def _rewrite_href(href: str, page: Path, src: Path, known: Dict[Path, Path]) -> Tuple[str, Optional[str]]:
    """回傳 (新 href, 死連結原因或 None)。只處理相對連結；站內 .md ⇒ .html。"""
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", href) or href.startswith("#") or href.startswith("/"):
        return href, None
    path_part, sep, frag = href.partition("#")
    unq = urllib.parse.unquote(path_part)
    # ../docs/<f> ⇒ ../<f>（site 在 docs/site；GitHub Pages 以 /docs 為根）；目標須真存在
    if unq.startswith("../docs/"):
        tail = unq[len("../docs/"):]
        exists = (REPO / "docs" / tail).exists()
        return "../" + urllib.parse.quote(tail, safe="/.-_~") + (sep + frag if sep else ""), (
            None if exists else f"docs 目標不存在: {href}"
        )
    target = (page.parent / unq).resolve() if unq else page.resolve()
    if unq and target in known:
        rel = Path(_relpath(known[target], known[page.resolve()].parent))
        return rel.as_posix() + (sep + frag if sep else ""), None
    if unq.endswith(".md"):
        # 站內找不到：可能已搬進 Archived/（既有死連結）；試著補救
        cand = src / "Archived" / Path(unq).name
        if cand.resolve() in known:
            rel = Path(_relpath(known[cand.resolve()], known[page.resolve()].parent))
            return rel.as_posix() + (sep + frag if sep else ""), None
        cand = src / Path(unq).name
        if cand.resolve() in known:
            rel = Path(_relpath(known[cand.resolve()], known[page.resolve()].parent))
            return rel.as_posix() + (sep + frag if sep else ""), None
        return href, f"站內 .md 不存在: {href}"
    return href, None


def _relpath(target: Path, base_dir: Path) -> str:
    import os

    return os.path.relpath(str(target), str(base_dir))


def _rel(p: Path) -> str:
    """顯示用相對路徑（out 在 repo 外時退回絕對路徑，不拋）。"""
    try:
        return p.relative_to(REPO).as_posix()
    except ValueError:
        return str(p)


def render_page(md_path: Path, src: Path, out: Path, known: Dict[Path, Path]) -> Tuple[str, List[str]]:
    """回傳 (html, 死連結清單)。"""
    text = md_path.read_text(encoding="utf-8")
    title = _title_of(text, md_path.stem)
    md = _md()
    dead: List[str] = []

    def render_link_open(self, tokens: List[Token], idx: int, options, env):
        tok = tokens[idx]
        href = tok.attrGet("href") or ""
        new, reason = _rewrite_href(href, md_path, src, known)
        if reason:
            dead.append(reason)
        tok.attrSet("href", new)
        return self.renderToken(tokens, idx, options, env)

    def render_heading_open(self, tokens: List[Token], idx: int, options, env):
        tok = tokens[idx]
        inline = tokens[idx + 1]
        plain = "".join(t.content for t in (inline.children or []) if t.type in ("text", "code_inline"))
        tok.attrSet("id", _slug(plain))
        return self.renderToken(tokens, idx, options, env)

    md.add_render_rule("link_open", render_link_open)
    md.add_render_rule("heading_open", render_heading_open)
    body = md.render(text)
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")

    depth = "../" if md_path.parent.name == "Archived" else ""
    crumb = "Archived ／ " if depth else ""
    rel_src = _rel(md_path)
    page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{depth}style.css">
</head>
<body>
<nav class="top"><a href="{depth}index.html">← 白話說明</a><span class="crumb">{crumb}{html.escape(md_path.name)}</span></nav>
<main>
{body}
<footer>由 <code>scripts/plain_docs_render.sh</code> 自 <code>{html.escape(rel_src)}</code> 生成；HTML 是產物，請改 .md。</footer>
</main>
</body>
</html>
"""
    return page, dead


def render_index(pages: List[Tuple[Path, str, str]], out: Path) -> str:
    """pages: (md_path, title, desc)。"""
    top = [p for p in pages if p[0].parent.name != "Archived"]
    arch = [p for p in pages if p[0].parent.name == "Archived"]

    def order_key(item):
        name = item[0].name
        return (INDEX_ORDER.index(name) if name in INDEX_ORDER else len(INDEX_ORDER), name)

    top.sort(key=order_key)
    arch.sort(key=lambda i: i[0].name)

    def li(item):
        p, title, desc = item
        href = (("Archived/" if p.parent.name == "Archived" else "") + p.stem + ".html")
        d = f'<span class="desc">{html.escape(desc)}</span>' if desc else ""
        return f'<li><a href="{html.escape(urllib.parse.quote(href, safe="/.-_~"))}">{html.escape(title)}</a><span class="desc">{html.escape(p.name)}</span>{d}</li>'

    body = ["<h1>白話說明</h1>", "<p>給使用者看的文件（來源為 repo 之 <code>白話說明/*.md</code>；本站由腳本生成）。</p>", "<h2>現行</h2>", '<ul class="index-list">']
    body += [li(i) for i in top]
    body += ["</ul>", "<h2>Archived（凍結歷史）</h2>", '<ul class="index-list">']
    body += [li(i) for i in arch]
    body += ["</ul>"]
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>白話說明</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<nav class="top"><span class="crumb">白話說明 ／ 首頁</span></nav>
<main>
{chr(10).join(body)}
<footer>由 <code>scripts/plain_docs_render.sh</code> 生成；HTML 是產物，請改 .md。</footer>
</main>
</body>
</html>
"""


def build(src: Path, out: Path) -> Tuple[Dict[Path, str], List[str]]:
    """回傳 ({輸出路徑: 內容}, 死連結清單)。純函式（不寫檔）。"""
    files = _collect(src)
    known: Dict[Path, Path] = {}
    for f in files:
        rel = f.relative_to(src).with_suffix(".html")
        known[f.resolve()] = (out / rel).resolve()
    outputs: Dict[Path, str] = {}
    dead_all: List[str] = []
    pages: List[Tuple[Path, str, str]] = []
    for f in files:
        page_html, dead = render_page(f, src, out, known)
        outputs[known[f.resolve()]] = page_html
        dead_all += [f"{_rel(f)}: {d}" for d in dead]
        text = f.read_text(encoding="utf-8")
        pages.append((f, _title_of(text, f.stem), _first_para(text)))
    outputs[(out / "index.html").resolve()] = render_index(pages, out)
    outputs[(out / "style.css").resolve()] = CSS
    return outputs, dead_all


def main(argv: Optional[List[str]] = None) -> int:
    global REPO
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只驗不寫；不一致 rc=1")
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--repo", default=str(REPO), help="repo 根（相對路徑顯示用；預設由腳本位置推導）")
    args = ap.parse_args(argv)
    REPO = Path(args.repo).resolve()
    src, out = Path(args.src).resolve(), Path(args.out).resolve()
    if not src.is_dir():
        print(f"ERROR: 來源目錄不存在: {src}", file=sys.stderr)
        return 2
    outputs, dead = build(src, out)

    if dead:
        for d in dead:
            print(f"[plain_docs_render] ✗ 死連結: {d}", file=sys.stderr)

    if args.check:
        bad = 0
        for path, content in outputs.items():
            if not path.is_file():
                print(f"[plain_docs_render] ✗ 缺產出: {_rel(path)}", file=sys.stderr)
                bad += 1
            elif path.read_text(encoding="utf-8") != content:
                print(f"[plain_docs_render] ✗ 產出過期: {_rel(path)}", file=sys.stderr)
                bad += 1
        # 多餘的 .html（來源已刪）亦報
        for stale in list(out.rglob("*.html")):
            if stale.resolve() not in outputs:
                print(f"[plain_docs_render] ✗ 多餘產出（來源已不存在）: {_rel(stale)}", file=sys.stderr)
                bad += 1
        if bad or dead:
            print(f"[plain_docs_render] CHECK FAIL: {bad} 檔不一致、{len(dead)} 條死連結（跑 bash scripts/plain_docs_render.sh 重生成）", file=sys.stderr)
            return 1
        print(f"[plain_docs_render] ✓ CHECK PASS: {len(outputs)} 檔與來源一致、0 死連結")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    (out / "Archived").mkdir(exist_ok=True)
    written = 0
    for path, content in outputs.items():
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
            written += 1
    for stale in list(out.rglob("*.html")):
        if stale.resolve() not in outputs:
            stale.unlink()
            print(f"[plain_docs_render] 移除多餘產出: {_rel(stale)}")
    print(f"[plain_docs_render] ✓ 生成 {len(outputs)} 檔（改寫 {written}）→ {_rel(out)}/；死連結 {len(dead)}")
    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())
