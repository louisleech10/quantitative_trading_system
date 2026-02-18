import { create } from 'zustand';
import type { ModelEnhancementResult } from '@/lib/types';

const DEFAULT_MODULES = [
  'calibration',
  'walk_forward',
  'sample_weight',
  'adversarial',
  'cpcv',
  'learning_curve',
] as const;

interface ModelEnhancementState {
  currentResult: ModelEnhancementResult | null;
  isRunning: boolean;
  activeModules: string[];
  setResult: (result: ModelEnhancementResult) => void;
  setRunning: (running: boolean) => void;
  setActiveModules: (modules: string[]) => void;
  reset: () => void;
}

export const useModelEnhancementStore = create<ModelEnhancementState>((set) => ({
  currentResult: null,
  isRunning: false,
  activeModules: [...DEFAULT_MODULES],
  setResult: (result) => set({ currentResult: result }),
  setRunning: (running) => set({ isRunning: running }),
  setActiveModules: (modules) => set({ activeModules: modules }),
  reset: () =>
    set({
      currentResult: null,
      isRunning: false,
      activeModules: [...DEFAULT_MODULES],
    }),
}));
