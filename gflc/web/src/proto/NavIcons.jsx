import React from 'react';

/**
 * GFLC v8 · 线性图标集（18 个导航图标 + 少量界面图标）
 * 规格：内联 SVG，stroke=1.6，currentColor，24×24 视框，零外链。
 */

function Svg({ size = 16, className = '', children, strokeWidth = 1.6, ...rest }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
      {...rest}
    >
      {children}
    </svg>
  );
}

/* 1 概览 */
export const DashIcon = (p) => (
  <Svg {...p}>
    <rect x="3.5" y="3.5" width="7" height="7" rx="2" />
    <rect x="13.5" y="3.5" width="7" height="7" rx="2" />
    <rect x="3.5" y="13.5" width="7" height="7" rx="2" />
    <rect x="13.5" y="13.5" width="7" height="7" rx="2" />
  </Svg>
);

/* 2 笔记 */
export const NotesIcon = (p) => (
  <Svg {...p}>
    <path d="M6 3.5h8.5L19 8v12.5H6z" />
    <path d="M14 3.5V8h5" />
    <path d="M9 12.5h7M9 16h5" />
  </Svg>
);

/* 3 学习 */
export const StudyIcon = (p) => (
  <Svg {...p}>
    <path d="M12 6.5C10.4 5.2 8.3 4.5 5.5 4.5H3.5v14h2c2.8 0 4.9.7 6.5 2 1.6-1.3 3.7-2 6.5-2h2v-14h-2c-2.8 0-4.9.7-6.5 2z" />
    <path d="M12 6.5v14" />
  </Svg>
);

/* 4 复习 */
export const ReviewIcon = (p) => (
  <Svg {...p}>
    <path d="M20 12a8 8 0 1 1-2.6-5.9" />
    <path d="M20 4v4.5h-4.5" />
    <path d="M12 8v4.5l3 1.8" />
  </Svg>
);

/* 5 计划 */
export const PlansIcon = (p) => (
  <Svg {...p}>
    <rect x="3.5" y="5" width="17" height="15.5" rx="3" />
    <path d="M3.5 9.5h17M8 3.5v3M16 3.5v3" />
    <path d="M8 13.5h3M13 13.5h3M8 17h3" />
  </Svg>
);

/* 6 成长 */
export const GrowthIcon = (p) => (
  <Svg {...p}>
    <path d="M3.5 19.5h17" />
    <path d="M6 19.5v-5M10.5 19.5v-8M15 19.5v-4M19.5 19.5v-11" />
  </Svg>
);

/* 7 资料 */
export const DocsIcon = (p) => (
  <Svg {...p}>
    <path d="M3.5 7.5c0-1.7 1.3-3 3-3h3l2 2.5h6c1.7 0 3 1.3 3 3v7.5c0 1.7-1.3 3-3 3H6.5c-1.7 0-3-1.3-3-3z" />
    <path d="M3.5 11h17" />
  </Svg>
);

/* 8 题库 */
export const BanksIcon = (p) => (
  <Svg {...p}>
    <path d="M12 3.5 20.5 8 12 12.5 3.5 8z" />
    <path d="M3.5 12.5 12 17l8.5-4.5" />
    <path d="M3.5 16.5 12 21l8.5-4.5" />
  </Svg>
);

/* 9 卡包 */
export const DeckIcon = (p) => (
  <Svg {...p}>
    <rect x="3.5" y="6.5" width="12" height="14" rx="2.5" />
    <path d="M18.5 5.2A2.5 2.5 0 0 1 20.5 7.6v10.9" />
    <path d="M7 11h6M7 14.5h4" />
  </Svg>
);

/* 10 视频 */
export const VideoIcon = (p) => (
  <Svg {...p}>
    <rect x="3" y="5.5" width="18" height="13" rx="3" />
    <path d="M10.5 9.5 15 12l-4.5 2.5z" />
  </Svg>
);

/* 11 问答 */
export const QaIcon = (p) => (
  <Svg {...p}>
    <path d="M20.5 12.5c0 3.9-3.8 7-8.5 7-.9 0-1.8-.1-2.6-.4L4 21l1.4-3.7A6.5 6.5 0 0 1 3.5 12.5c0-3.9 3.8-7 8.5-7s8.5 3.1 8.5 7z" />
    <path d="M9 11.5h6M9 14.5h4" />
  </Svg>
);

/* 12 任务 */
export const TasksIcon = (p) => (
  <Svg {...p}>
    <path d="M4 6.5 5.6 8 8.5 5" />
    <path d="M4 13.5 5.6 15l2.9-3" />
    <path d="M11.5 7h8.5M11.5 14h8.5M11.5 20h8.5" />
  </Svg>
);

/* 13 设置 */
export const SettingsIcon = (p) => (
  <Svg {...p}>
    <path d="M4 7h9M17 7h3M4 17h3M11 17h9" />
    <circle cx="15" cy="7" r="2.2" />
    <circle cx="9" cy="17" r="2.2" />
  </Svg>
);

/* 14 搜索 */
export const SearchIcon = (p) => (
  <Svg {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M16 16l4 4" />
  </Svg>
);

/* 15 通知 */
export const BellIcon = (p) => (
  <Svg {...p}>
    <path d="M6.5 10a5.5 5.5 0 0 1 11 0c0 4 1.5 5.5 1.5 5.5H5s1.5-1.5 1.5-5.5z" />
    <path d="M10 19a2.2 2.2 0 0 0 4 0" />
  </Svg>
);

/* 16 新增 */
export const PlusIcon = (p) => (
  <Svg {...p}>
    <path d="M12 5v14M5 12h14" />
  </Svg>
);

/* 17 收起/展开侧栏 */
export const SidebarIcon = (p) => (
  <Svg {...p}>
    <rect x="3.5" y="4.5" width="17" height="15" rx="3" />
    <path d="M9.5 4.5v15" />
    <path d="M6 12h1.5" />
  </Svg>
);

/* 18 关闭 */
export const CloseIcon = (p) => (
  <Svg {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Svg>
);

/* —— 界面辅助图标 —— */
export const CheckIcon = (p) => (
  <Svg {...p}>
    <path d="M4.5 12.5 9 17l10.5-10" />
  </Svg>
);

export const ArrowRightIcon = (p) => (
  <Svg {...p}>
    <path d="M5 12h13" />
    <path d="M13 7l5 5-5 5" />
  </Svg>
);

export const ChevronDownIcon = (p) => (
  <Svg {...p}>
    <path d="M6 9.5l6 6 6-6" />
  </Svg>
);

export const UploadIcon = (p) => (
  <Svg {...p}>
    <path d="M12 16V5" />
    <path d="M8 8.5 12 4.5l4 4" />
    <path d="M4.5 15.5V18a2.5 2.5 0 0 0 2.5 2.5h10a2.5 2.5 0 0 0 2.5-2.5v-2.5" />
  </Svg>
);

export const SparkIcon = (p) => (
  <Svg {...p}>
    <path d="M12 3.5l1.7 4.6 4.8 1.7-4.8 1.7L12 16.1l-1.7-4.6-4.8-1.7 4.8-1.7z" />
    <path d="M18 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z" />
  </Svg>
);

export const TargetIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="8" />
    <circle cx="12" cy="12" r="3.6" />
    <path d="M12 4V2M12 22v-2M4 12H2M22 12h-2" />
  </Svg>
);

export const FlameIcon = (p) => (
  <Svg {...p}>
    <path d="M12 3.5c3 3.2 5.5 5.6 5.5 9a5.5 5.5 0 0 1-11 0c0-1.9.8-3.3 2-4.6.4 1.4 1.2 2.2 2.2 2.6-.3-2.6.3-5 1.3-7z" />
  </Svg>
);

export const PlayIcon = (p) => (
  <Svg {...p}>
    <path d="M8 5.5 18 12 8 18.5z" />
  </Svg>
);

/** 导航 key → 图标组件 */
export const NAV_ICONS = {
  dash: DashIcon,
  notes: NotesIcon,
  study: StudyIcon,
  review: ReviewIcon,
  plans: PlansIcon,
  growth: GrowthIcon,
  docs: DocsIcon,
  banks: BanksIcon,
  deck: DeckIcon,
  video: VideoIcon,
  qa: QaIcon,
  tasks: TasksIcon,
  settings: SettingsIcon,
};

export default NAV_ICONS;
