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
    python3 scripts/patch_locus_check.py <patch.md> [...] [--diff-base <ref>] [--also-impl]

不給 --diff-base 時，比對「工作區相對 HEAD」之改動（含 staged 與 unstaged）。
🔴 **commit 之後複驗必須帶 `--diff-base <套用前 ref>`**（GROK-R9-P1-04 ④）：
   對乾淨 worktree 跑無 base 之檢查，會把**已落地**之 locus 誤報為「檔案未被本次改動」
   ——那是方法論假紅，與 stage／quotepath 是三件不同的事，勿混為一談。

SYNC-LOCI 每列可加 stage 後綴 `@spec`／`@doc`／`@harness`／`@impl`（**缺省＝`@spec`**）。
未達之 `@impl` 列為 DEFERRED、不計 rc；`--also-impl` 使其亦計入（**只加寬，不縮窄**）。

rc: 0=diff 覆蓋全部非 DEFERRED 之 SYNC-LOCI；2=有 locus 未被觸及（或補丁包格式不合）

🔴 **2026-08-23 強度訂正（CODEX-R8-P1-06）**：首版只以「dirty worktree 之**檔名**集合」
判定 locus ⇒ 同檔之**無關修改**、或該檔本來就 dirty，即可被誤算為「補丁已套用」。
主委當時在 HANDOFF 與角色卡以「diff 觸及集合 ⊇ SYNC-LOCI」描述其強度，
**該描述高於實際能力**。現改為驗到 **anchor 層級**：
locus 帶 `#anchor` 者，該 anchor 之字面必須出現在**該檔之 diff hunk 內容**中
（新增或刪除行皆算），僅檔名相符不足。

🔴 誠實邊界（不得誇大）：
  1. 本閘只驗「宣告的 locus 有沒有被真的改到」。**委員漏列的 locus，本閘看不見**
     ——那要靠 review 輪抓，且算委員責任。
  2. anchor 比對是**字面比對**：anchor 若寫得太籠統（如 `#main`），
     同檔任何含該字串之改動都會通過 ⇒ **anchor 之精確度是委員的責任**。
  3. 不驗「改得對不對」，只驗「有沒有改到那裡」。
  4. 「選哪個技術修法正確」「使用者 label 語意是否正確」「未被列出的隱藏複述」
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

# 🔴 R9（CODEX-R9-P1-06 ＋ GROK-R9-P1-04；三家議題一裁定）：stage 維度。
#
# 病根：R8 之補丁包把「SPEC 段落」與「實作階段才會動到的程式檔」混列在同一份 SYNC-LOCI。
#   epic 在規格階段，那些程式檔現在不該動 ⇒ locus 閘必紅，且無法區分
#   「合法的凍前狀態」與「主委漏套」。
#
# 三家裁定（brief 議題一）：**stage 是補丁包自我宣告的責任資料，不是呼叫端的降噪開關**。
#   ⇒ 呼叫端**只能加寬**（`--also-impl`），**不得**有「只檢查某 subset」之旗標。
#
# 兩份補丁包互斥，主委裁決採 GROK 版（逐 locus 後綴）：
#   · CODEX `-locus-stage.md`：`STAGE:` header，每包單一 stage，impl loci 另立包。
#   · GROK  `-locus-stage-quotepath.md`：逐 locus `@stage` 後綴，缺省 `@spec`。
#   採後者之理由：一次改動本就同時觸及 SPEC 文字、白話說明與治理腳本（不同 stage
#   但同一件事），強制「每包單一 stage」會逼委員把一個群集拆成三包，反而增加漏列面；
#   逐 locus 後綴之預設值是 `@spec`（最嚴），未標註者行為與 R8 完全相同 ⇒ 不放寬。
_STAGES = ('spec', 'doc', 'harness', 'impl')
_DEFAULT_STAGE = 'spec'
_STAGE_SUFFIX = re.compile(r'\s*@(' + '|'.join(_STAGES) + r')\s*$')


def _git(*args):
    """git 呼叫統一入口。

    🔴 **必加 `-c core.quotepath=false`**（GROK-R9-P1-04，實測）：預設 `quotepath=true`
    時，非 ASCII 路徑會被輸出成 `"\\347\\231\\275\\350\\251\\261..."` 八進位字面，
    與 SYNC-LOCI 之 UTF-8 路徑**永不相等** ⇒ `白話說明/…` 這類檔即使已改也報
    「檔案未被本次改動」。此為機械閘之**假紅**，與 R8 之輸出截斷、pipefail 假綠同型。
    """
    return subprocess.run(['git', '-c', 'core.quotepath=false'] + list(args),
                          capture_output=True, text=True)


def parse_patch(path):
    """回傳 (loci, errors)；loci 為 [(檔案, 錨點or None, stage)]。"""
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
                f, anchor = m.group(1), m.group(2)
                stage = _DEFAULT_STAGE
                if anchor:
                    sm = _STAGE_SUFFIX.search(anchor)
                    if sm:
                        stage = sm.group(1)
                        anchor = _STAGE_SUFFIX.sub('', anchor).strip() or None
                else:
                    sm = _STAGE_SUFFIX.search(f)
                    if sm:
                        stage = sm.group(1)
                        f = _STAGE_SUFFIX.sub('', f).strip()
                # 🔴 anchor 格式閘（三家一致；CODEX-R9-P1-06 ③、GROK-R9-P1-04 ③）：
                #   anchor 必須是**該檔當前內容可字面找到**之字串。
                #   R8 有五個 anchor 寫成敘述（`檔頭 A-6／FROZEN 句`／`§A-A-6`／`§G-G-2`…），
                #   這些字串在檔內根本不存在 ⇒ 實質內容改完了、閘仍紅，且紅得沒有資訊。
                #   ⇒ 提交當下就 fail-closed（委員責任），不等到 diff 對證。
                #   誠實邊界：本閘不驗 anchor 是否**精確指到該改的段落**，只驗它存在。
                if anchor and os.path.isfile(f):
                    try:
                        cur = io.open(f, encoding='utf-8', errors='replace').read()
                    except IOError:
                        cur = ''
                    if anchor not in cur:
                        errors.append(
                            'anchor 非字面：`%s#%s` 在該檔當前內容中找不到'
                            '（敘述型 anchor 不可用；須為可 grep 之字面）' % (f, anchor))
                loci.append((f, anchor, stage))
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
        out = _git('diff', '--name-only', base)
        if out.returncode != 0:
            return None
        names |= {l.strip() for l in out.stdout.splitlines() if l.strip()}
    st = _git('status', '--porcelain', '-z', '-uall')
    if st.returncode != 0:
        return None
    for rec in st.stdout.split('\0'):
        if len(rec) > 3:
            names.add(rec[3:].strip())
    return names


def _head_time():
    out = _git('log', '-1', '--format=%ct')
    if out.returncode != 0 or not out.stdout.strip():
        return None
    return int(out.stdout.strip())


def is_touched(path, touched, head_ts):
    """該 locus 檔本次有無被改動。

    🔴 **gitignore 之盲區（2026-08-23 主委反測發現）**：本 repo 之 `handoffs/*` 列在
    `.git/info/exclude` ⇒ `git status --porcelain -uall` **不列 ignored 檔**
    （`-uall` 只含 untracked，不含 ignored）。補丁包若把 `handoffs/*-facts.sh`
    列為 locus，會被誤判「未改動」——與首版之 untracked 盲區同型，是**第二個** fail-open。
    ⇒ git 看不見者，退回**檔案 mtime 對 HEAD commit 時間**之比較：
      mtime > HEAD 之 commit 時間 ⇒ 視為本次改動。
    誠實邊界：mtime 可被 `touch` 偽造，且同一 commit 週期內之舊改動也會算進來
    ——這是 gitignore 檔的先天限制，不宣稱與 tracked 檔同強度。
    """
    if path in touched:
        return True
    if head_ts is None:
        return False
    try:
        return os.path.getmtime(path) > head_ts
    except OSError:
        return False


def diff_hunks(path, base):
    """回傳該檔之 diff hunk 內容（含新增與刪除行）。未追蹤檔 ⇒ 回全檔內容。"""
    cmds = []
    if base:
        cmds.append(['diff', '-U0', base, '--', path])
    cmds.append(['diff', '-U0', 'HEAD', '--', path])
    cmds.append(['diff', '-U0', '--cached', '--', path])
    body = ''
    for c in cmds:
        out = _git(*c)
        if out.returncode == 0:
            body += out.stdout
    if body.strip():
        return body
    # 未追蹤（新建）檔：git diff 無輸出 ⇒ 全檔視為新增
    try:
        return io.open(path, encoding='utf-8', errors='replace').read()
    except IOError:
        return ''


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
    also_impl = '--also-impl' in args
    args = [a for a in args if a != '--also-impl']
    patches = args
    if not patches:
        print(__doc__.rsplit('用法：', 1)[-1], file=sys.stderr)
        return 0

    touched = changed_files(base)
    if touched is None:
        print('ERROR: git diff 失敗（fail-closed）', file=sys.stderr)
        return 2
    head_ts = _head_time()

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
        deferred = []
        for f, anchor, stage in loci:
            why = None
            if not is_touched(f, touched, head_ts):
                why = '檔案未被本次改動'
            elif anchor:
                # 🔴 CODEX-R8-P1-06：僅檔名相符不足，anchor 須出現在 diff hunk 內
                body = diff_hunks(f, base)
                if anchor not in body:
                    why = 'anchor 未出現在該檔之 diff hunk 內'
            if why is None:
                continue
            # 🔴 stage=impl 之未達 locus：預設列為 DEFERRED、不計 rc
            #    （三家裁定：stage 由補丁包宣告；呼叫端只可用 --also-impl **加寬**）。
            #    誠實邊界：委員若把 spec locus 誤標 @impl，本閘看不見 ⇒ 屬 anchor 精確度
            #    同類之委員責任，保留獨立審查（角色卡「做不成機械閘者」第三項）。
            if stage == 'impl' and not also_impl:
                deferred.append((f, anchor, why))
            else:
                missing.append((f, anchor, stage, why))
        if missing:
            rc = 2
            print('[patch_locus_check] 🔴 %s：以下 SYNC-LOCI 未被本次改動涵蓋' % pf,
                  file=sys.stderr)
            for f, a, stage, why in missing:
                print('    · %s%s  [@%s]  ← %s' % (f, ('#' + a) if a else '', stage, why),
                      file=sys.stderr)
        if deferred:
            print('[patch_locus_check] ⏳ %s：以下 locus 標 @impl，凍前不套用（DEFERRED，不計 rc）'
                  % pf)
            for f, a, why in deferred:
                print('    · %s%s  ← %s' % (f, ('#' + a) if a else '', why))
            print('    （實作階段驗收請加 --also-impl；本旗標只加寬、不縮窄）')
        if not missing and loci and not errors:
            print('[patch_locus_check] ✓ %s：%d 個 locus 全部被改到（含 anchor 比對）%s'
                  % (pf, len(loci) - len(deferred),
                     ('；另 %d 個 @impl DEFERRED' % len(deferred)) if deferred else ''))
    if rc:
        print('\n  規則：主委 commit 之 diff 觸及集合須 ⊇ 補丁包之 SYNC-LOCI。',
              file=sys.stderr)
        print('  漏列 locus ⇒ 補丁包紅（委員責任），不算主委自傷；',
              file=sys.stderr)
        print('  已列而未改 ⇒ 主委套用不完整，補改後重跑。', file=sys.stderr)
    return rc


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
