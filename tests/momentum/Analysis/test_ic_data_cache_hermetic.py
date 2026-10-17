"""撤除 redirect 時 digest canary 必能偵測 sacrificial production write。"""

from __future__ import annotations

from pathlib import Path

import pytest

import tests.fixtures.ic_persist_redirect as redirect
from momentum.Analysis.ic_reporter import ICReporter
from tests.fixtures.ic_persist_redirect import RedirectPatchSet


def test_mutation_redirect_disabled_caught(
    redirect_patch_set: RedirectPatchSet,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """以假 production 根（tmp 下之 work/data_cache）跑 digest canary：

    1. redirect 啟用時，經真生產接點 ``ICReporter.save_report``（S2 wrapper）與 ``_redirect_path``
       之寫入全落在 redirect root，``digest_data_cache`` 前後不變（hermetic）；
    2. 撤除 redirect（``IC_PERSIST_REDIRECT_DISABLE=1``，即 mutation）後同樣之寫入落到 production，
       ``digest_data_cache`` 必偵測到新增之兩檔——證明 canary 會抓到 sacrificial production write。
    """
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    fake_production = (work / "data_cache").resolve()
    # session 範圍 patch set 之 production_prefix 以 monkeypatch 改（測後還原，不污染後續測試）
    monkeypatch.setattr(redirect_patch_set, "production_prefix", fake_production)
    # digest_data_cache 掃 _repo_root()/data_cache；指到 work ⇒ 掃的正是假 production
    monkeypatch.setattr(redirect, "_repo_root", lambda: work)
    reporter = ICReporter({"ai_summary": False})
    report_dir = fake_production / "reports" / "canary"

    digest_before = redirect.digest_data_cache()
    assert digest_before == {}
    ctx = redirect_patch_set.activate(tmp_path / "redirect", owner="hermetic-mutation")
    try:
        production_path = fake_production / "features/canary.txt"
        redirected = redirect._redirect_path(production_path)
        assert redirected.resolve().is_relative_to(ctx.redirect_root)
        redirected.parent.mkdir(parents=True, exist_ok=True)
        redirected.write_text("canary", encoding="utf-8")
        saved = reporter.save_report({}, str(report_dir), "canary")
        assert Path(saved["json"]).resolve().is_relative_to(ctx.redirect_root)
        assert redirect.digest_data_cache() == digest_before, "redirect 啟用時 production 不得有任何寫入"
        assert not ctx.spy.violations

        monkeypatch.setenv("IC_PERSIST_REDIRECT_DISABLE", "1")
        mutated = redirect._redirect_path(production_path)
        mutated.parent.mkdir(parents=True, exist_ok=True)
        mutated.write_text("canary", encoding="utf-8")
        assert mutated.resolve().is_relative_to(work)
        assert not mutated.resolve().is_relative_to(ctx.redirect_root)
        leaked = reporter.save_report({}, str(report_dir), "canary")
        assert Path(leaked["json"]).resolve().is_relative_to(fake_production)

        digest_after = redirect.digest_data_cache()
        new_files = set(digest_after) - set(digest_before)
        assert new_files == {"features/canary.txt", "reports/canary/ic_report_canary.json"}, (
            f"digest canary 未偵測到撤除 redirect 後之 production 寫入：{sorted(new_files)}"
        )
    finally:
        monkeypatch.delenv("IC_PERSIST_REDIRECT_DISABLE", raising=False)
        redirect_patch_set.deactivate(ctx)
    print("MUTATION_CANARY=1")
