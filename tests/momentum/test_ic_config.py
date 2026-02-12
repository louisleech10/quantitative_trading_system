import yaml
import pytest

from momentum.Analysis.ic_config_schema import ICConfig, load_ic_config


def test_load_ic_config_defaults():
    """測試預設設定可正確載入。"""
    config = load_ic_config()
    assert isinstance(config, ICConfig)
    assert config.global_settings.default_method == "spearman"
    assert config.thresholds.icir_min == 0.5


def test_load_ic_config_merge(tmp_path):
    """測試三層設定合併順序。"""
    default_config = {
        "version": "1.0",
        "global": {"default_method": "spearman"},
        "thresholds": {"icir_min": 0.5},
    }
    user_config = {
        "global": {"default_method": "kendall"},
        "thresholds": {"icir_min": 0.6},
    }

    default_path = tmp_path / "ic_config.yaml"
    user_path = tmp_path / "user_ic_config.yaml"

    default_path.write_text(yaml.safe_dump(default_config), encoding="utf-8")
    user_path.write_text(yaml.safe_dump(user_config), encoding="utf-8")

    config = load_ic_config(
        default_path=str(default_path),
        user_path=str(user_path),
        api_override={"thresholds": {"icir_min": 0.9}},
    )

    assert config.global_settings.default_method == "kendall"
    assert config.thresholds.icir_min == 0.9


def test_read_yaml_missing_required(tmp_path):
    """缺少預設設定時應拋出錯誤。"""
    default_path = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError):
        load_ic_config(default_path=str(default_path))


def test_read_yaml_invalid_format(tmp_path):
    """非 mapping 應拋出錯誤。"""
    default_path = tmp_path / "ic_config.yaml"
    default_path.write_text("- invalid", encoding="utf-8")

    with pytest.raises(ValueError):
        load_ic_config(default_path=str(default_path), user_path=str(default_path))


def test_load_ic_config_rejects_invalid_override(tmp_path):
    """api_override 非 dict 時應拋出錯誤。"""
    default_path = tmp_path / "ic_config.yaml"
    default_path.write_text("version: '1.0'", encoding="utf-8")

    with pytest.raises(ValueError):
        load_ic_config(default_path=str(default_path), api_override="bad")


def test_load_ic_config_missing_user_file(tmp_path):
    """缺少 user config 時應回空 dict 合併。"""
    default_path = tmp_path / "ic_config.yaml"
    default_path.write_text("version: '1.0'\nthresholds:\n  icir_min: 0.5", encoding="utf-8")

    config = load_ic_config(default_path=str(default_path), user_path=str(tmp_path / "missing.yaml"))

    assert config.thresholds.icir_min == 0.5
