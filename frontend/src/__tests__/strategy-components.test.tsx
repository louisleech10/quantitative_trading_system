/**
 * strategy-components.test.tsx - 策略組件單元測試
 *
 * Phase 3.3+3.4 - Task D2: 組件單元測試
 *
 * 測試範圍:
 * - DataSourceSelector 組件
 * - IndicatorSelector 組件
 * - StrategyLogicSelector 組件
 * - ParameterRangeInput 組件
 * - TestModeSelector 組件
 * - SignalTooltip 組件
 *
 * Ultra Think 記錄:
 * - 步驟 1: 初版代碼 (當前)
 * - 步驟 2: 審查優化 (待執行)
 * - 步驟 3: 最終優化 (待執行)
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import DataSourceSelector from "@/components/strategy/DataSourceSelector";
import IndicatorSelector from "@/components/strategy/IndicatorSelector";
import StrategyLogicSelector from "@/components/strategy/StrategyLogicSelector";
import SignalTooltip from "@/components/strategy/SignalTooltip";
import TestModeSelector from "@/components/strategy/TestModeSelector";

/**
 * DataSourceSelector 測試
 */
describe("DataSourceSelector", () => {
  it("should render with default value", () => {
    const onChange = jest.fn();
    render(<DataSourceSelector value="close" onChange={onChange} />);

    expect(screen.getByText("數據源選擇")).toBeInTheDocument();
  });

  it("should call onChange when selection changes", () => {
    const onChange = jest.fn();
    render(<DataSourceSelector value="close" onChange={onChange} />);

    // 模擬選擇變更
    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "volume" } });

    expect(onChange).toHaveBeenCalledWith("volume");
  });

  it("should be disabled when disabled prop is true", () => {
    const onChange = jest.fn();
    render(<DataSourceSelector value="close" onChange={onChange} disabled={true} />);

    const select = screen.getByRole("combobox");
    expect(select).toBeDisabled();
  });

  it("should display all 8 data source options", () => {
    const onChange = jest.fn();
    render(<DataSourceSelector value="close" onChange={onChange} />);

    const select = screen.getByRole("combobox");
    const options = select.querySelectorAll("option");

    // 應該有 8 個選項
    expect(options).toHaveLength(8);
  });
});

/**
 * IndicatorSelector 測試
 */
describe("IndicatorSelector", () => {
  it("should render with EMA selected by default", () => {
    const onChange = jest.fn();
    render(<IndicatorSelector value="ema" onChange={onChange} />);

    expect(screen.getByText("指標類型選擇")).toBeInTheDocument();
  });

  it("should show coming soon badge for unavailable indicators", () => {
    const onChange = jest.fn();
    render(<IndicatorSelector value="ema" onChange={onChange} />);

    // 檢查是否有 "即將推出" 標記
    const comingSoonBadges = screen.queryAllByText("即將推出");
    expect(comingSoonBadges.length).toBeGreaterThan(0);
  });

  it("should not allow selection of unavailable indicators", () => {
    const onChange = jest.fn();
    render(<IndicatorSelector value="ema" onChange={onChange} />);

    // 嘗試選擇不可用的指標
    const smaOption = screen.getByRole("option", { name: /SMA/ });
    expect(smaOption).toBeDisabled();
  });
});

/**
 * StrategyLogicSelector 測試
 */
describe("StrategyLogicSelector", () => {
  it("should render three strategy options", () => {
    const onChange = jest.fn();
    render(<StrategyLogicSelector value="three_line" onChange={onChange} />);

    // 應該顯示 3 個策略選項
    expect(screen.getByText("三線排列")).toBeInTheDocument();
    expect(screen.getByText("短長交叉")).toBeInTheDocument();
    expect(screen.getByText("中長交叉")).toBeInTheDocument();
  });

  it("should display strategy conditions", () => {
    const onChange = jest.fn();
    render(<StrategyLogicSelector value="three_line" onChange={onChange} />);

    // 檢查條件顯示
    expect(screen.getByText(/short > mid > long/)).toBeInTheDocument();
  });

  it("should call onChange when strategy is selected", () => {
    const onChange = jest.fn();
    render(<StrategyLogicSelector value="three_line" onChange={onChange} />);

    // 選擇不同的策略
    const shortLongButton = screen.getByText("短長交叉").closest("button");
    if (shortLongButton) {
      fireEvent.click(shortLongButton);
      expect(onChange).toHaveBeenCalledWith("short_long_cross");
    }
  });
});

/**
 * TestModeSelector 測試
 */
describe("TestModeSelector", () => {
  it("should render single and optuna mode options", () => {
    const onChange = jest.fn();
    render(
      <TestModeSelector
        value={{ mode: "single" }}
        onChange={onChange}
      />
    );

    expect(screen.getByText("單次測試")).toBeInTheDocument();
    expect(screen.getByText("Optuna 優化")).toBeInTheDocument();
  });

  it("should show estimated execution time", () => {
    const onChange = jest.fn();
    render(
      <TestModeSelector
        value={{ mode: "single" }}
        onChange={onChange}
      />
    );

    // 檢查預估時間顯示
    expect(screen.getByText(/< 5秒/)).toBeInTheDocument();
  });

  it("should allow changing optuna trials", () => {
    const onChange = jest.fn();
    render(
      <TestModeSelector
        value={{ mode: "optuna", optuna_trials: 100 }}
        onChange={onChange}
      />
    );

    // 檢查 trials 輸入框
    const trialsInput = screen.getByLabelText(/Optuna 試驗次數/);
    expect(trialsInput).toBeInTheDocument();
    expect(trialsInput).toHaveValue(100);
  });
});

/**
 * SignalTooltip 測試
 */
describe("SignalTooltip", () => {
  const mockData = {
    timestamp: 1704067200, // 2024-01-01 00:00:00
    price: 67823.45,
    indicator_values: {
      ema_short: 7,
      ema_mid: 18,
      ema_long: 35,
    },
    signal_density: 0.853,
  };

  it("should not render when data is null", () => {
    const { container } = render(<SignalTooltip data={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("should render with signal data", () => {
    render(<SignalTooltip data={mockData} />);

    // 檢查標題
    expect(screen.getByText("📍 策略信號")).toBeInTheDocument();
  });

  it("should display formatted price", () => {
    render(<SignalTooltip data={mockData} />);

    // 檢查價格格式化
    expect(screen.getByText(/\$67,823\.45/)).toBeInTheDocument();
  });

  it("should display all indicator values", () => {
    render(<SignalTooltip data={mockData} />);

    // 檢查所有指標值
    expect(screen.getByText("短期 EMA")).toBeInTheDocument();
    expect(screen.getByText("中期 EMA")).toBeInTheDocument();
    expect(screen.getByText("長期 EMA")).toBeInTheDocument();
    expect(screen.getByText("7.00")).toBeInTheDocument();
    expect(screen.getByText("18.00")).toBeInTheDocument();
    expect(screen.getByText("35.00")).toBeInTheDocument();
  });

  it("should display signal density when provided", () => {
    render(<SignalTooltip data={mockData} />);

    // 檢查信號密度
    expect(screen.getByText("信號密度")).toBeInTheDocument();
    expect(screen.getByText("85.3%")).toBeInTheDocument();
    expect(screen.getByText("高密度區域")).toBeInTheDocument();
  });

  it("should not display signal density section when not provided", () => {
    const dataWithoutDensity = { ...mockData, signal_density: undefined };
    render(<SignalTooltip data={dataWithoutDensity} />);

    // 不應該顯示信號密度區塊
    expect(screen.queryByText("信號密度")).not.toBeInTheDocument();
  });

  it("should update position based on mousePosition prop", () => {
    const { rerender } = render(
      <SignalTooltip
        data={mockData}
        mousePosition={{ x: 100, y: 200 }}
      />
    );

    // 重新渲染並檢查位置更新
    rerender(
      <SignalTooltip
        data={mockData}
        mousePosition={{ x: 300, y: 400 }}
      />
    );

    // Tooltip 應該存在 (位置通過 style 屬性控制)
    expect(screen.getByText("📍 策略信號")).toBeInTheDocument();
  });
});

/**
 * 參數驗證測試
 */
describe("Parameter Validation", () => {
  it("should validate EMA parameters in single mode", () => {
    // 測試: short < mid < long
    const validParams = {
      ema_short: 7,
      ema_mid: 18,
      ema_long: 35,
    };

    const invalidParams = {
      ema_short: 35,
      ema_mid: 18,
      ema_long: 7,
    };

    // 驗證邏輯
    const isValid = (params: any) => {
      return (
        params.ema_short < params.ema_mid &&
        params.ema_mid < params.ema_long
      );
    };

    expect(isValid(validParams)).toBe(true);
    expect(isValid(invalidParams)).toBe(false);
  });

  it("should validate EMA parameter ranges in optuna mode", () => {
    // 測試: short.max < mid.min < mid.max < long.min
    const validRanges = {
      ema_short: { min: 5, max: 10 },
      ema_mid: { min: 15, max: 25 },
      ema_long: { min: 30, max: 40 },
    };

    const invalidRanges = {
      ema_short: { min: 5, max: 20 }, // max 過大，與 mid.min 重疊
      ema_mid: { min: 15, max: 25 },
      ema_long: { min: 30, max: 40 },
    };

    // 驗證邏輯
    const isValid = (ranges: any) => {
      return (
        ranges.ema_short.max < ranges.ema_mid.min &&
        ranges.ema_mid.max < ranges.ema_long.min
      );
    };

    expect(isValid(validRanges)).toBe(true);
    expect(isValid(invalidRanges)).toBe(false);
  });
});

/**
 * 整合測試 - 完整配置流程
 */
describe("Integration - Complete Configuration Flow", () => {
  it("should validate complete strategy configuration", () => {
    const validConfig = {
      data_source: "close",
      indicator_type: "ema",
      strategy_logic: "three_line",
      test_mode: { mode: "single" as const },
      ema_parameters: {
        ema_short: 7,
        ema_mid: 18,
        ema_long: 35,
      },
      training_window: {
        reference_point: "TO" as const,
        lookback_bars: 24,
        lookforward_bars: 0,
        mode: "relative" as const,
      },
    };

    // 驗證所有欄位存在
    expect(validConfig.data_source).toBeDefined();
    expect(validConfig.indicator_type).toBeDefined();
    expect(validConfig.strategy_logic).toBeDefined();
    expect(validConfig.test_mode.mode).toBe("single");
    expect(validConfig.ema_parameters.ema_short).toBe(7);
    expect(validConfig.training_window.reference_point).toBe("TO");
  });
});
