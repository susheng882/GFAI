import daisyui from 'daisyui';
import animate from 'tailwindcss-animate';

/** GFLC v8 设计 token（对齐原型 v7l 的苹果浅灰白体系） */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  // 进度条按 2% 步进取宽度类（运行时拼类名，需预生成；避免内联 style）
  safelist: Array.from({ length: 51 }, (_, i) => `w-[${i * 2}%]`),
  theme: {
    extend: {
      colors: {
        ink: '#1D1D1F',
        ink2: '#6E6E73',
        ink3: '#86868B',
        line: '#E8E8ED',
        line2: '#D2D2D7',
        page: '#F5F5F7',
        card: '#FFFFFF',
        sider: '#FBFBFD',
        sel: '#EFEFF2',
        brand: '#0071E3',
        brandSoft: '#E8F1FD',
        ok: '#34C759',
        warn: '#FF9F0A',
        bad: '#FF3B30',
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'SF Pro Text',
          'Segoe UI',
          'PingFang SC',
          'Hiragino Sans GB',
          'Microsoft YaHei',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
        mono: ['SF Mono', 'ui-monospace', 'Menlo', 'Consolas', 'monospace'],
      },
      borderRadius: {
        card: '16px',
        field: '10px',
      },
      spacing: {
        '4.5': '18px',
        '13': '52px',
        '57': '228px',
        '16': '64px',
      },
      transitionTimingFunction: {
        apple: 'cubic-bezier(.16,1,.3,1)',
      },
      boxShadow: {
        // 仅侧栏底部极淡阴影，禁止彩色 / 发光
        sider: '1px 0 0 0 #E8E8ED',
        pop: '0 12px 32px rgba(0,0,0,0.08)',
      },
      maxWidth: {
        shell: '1180px',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-up': 'fadeUp 220ms cubic-bezier(.16,1,.3,1) both',
      },
    },
  },
  plugins: [daisyui, animate],
  daisyui: {
    logs: false,
    themes: [
      {
        gflc: {
          primary: '#0071E3',
          'primary-content': '#FFFFFF',
          secondary: '#6E6E73',
          accent: '#0071E3',
          neutral: '#1D1D1F',
          'base-100': '#FFFFFF',
          'base-200': '#F5F5F7',
          'base-300': '#E8E8ED',
          'base-content': '#1D1D1F',
          info: '#0071E3',
          success: '#34C759',
          warning: '#FF9F0A',
          error: '#FF3B30',
          '--rounded-box': '16px',
          '--rounded-btn': '10px',
          '--rounded-badge': '999px',
          '--border-btn': '1px',
        },
      },
    ],
  },
};
