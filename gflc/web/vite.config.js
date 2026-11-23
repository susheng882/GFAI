import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 构建产物输出到 gflc/web/dist（本 Agent 独占路径内）。
// 集成方接线方式见 README.md：把 FRONTEND_DIR 指向 gflc/web/dist，
// 或把 dist 内容复制到 backend/frontend/dist 后修改 FRONTEND_DIR=./frontend/dist。
export default defineConfig({
  plugins: [react()],
  base: '/',
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1200,
  },
});
