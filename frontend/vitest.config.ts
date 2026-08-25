import path from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    // GAP-3 UX Task 1.3 ④(a)：雜湊入口之執行期計數（passthrough 包裝，不改變既有行為）
    setupFiles: ['src/test/hashEntrySpy.ts'],
  },
});
