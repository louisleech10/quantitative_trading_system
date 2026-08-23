# -*- coding: utf-8 -*-
"""補丁包 locus 對證（PATCH-LOCUS，2026-08-23）。

出處＝R3 consult 三家共識（GROK-R3-P1-03／CODEX-R3-P1-02／CODEX-R3-P1-01）。

病根（量化事實）：GAP-3 UAT 缺口 SPEC 七輪對抗審，主委自傷 21 條，
其中約 **14 條**同一形態——**改了某處之權威定義，未同步所有複述它的位置**。
R5 起改由委員逐條指定修法、主委照抄，技術決策因此零錯誤，
但**錯誤轉移到整合**：主委把三家規格縫進一份 1580 行文件時，
產生誰都沒指定過的新交叉引用（計數字面／禁令互斥／登記義務）。

⇒ 三家裁定之新流程：**委員產出【補丁包】**（唯一允許的整合輸入），
主委**整包套用、禁自寫第二處複述**。本閘即該流程之機械對證：

    主委 commit 之 diff 觸及集合  ⊇  補丁包宣告之 SYNC-LOCI

漏列 locus ⇒ **補丁包紅**（算委員責任），**不算主委自傷**——
這條歸屬很重要：它把「整合正確性」從主委的注意力移到結構上。

補丁包格式（`handoffs/patches/*.md`）：

    # PATCH cluster <名>
    AUTHORITY: <哪一處是權威定義>
    SYNC-LOCI:
    - <檔>#<錨點>
    - <檔>#<錨點>
    BEFORE/AFTER: <可直接套用之替換或 diff>
    VERIFY:
    - <命令>

用法：
    python3 scripts/patch_locus_check.py <patch.md> [<patch.md> ...] [--diff-base <git-ref>]

不給 --diff-base 時，比對「工作區相對 HEAD」之改動（含 staged 與 unstaged）。
rc: 0=diff 覆蓋全部 SYNC-LOCI；2=有 locus 未被觸及（或補丁包格式不合）

🔴 誠實邊界（三家明列，不得誇大）：
  1. 本閘只驗「宣告的 locus 有沒有被碰到」。**委員漏列的 locus，本閘看不見**
     ——那要靠 review 輪抓，且算委員責任。
  2. 只驗「檔案有被改」與「錨點行仍存在／已變動」，**不驗改得對不對**。
  3. 「選哪個技術修法正確」「使用者 label 語意是否正確」「未被列出的隱藏複述」
     ——三家明說**做不成機械閘**，保留獨立委員與使用者裁定。
"""

import io
import os
import re
import subprocess
import sys

_LOCI_START = re.compile(r'^SYNC-LOCI:\s*$')
_LOCI_ITEM = re.compile(r'^\s*-\s+(\S+?)(?:#(.+))?\s*$')
_SECTION = re.compile(r'^(AUTHORITY|BEFORE/AFTER|VERIFY|BEFORE|AFTER)\s*:')


def parse_patch(path):
    """回傳 (loci, errors)；loci 為 [(檔案, 錨點or None)]。"""
    loci, errors = [], []
    text = io.open(path, encoding='utf-8').read()
    if 'AUTHORITY:' not in text:
        errors.append('缺 AUTHORITY 欄')
    if 'SYNC-LOCI:' not in text:
        errors.append('缺 SYNC-LOCI 欄')
    if 'VERIFY:' not in text:
        errors.append('缺 VERIFY 欄')
    in_loci = False
    for line in text.splitlines():
        if _LOCI_START.match(line):
            in_loci = True
            continue
        if in_loci:
            if _SECTION.match(line) or line.startswith('#'):
                in_loci = False
                continue
            m = _LOCI_ITEM.match(line)
            if m:
                loci.append((m.group(1), m.group(2)))
            elif line.strip() == '':
                continue
            else:
                in_loci = False
    if not loci and 'SYNC-LOCI:' in text:
        errors.append('SYNC-LOCI 欄為空（空對空恆綠是假綠）')
    return loci, errors


def changed_files(base):
    """本次改動之檔案集合。

    🔴 **必含未追蹤檔**：`git diff HEAD --name-only` **不列 untracked**
    ⇒ 補丁包若把「新建檔」列為 locus，會被誤判為「未觸及」（fail-open）。
    主委自製本閘後立即以反測發現此洞（新建 `scripts/gap3ux_pre_review.sh` 被判未觸及）。
    此坑與 `gen_fact_key_blocks.sh` 之「列舉器必含未追蹤檔」同型（該處已載於檔頭）。
    ⇒ 指定 base 時用 `git diff <base> --name-only` 加 untracked；
       未指定時一律走 `git status --porcelain`（涵蓋 staged／unstaged／untracked）。
    """
    names = set()
    if base:
        out = subprocess.run(['git', 'diff', '--name-only', base],
                             capture_output=True, text=True)
        if out.returncode != 0:
            return None
        names |= {l.strip() for l in out.stdout.splitlines() if l.strip()}
    st = subprocess.run(['git', 'status', '--porcelain', '-z', '-uall'],
                        capture_output=True, text=True)
    if st.returncode != 0:
        return None
    for rec in st.stdout.split('\0'):
        if len(rec) > 3:
            names.add(rec[3:].strip())
    return names


def main(argv):
    args = [a for a in argv[1:] if a]
    base = None
    if '--diff-base' in args:
        i = args.index('--diff-base')
        if i + 1 >= len(args):
            print('ERROR: --diff-base 後須接 git ref', file=sys.stderr)
            return 2
        base = args[i + 1]
        args = args[:i] + args[i + 2:]
    patches = args
    if not patches:
        print(__doc__.rsplit('用法：', 1)[-1], file=sys.stderr)
        return 0

    touched = changed_files(base)
    if touched is None:
        print('ERROR: git diff 失敗（fail-closed）', file=sys.stderr)
        return 2

    rc = 0
    for pf in patches:
        if not os.path.isfile(pf):
            print('ERROR: 補丁包不存在：%s（fail-closed）' % pf, file=sys.stderr)
            rc = 2
            continue
        loci, errors = parse_patch(pf)
        for e in errors:
            print('[patch_locus_check] 🔴 %s：%s' % (pf, e), file=sys.stderr)
            rc = 2
        missing = []
        for f, anchor in loci:
            if f not in touched:
                missing.append((f, anchor))
        if missing:
            rc = 2
            print('[patch_locus_check] 🔴 %s：以下 SYNC-LOCI 未被本次 diff 觸及' % pf,
                  file=sys.stderr)
            for f, a in missing:
                print('    · %s%s' % (f, ('#' + a) if a else ''), file=sys.stderr)
        elif loci and not errors:
            print('[patch_locus_check] ✓ %s：%d 個 locus 全部被觸及' % (pf, len(loci)))
    if rc:
        print('\n  規則：主委 commit 之 diff 觸及集合須 ⊇ 補丁包之 SYNC-LOCI。',
              file=sys.stderr)
        print('  漏列 locus ⇒ 補丁包紅（委員責任），不算主委自傷；',
              file=sys.stderr)
        print('  已列而未改 ⇒ 主委套用不完整，補改後重跑。', file=sys.stderr)
    return rc


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
