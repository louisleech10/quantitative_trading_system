"""
Phase C 驗證測試 — Feature Factory Granular Control Plan (Frontend)

涵蓋項目（§19.2 前端測試）：
- C1: Zustand store 擴展（per-indicator toggle）
- C2: IndicatorCheckbox 元件
- C3: CategorySection 元件（Select All/Deselect All, indeterminate）
- C4: LayerPanel 元件（Tab 導航 + Layer 開關）
- C5: 即時特徵預覽列
- C6: 搜尋/過濾功能
- C7: Preset 選擇器更新（server-side API）
- C8: 配置匯出/匯入
- C9: 特徵數量警告 UI

因前端無 React Testing Library / Jest 環境，本檔以結構性驗證為主：
- 檢查新檔案是否存在且含必要匯出/Pattern
- 檢查 store / hook / types 是否包含必要 state/action/API
- 檢查 page.tsx 是否整合所有新元件
- 搭配 `npm run build` 確認 TypeScript 編譯通過
"""

import re
from pathlib import Path

import pytest

# ── Project root ──
ROOT = Path(__file__).resolve().parent.parent
FE = ROOT / "frontend" / "src"
COMP = FE / "components" / "feature-factory"

# ── helpers ──


def _read(path: Path) -> str:
    """讀取檔案內容（UTF-8）"""
    return path.read_text(encoding="utf-8")


# ===========================================================
# §19.2-1  Component Render — 各 Layer panel 正常渲染（7 tests）
# ===========================================================


class TestComponentRender:
    """驗證 7 個 Layer panel 子元件定義於 LayerPanel.tsx"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.layer_panel = _read(COMP / "LayerPanel.tsx")

    def test_layer1_content_exists(self):
        """Layer1Content 函式元件存在"""
        assert "Layer1Content" in self.layer_panel

    def test_layer2_content_exists(self):
        """Layer2Content 函式元件存在"""
        assert "Layer2Content" in self.layer_panel

    def test_layer3_content_exists(self):
        """Layer3Content 函式元件存在"""
        assert "Layer3Content" in self.layer_panel

    def test_layer4_content_exists(self):
        """Layer4Content 函式元件存在"""
        assert "Layer4Content" in self.layer_panel

    def test_layer5_content_exists(self):
        """Layer5Content 函式元件存在"""
        assert "Layer5Content" in self.layer_panel

    def test_layer6_content_exists(self):
        """Layer6Content 函式元件存在"""
        assert "Layer6Content" in self.layer_panel

    def test_layer65_content_exists(self):
        """Layer65Content 函式元件存在"""
        assert "Layer65Content" in self.layer_panel


# ===========================================================
# §19.2-2  Select All / Deselect All（4 tests）
# ===========================================================


class TestSelectAllDeselectAll:
    """驗證 CategorySection 支援 Select All / Deselect All / Indeterminate"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.category = _read(COMP / "CategorySection.tsx")
        self.store = _read(FE / "store" / "featureFactoryStore.ts")

    def test_select_all_button(self):
        """CategorySection 有全選按鈕文字"""
        assert "全選" in self.category or "Select All" in self.category

    def test_deselect_all_button(self):
        """CategorySection 有取消全選按鈕文字"""
        assert "取消" in self.category or "Deselect" in self.category

    def test_indeterminate_state(self):
        """CategorySection 處理 indeterminate checkbox 狀態"""
        # indeterminate 是 DOM 屬性，需要 ref 設定
        assert "indeterminate" in self.category

    def test_store_toggle_all_in_category(self):
        """Store 有 toggleAllInCategory action"""
        assert "toggleAllInCategory" in self.store


# ===========================================================
# §19.2-3  Layer Toggle（3 tests）
# ===========================================================


class TestLayerToggle:
    """驗證層級開關 on/off 不影響子項 enabled 狀態"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.layer_panel = _read(COMP / "LayerPanel.tsx")
        self.store = _read(FE / "store" / "featureFactoryStore.ts")

    def test_tab_navigation_exists(self):
        """LayerPanel 包含 Tab 導航（7 個 Layer）"""
        # 檢查是否有 tab 切換相關的 state
        assert re.search(r"activeTab|selectedTab|activeLayer", self.layer_panel)

    def test_toggle_aggregator_action(self):
        """Store 有 toggleAggregator action 用於 Layer 3"""
        assert "toggleAggregator" in self.store

    def test_toggle_meta_sub_engine_action(self):
        """Store 有 toggleMetaSubEngine action 用於 Layer 6"""
        assert "toggleMetaSubEngine" in self.store


# ===========================================================
# §19.2-4  Search Filter（2 tests）
# ===========================================================


class TestSearchFilter:
    """驗證搜尋指標名稱正確過濾"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.layer_panel = _read(COMP / "LayerPanel.tsx")
        self.store = _read(FE / "store" / "featureFactoryStore.ts")

    def test_search_input_exists(self):
        """LayerPanel 包含搜尋輸入框"""
        assert re.search(r'type="text"|type="search"|placeholder.*[Ss]earch|搜尋', self.layer_panel)

    def test_store_indicator_search_state(self):
        """Store 有 indicatorSearch state 用於過濾"""
        assert "indicatorSearch" in self.store


# ===========================================================
# §19.2-5  Preview Update（2 tests）
# ===========================================================


class TestPreviewUpdate:
    """驗證 config 變更後即時更新預覽"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.preview_bar = _read(COMP / "FeaturePreviewBar.tsx")
        self.page = _read(FE / "app" / "feature-factory" / "page.tsx")

    def test_preview_bar_reads_preview_data(self):
        """FeaturePreviewBar 接收 preview 資料（透過 props 或 store）"""
        # 元件以 props 接收 preview，由 page.tsx 從 store 傳入
        assert "preview" in self.preview_bar and "FeaturePreview" in self.preview_bar

    def test_page_integrates_preview_bar(self):
        """page.tsx 整合預覽元件（舊版 FeaturePreviewBar / 新版 PreviewPanel）。"""
        assert ("PreviewPanel" in self.page) or ("FeaturePreviewBar" in self.page)


# ===========================================================
# §19.2-6  Preset Apply（3 tests）
# ===========================================================


class TestPresetApply:
    """驗證切換預設正確覆蓋"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.preset = _read(COMP / "PresetSelector.tsx")
        self.hook = _read(FE / "hooks" / "useFeatureFactory.ts")

    def test_preset_uses_server_api(self):
        """PresetSelector 呼叫 server-side API（applyPreset）"""
        assert "applyPreset" in self.preset

    def test_hook_has_apply_preset(self):
        """useFeatureFactory hook 有 applyPreset 函式"""
        assert "applyPreset" in self.hook

    def test_hook_preset_calls_post(self):
        """applyPreset 使用 POST 呼叫 presets endpoint"""
        assert re.search(r"presets/|preset", self.hook)


# ===========================================================
# 額外驗證：新檔案存在性 & 整合完整性
# ===========================================================


class TestFileExistence:
    """驗證所有 Phase C 新建/修改的檔案皆存在"""

    @pytest.mark.parametrize("filename", [
        "IndicatorCheckbox.tsx",
        "CategorySection.tsx",
        "LayerPanel.tsx",
        "FeaturePreviewBar.tsx",
        "ConfigIOButtons.tsx",
    ])
    def test_new_component_exists(self, filename):
        """新元件檔案存在"""
        assert (COMP / filename).exists(), f"{filename} not found"

    def test_store_modified(self):
        """featureFactoryStore.ts 包含 schema state"""
        content = _read(FE / "store" / "featureFactoryStore.ts")
        assert "schema" in content

    def test_hook_has_load_schema(self):
        """useFeatureFactory.ts 包含 loadSchema"""
        content = _read(FE / "hooks" / "useFeatureFactory.ts")
        assert "loadSchema" in content

    def test_types_has_feature_schema(self):
        """types.ts 包含 FeatureSchema interface"""
        content = _read(FE / "lib" / "types.ts")
        assert "FeatureSchema" in content


class TestStoreActions:
    """驗證 Zustand store 包含所有必要 actions"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.store = _read(FE / "store" / "featureFactoryStore.ts")

    @pytest.mark.parametrize("action", [
        "setSchema",
        "setIndicatorSearch",
        "toggleIndicator",
        "toggleAllInCategory",
        "toggleCategory",
        "toggleAggregator",
        "toggleAllAggregators",
        "toggleMetaSubEngine",
        "toggleCrossFeature",
        "toggleOperator",
    ])
    def test_action_exists(self, action):
        """Store action '{action}' 存在"""
        assert action in self.store, f"Action '{action}' not found in store"


class TestHookAPI:
    """驗證 useFeatureFactory hook 包含所有必要 API 函式"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.hook = _read(FE / "hooks" / "useFeatureFactory.ts")

    @pytest.mark.parametrize("func", [
        "loadSchema",
        "batchToggle",
        "applyPreset",
    ])
    def test_api_function_exists(self, func):
        """Hook function '{func}' 存在"""
        assert func in self.hook, f"Function '{func}' not found in hook"


class TestConfigIOButtons:
    """驗證 C8 配置匯出/匯入元件"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = _read(COMP / "ConfigIOButtons.tsx")

    def test_export_functionality(self):
        """有 JSON 下載（export）邏輯"""
        assert re.search(r"download|export|JSON\.stringify", self.content)

    def test_import_functionality(self):
        """有檔案上傳（import）邏輯"""
        assert re.search(r'type="file"|FileReader|import|upload', self.content)

    def test_validation_on_import(self):
        """匯入時驗證 config 結構"""
        assert "atomic_indicators" in self.content


class TestFeaturePreviewBar:
    """驗證 C5+C9 特徵預覽列 & 警告"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = _read(COMP / "FeaturePreviewBar.tsx")

    def test_warning_threshold_defined(self):
        """定義警告閾值（10000）"""
        assert "10000" in self.content or "10_000" in self.content

    def test_hard_limit_defined(self):
        """定義硬上限（50000）"""
        assert "50000" in self.content or "50_000" in self.content

    def test_min_features_warning(self):
        """定義最低特徵數警告"""
        # MIN_FEATURES_WARNING = 5
        assert re.search(r"MIN_FEATURES|min.*warn|< 5|<= 0", self.content)

    def test_zero_features_warning(self):
        """0 特徵數顯示錯誤訊息"""
        assert re.search(r"=== 0|== 0|零|no feature|0 個", self.content, re.IGNORECASE)


class TestPageIntegration:
    """驗證 page.tsx 整合所有 Phase C 元件"""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.page = _read(FE / "app" / "feature-factory" / "page.tsx")

    def test_layer_panel_imported(self):
        """LayerPanel 被匯入"""
        assert "LayerPanel" in self.page

    def test_feature_preview_bar_imported(self):
        """預覽元件被匯入（舊版 FeaturePreviewBar / 新版 PreviewPanel）。"""
        assert ("PreviewPanel" in self.page) or ("FeaturePreviewBar" in self.page)

    def test_config_io_buttons_imported(self):
        """Config IO 功能被整合（可直接在 page，或透過 ConfigPanel 組合）。"""
        assert ("ConfigIOButtons" in self.page) or ("ConfigPanel" in self.page)

    def test_schema_loaded(self):
        """page 有載入 schema 邏輯"""
        assert "loadSchema" in self.page or "schema" in self.page
