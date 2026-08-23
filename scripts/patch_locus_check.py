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
# 🔴 R17：同時接受 `@stage`（原形）與 `[@stage]`（方括號形），且**方括號形不要求前置空白**。
#   出處：R17 三家共 22 個 anchor 被判「非字面」——實因 brief 之格式行寫作
#   `- <檔>#<錨點>[@spec|@doc|@harness|@impl]`，方括號在該行是「可選」之標記，
#   委員合理地照字面寫成 `#錨點[@spec]`（無空白）⇒ 舊 regex 只吃 `\s*@stage$`
#   ⇒ `[@spec]` 被當成 anchor 的一部分 ⇒ **永遠 grep 不到＝假紅**（不是 fail-open）。
#   本次修正**只影響切分**，不改任何達成/未達成之判準：切出正確 anchor 後，
#   該 anchor 反而要接受完整比對（比假紅更嚴）。stage 集合為封閉四值，切分無歧義。
#   ⚠️ 原形之前置空白為 `\s*`（**零個也合法**，R9 起即如此，`ICAnalyzeRequest@impl` 靠此解析）
#      ——改成 `\s+` 會讓既有兩條回歸測試變紅（R17 落地時實際踩到），不得收窄。
_STAGE_SUFFIX = re.compile(
    r'(?:\s*\[\s*@(' + '|'.join(_STAGES) + r')\s*\]|\s*@(' + '|'.join(_STAGES) + r'))\s*$')


def _stage_of(match):
    """_STAGE_SUFFIX 有兩個互斥 group（方括號形／空白形），取有值者。"""
    return match.group(1) or match.group(2)


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
    """回傳 (loci, errors, body_text)；loci 為 [(檔案, 錨點or None, stage)]。

    🔴 **SYNC-LOCI 區段之終止條件為封閉集合**（CODEX-R11-P1-09）：
    首版遇到「非空、非合法 item」之行就靜默 `in_loci = False` ⇒
    `- a#X` / `MALFORMED` / `- b#Y` 這種內容只解析到第一條，**後面的 locus 整段消失**
    且 rc=0（實測 probe：`malformed_locus_ignored_rc=0`）。
    格式破壞會截斷驗證範圍，是本閘之**第四個自欺點**。
    ⇒ 只有 `_SECTION`（AUTHORITY/BEFORE-AFTER/VERIFY…）或 `#` 標題可終止該區段；
      其餘非空且非合法 item 之行一律 **parse error、fail-closed**。
    """
    loci, errors = [], []
    outside = []          # SYNC-LOCI 區段**以外**之正文（＝委員意圖之證據來源）
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
        if not in_loci:
            outside.append(line)
        if in_loci:
            if _SECTION.match(line) or line.startswith('#'):
                in_loci = False
                outside.append(line)
                continue
            m = _LOCI_ITEM.match(line)
            if m:
                f, anchor = m.group(1), m.group(2)
                stage = _DEFAULT_STAGE
                if anchor:
                    sm = _STAGE_SUFFIX.search(anchor)
                    if sm:
                        stage = _stage_of(sm)
                        anchor = _STAGE_SUFFIX.sub('', anchor).strip() or None
                else:
                    sm = _STAGE_SUFFIX.search(f)
                    if sm:
                        stage = _stage_of(sm)
                        f = _STAGE_SUFFIX.sub('', f).strip()
                loci.append((f, anchor, stage))
            elif line.strip() == '':          # 空行不終止區段（R11：只有 _SECTION／# 可終止）
                continue
            else:
                errors.append(
                    'SYNC-LOCI 內有非法行（既非 `- <檔>[#<anchor>][@stage]`、'
                    '亦非 AUTHORITY/BEFORE-AFTER/VERIFY 之區段起點）：%r'
                    '——格式破壞會截斷解析範圍，fail-closed' % line[:80])
                in_loci = False
    if not loci and 'SYNC-LOCI:' in text:
        errors.append('SYNC-LOCI 欄為空（空對空恆綠是假綠）')
    # 🔴 意圖證據**必須排除 SYNC-LOCI 區段本身**：該區段就寫著 anchor 字面，
    #   拿它當「委員說要動這個字面」等於自我證明，弱證據之補強會變成恆真（假綠）。
    return loci, errors, '\n'.join(outside)


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
    🔴 **R11**：此路徑之 anchor 比對屬**弱證據**（`diff_hunks` 回 `weak_full=True`），
      須另有補丁包正文之意圖佐證才算達成——否則零內容改動亦會通過。
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
    """回傳 `(added, removed, weak_full)`。

    · `added`／`removed`：該檔 diff 之 `+`／`-` 行內容（各自串接）。
    · `weak_full`：True 表示**無法取得 diff**（未追蹤／被 gitignore 之檔），
      退回「全檔內容當作新增」——**這是弱證據**（GROK-R11-P1-06）：
      該檔只要 mtime 比 HEAD 新就會被 `is_touched` 判為 touched，
      再把全檔當 hunk ⇒ **檔內既有字面在零內容改動下也會通過**。
    """
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
        # 🔴 只保留**新增／刪除行**，丟掉 hunk header，並**分開**回傳。
        #   病根（主委自查，R10）：`git diff -U0` 之 hunk header 形如
        #   `@@ -1,2 +1,2 @@ SECTION_UNTOUCHED`——git 會把它認定之「所屬區塊標題」
        #   （對 .md 常是前一個標題行）附在 `@@` 之後。若把整份 diff 當比對面，
        #   **未改動之標題文字會被當成「改到了」** ⇒ 同檔任一改動即可讓該標題下的
        #   所有 anchor 通過，正是 CODEX-R8-P1-06 要根除之「僅檔名相符」之變體。
        added = [l for l in body.split('\n')
                 if l.startswith('+') and not l.startswith('+++')]
        removed = [l for l in body.split('\n')
                   if l.startswith('-') and not l.startswith('---')]
        return '\n'.join(added), '\n'.join(removed), False
    # 未追蹤（新建）／被 gitignore 之檔：git diff 無輸出 ⇒ 全檔視為新增（**弱證據**）
    try:
        return io.open(path, encoding='utf-8', errors='replace').read(), '', True
    except IOError:
        return '', '', True


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
        loci, errors, patch_text = parse_patch(pf)
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
                # 🔴 CODEX-R8-P1-06：僅檔名相符不足，anchor 須出現在 diff hunk 內。
                #
                # 🔴 **R11：證據分強弱（COMPOSER-R11-P1-03／GROK-R11-P1-06）**
                #   強證據＝anchor 出現在**新增行**（`+`）。
                #   弱證據有二，R10 版對它們**無條件放行**，各是一個假綠：
                #     (1) anchor 只出現在**刪除行**——同檔刪掉一段**無關**文字若恰含該字面即通過；
                #     (2) `weak_full`（未追蹤／被 gitignore 之檔取不到 diff，退回全檔當新增）
                #         ——該檔只要 mtime 比 HEAD 新就被判 touched，**零內容改動亦通過**。
                #   ⇒ 弱證據改為**須另有委員意圖佐證**：該 anchor 亦須出現在**補丁包自身正文**
                #     （AUTHORITY／BEFORE-AFTER／VERIFY 任一處），即委員自己寫出要動這個字面。
                #     強證據不受影響 ⇒ 這是**收緊**，不是放寬。
                #   誠實邊界：委員若在 BEFORE/AFTER 抄了字面卻其實沒打算動，本閘看不見
                #   ——與 anchor 精確度同類，屬委員責任。
                added, removed, weak_full = diff_hunks(f, base)
                if anchor in added and not weak_full:
                    continue                      # 強證據
                weak_hit = (anchor in removed) or (weak_full and anchor in added)
                if weak_hit:
                    if anchor in patch_text:
                        continue                  # 弱證據 ＋ 委員意圖佐證
                    why = ('anchor 僅有弱證據（%s）而補丁包正文未提及該字面'
                           % ('全檔 fallback：無 diff 可取' if weak_full else '只出現在刪除行'))
                else:
                    # 🔴 anchor 字面閘（CODEX-R9-P1-06 ③／GROK-R9-P1-04 ③）：
                    #   分辨「該改而未改」與「anchor 根本不是字面（委員責任）」。
                    #   ⚠️ **R9 版判準錯誤**：只查「當前內容」⇒ 委員 anchor 若引用
                    #   **將被刪除**之舊文字，套用後必然找不到而被誤歸委員責任
                    #   （R10 十餘個 anchor 因此假紅）。刪除行之情形已由上方 weak_hit 承接。
                    cur = ''
                    if os.path.isfile(f):
                        try:
                            cur = io.open(f, encoding='utf-8', errors='replace').read()
                        except IOError:
                            cur = ''
                    if anchor in cur:
                        why = 'anchor 未出現在該檔之 diff hunk 內'
                    else:
                        why = ('anchor 非字面：當前內容與 diff hunk 皆找不到'
                               '（敘述型 anchor 不可用；須為可 grep 之字面）⇒ 委員責任')
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
