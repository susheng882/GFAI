import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import NAV_ICONS, {
  SearchIcon,
  BellIcon,
  SidebarIcon,
  CloseIcon,
  ArrowRightIcon,
  CheckIcon,
} from './NavIcons.jsx';
import { Badge, Divider, KeyCap, cx } from './ui.jsx';
import {
  profile as defaultProfile,
  notificationCount,
  paletteActions,
} from './mock/index.js';

/** 侧栏分组（对齐 v8 规格：学习 / 资料 / 助手 / 系统） */
const NAV_GROUPS = [
  {
    title: '学习',
    items: [
      { key: 'dash', name: '概览', to: '/dash' },
      { key: 'notes', name: '笔记', to: '/notes' },
      { key: 'study', name: '学习', to: '/study' },
      { key: 'review', name: '复习', to: '/review', badge: 42 },
      { key: 'plans', name: '计划', to: '/plans' },
      { key: 'growth', name: '成长', to: '/growth' },
    ],
  },
  {
    title: '资料',
    items: [
      { key: 'docs', name: '资料', to: '/docs' },
      { key: 'banks', name: '题库', to: '/banks' },
      { key: 'deck', name: '卡包', to: '/deck' },
      { key: 'video', name: '视频', to: '/video' },
    ],
  },
  {
    title: '助手',
    items: [{ key: 'qa', name: '问答', to: '/qa' }],
  },
  {
    title: '系统',
    items: [
      { key: 'tasks', name: '任务', to: '/tasks', badge: 3 },
      { key: 'settings', name: '设置', to: '/settings' },
    ],
  },
];

const PAGE_TITLES = {
  dash: ['概览', '今日复习、掌握率与学习闭环；一屏看到该做什么'],
  notes: ['笔记', '文件夹管理，AI 协作补写'],
  study: ['学习', '刷题、背诵、错题一页'],
  review: ['复习', '按遗忘曲线安排今日到期卡片'],
  plans: ['计划', '目标拆解为每日任务，勾选完成'],
  growth: ['成长', '等级、五维能力、里程碑'],
  docs: ['资料', '上传教材 / 讲义，解析并生成卡片'],
  banks: ['题库', '导入试卷，按题型归档练习'],
  deck: ['卡包', '按大纲章节组织的背诵卡包'],
  video: ['视频', '链接或上传，转写后生成结构化笔记'],
  qa: ['问答', '先查你的资料，再联网，最后用学科知识'],
  tasks: ['任务', '后台任务进度与重试'],
  settings: ['设置', '模型供应商、转录器、诊断与监控'],
};

const NOTIFICATIONS = [
  { id: 'n1', tone: 'brand', title: '42 张卡片今日到期', time: '10 分钟前', desc: '操作系统 · 内存管理 占 18 张' },
  { id: 'n2', tone: 'ok', title: '视频转写完成', time: '1 小时前', desc: '操作系统 第 4 讲 · 已生成 12 张卡片' },
  { id: 'n3', tone: 'warn', title: '解析队列积压 3 个任务', time: '2 小时前', desc: '可在「任务」页查看进度' },
];

function usePageKey() {
  const { pathname } = useLocation();
  return useMemo(() => {
    const seg = pathname.split('/').filter(Boolean)[0] || 'dash';
    return PAGE_TITLES[seg] ? seg : 'dash';
  }, [pathname]);
}

function LogoMark({ mini }) {
  return (
    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] bg-ink text-[11px] font-medium text-white">
      GF
    </span>
  );
}

function Sidebar({ mini, onToggle, onLogout, user, width = 228, onResize }) {
  const [dragging, setDragging] = useState(false);
  const startX = useRef(0);
  const startW = useRef(228);

  const onMouseDown = (e) => {
    e.preventDefault();
    startX.current = e.clientX;
    startW.current = width;
    setDragging(true);
    const onMove = (ev) => {
      const delta = ev.clientX - startX.current;
      const next = Math.min(320, Math.max(180, startW.current + delta));
      onResize?.(next);
    };
    const onUp = () => {
      setDragging(false);
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  return (
    <aside
      className={cx(
        'relative flex h-full shrink-0 flex-col border-r border-line bg-sider shadow-sider',
        mini ? 'w-[64px]' : 'transition-[width] duration-200 ease-apple',
      )}
      style={mini ? undefined : { width }}
    >
      {/* 拖拽手柄：右侧边缘，调整侧栏宽度 */}
      {!mini && (
        <span
          onMouseDown={onMouseDown}
          className={cx(
            'absolute right-0 top-0 z-20 h-full w-[5px] cursor-col-resize',
            dragging ? 'bg-brand/30' : 'hover:bg-brand/15',
          )}
          title="拖拽调整侧栏宽度"
        />
      )}
      <div className={cx('flex h-14 shrink-0 items-center border-b border-line', mini ? 'justify-center px-0' : 'gap-2.5 px-4')}>
        <LogoMark mini={mini} />
        {mini ? null : (
          <div className="min-w-0">
            <p className="truncate text-[13px] font-medium leading-[18px] text-ink">GFLC 成长向前</p>
            <p className="truncate text-[10px] leading-[14px] text-ink3">考研 11408 · 第 128 天</p>
          </div>
        )}
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-2.5 py-3" aria-label="主导航">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="mb-3 last:mb-0">
            {mini ? <div className="mx-auto mb-1.5 h-px w-6 bg-line" /> : (
              <p className="mb-1 px-2.5 text-[10px] font-medium leading-[16px] text-ink3">{group.title}</p>
            )}
            <div className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const Icon = NAV_ICONS[item.key];
                return (
                  <NavLink
                    key={item.key}
                    to={item.to}
                    title={mini ? item.name : undefined}
                    className={({ isActive }) =>
                      cx('gf-nav', mini && 'justify-center px-0', isActive && 'gf-nav-on')
                    }
                  >
                    <Icon size={16} className="shrink-0" />
                    {mini ? null : (
                      <>
                        <span className="truncate">{item.name}</span>
                        {item.badge ? (
                          <span className="gf-num ml-auto rounded-full bg-sel px-1.5 text-[10px] leading-[15px] text-ink2">
                            {item.badge}
                          </span>
                        ) : null}
                      </>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="shrink-0 border-t border-line p-2.5">
        {mini ? null : (
          <>
            <div className="flex items-center gap-2 rounded-[10px] px-1.5 py-1.5">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sel text-[10px] font-medium text-ink">
                {user.initial}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[12px] leading-[16px] text-ink">{user.name}</p>
                <p className="truncate text-[10px] leading-[14px] text-ink3">{user.exam} · 目标 {user.targetScore}</p>
              </div>
            </div>
            <Divider className="my-1.5" />
          </>
        )}
        <div className={cx('flex items-center', mini ? 'justify-center' : 'justify-between')}>
          {mini ? null : (
            <button
              type="button"
              onClick={onLogout}
              className="gf-btn h-7 px-2 text-[11px] text-ink3 hover:bg-sel hover:text-ink"
            >
              退出登录
            </button>
          )}
          <button
            type="button"
            onClick={onToggle}
            aria-label={mini ? '展开侧栏' : '收起侧栏'}
            title={mini ? '展开侧栏' : '收起侧栏'}
            className="flex h-7 w-7 items-center justify-center rounded-[8px] text-ink3 transition-colors duration-200 ease-apple hover:bg-sel hover:text-ink"
          >
            <SidebarIcon size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}

function Topbar({ pageKey, mini, onToggleMini, onOpenPalette, user, onLogout }) {
  const [title, sub] = PAGE_TITLES[pageKey] || PAGE_TITLES.dash;
  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef(null);

  useEffect(() => {
    if (!notifOpen) return undefined;
    const onDocClick = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) setNotifOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [notifOpen]);

  return (
    <header className="relative z-20 flex h-14 shrink-0 items-center gap-3 border-b border-line bg-card px-6">
      <button
        type="button"
        onClick={onToggleMini}
        className="hidden h-7 w-7 items-center justify-center rounded-[8px] text-ink3 hover:bg-sel hover:text-ink xl:hidden"
        aria-label="切换侧栏"
      >
        <SidebarIcon size={16} />
      </button>
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-[17px] font-medium leading-[24px] text-ink">{title}</h1>
        <p className="truncate text-[12px] leading-[16px] text-ink3">{sub}</p>
      </div>

      <button
        type="button"
        onClick={onOpenPalette}
        className="flex h-8 w-[248px] shrink-0 items-center gap-2 rounded-[10px] bg-sel px-2.5 text-[12px] text-ink3 transition-colors duration-200 ease-apple hover:bg-line"
      >
        <SearchIcon size={14} className="shrink-0" />
        <span className="truncate">搜索资料、卡片、题目</span>
        <span className="ml-auto flex items-center gap-0.5">
          <KeyCap>⌘</KeyCap>
          <KeyCap>K</KeyCap>
        </span>
      </button>

      <div className="relative shrink-0" ref={notifRef}>
        <button
          type="button"
          onClick={() => setNotifOpen((v) => !v)}
          className="relative flex h-8 w-8 items-center justify-center rounded-[10px] text-ink2 transition-colors duration-200 ease-apple hover:bg-sel hover:text-ink"
          aria-label="通知"
          aria-expanded={notifOpen}
        >
          <BellIcon size={17} />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-bad" />
        </button>
        {notifOpen ? (
          <div className="absolute right-0 top-10 w-[300px] animate-fade-up overflow-hidden rounded-[16px] border border-line bg-card shadow-pop">
            <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
              <p className="text-[13px] font-medium text-ink">通知</p>
              <Badge tone="neutral">{notificationCount} 条</Badge>
            </div>
            <ul className="divide-y divide-line">
              {NOTIFICATIONS.map((n) => (
                <li key={n.id} className="px-4 py-2.5">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cx(
                        'h-1.5 w-1.5 rounded-full',
                        n.tone === 'ok' ? 'bg-ok' : n.tone === 'warn' ? 'bg-warn' : 'bg-brand',
                      )}
                    />
                    <p className="truncate text-[12px] font-medium text-ink">{n.title}</p>
                    <span className="ml-auto shrink-0 text-[10px] text-ink3">{n.time}</span>
                  </div>
                  <p className="mt-0.5 pl-3 text-[11px] text-ink3">{n.desc}</p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      <button
        type="button"
        onClick={onLogout}
        title={`${user.name} · 退出登录`}
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sel text-[11px] font-medium text-ink transition-colors duration-200 ease-apple hover:bg-line"
      >
        {user.initial}
      </button>
    </header>
  );
}

function CommandPalette({ open, onClose }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef(null);

  const items = useMemo(() => {
    const pages = NAV_GROUPS.flatMap((g) =>
      g.items.map((it) => ({
        key: `go-${it.key}`,
        label: `前往${it.name}页面`,
        hint: g.title,
        to: it.to,
        icon: NAV_ICONS[it.key],
      })),
    );
    const actions = paletteActions.map((a) => ({
      key: a.key,
      label: a.label,
      hint: a.hint,
      to: a.to,
      icon: ArrowRightIcon,
    }));
    return [...actions, ...pages];
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) => `${it.label}${it.hint}`.toLowerCase().includes(q));
  }, [items, query]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setCursor(0);
      const t = window.setTimeout(() => inputRef.current?.focus(), 30);
      return () => window.clearTimeout(t);
    }
    return undefined;
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setCursor((c) => (filtered.length ? (c + 1) % filtered.length : 0));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setCursor((c) => (filtered.length ? (c - 1 + filtered.length) % filtered.length : 0));
      } else if (e.key === 'Enter') {
        const target = filtered[cursor];
        if (target) {
          e.preventDefault();
          navigate(target.to);
          onClose();
        }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, filtered, cursor, navigate, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center">
      <button
        type="button"
        aria-label="关闭命令面板"
        onClick={onClose}
        className="absolute inset-0 bg-ink/20"
      />
      <div className="relative mt-[120px] w-[520px] animate-fade-up overflow-hidden rounded-[16px] border border-line bg-card shadow-pop">
        <div className="flex h-12 items-center gap-2 border-b border-line px-4">
          <SearchIcon size={15} className="shrink-0 text-ink3" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setCursor(0);
            }}
            placeholder="搜索页面或动作"
            className="h-full w-full bg-transparent text-[13px] text-ink placeholder:text-ink3 focus:outline-none"
          />
          <button type="button" onClick={onClose} className="shrink-0 text-ink3 hover:text-ink" aria-label="关闭">
            <CloseIcon size={15} />
          </button>
        </div>
        <ul className="max-h-[336px] overflow-y-auto p-1.5">
          {filtered.length === 0 ? (
            <li className="px-3 py-6 text-center text-[12px] text-ink3">没有匹配的页面或动作</li>
          ) : (
            filtered.map((it, idx) => {
              const Icon = it.icon;
              const active = idx === cursor;
              return (
                <li key={it.key}>
                  <button
                    type="button"
                    onMouseEnter={() => setCursor(idx)}
                    onClick={() => {
                      navigate(it.to);
                      onClose();
                    }}
                    className={cx(
                      'flex h-9 w-full items-center gap-2.5 rounded-[10px] px-2.5 text-left text-[13px] transition-colors duration-150 ease-apple',
                      active ? 'bg-sel text-ink' : 'text-ink2 hover:bg-sel hover:text-ink',
                    )}
                  >
                    <Icon size={15} className="shrink-0" />
                    <span className="truncate">{it.label}</span>
                    <span className="ml-auto shrink-0 text-[10px] text-ink3">{it.hint}</span>
                    {active ? <CheckIcon size={13} className="shrink-0 text-brand" /> : null}
                  </button>
                </li>
              );
            })
          )}
        </ul>
        <div className="flex items-center gap-3 border-t border-line px-4 py-2 text-[10px] text-ink3">
          <span>↑↓ 选择</span>
          <span>Enter 执行</span>
          <span>Esc 关闭</span>
        </div>
      </div>
    </div>
  );
}

const MINI_KEY = 'gflc_sbmini';

/**
 * AppShell：侧栏（展开 228px / 收起 64px）+ 顶栏 + 内容容器 + 路由出口
 */
export default function AppShell({ children, user = defaultProfile, onLogout = () => {} }) {
  const [mini, setMini] = useState(() => {
    try {
      return window.localStorage.getItem(MINI_KEY) === '1';
    } catch {
      return false;
    }
  });
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [sbWidth, setSbWidth] = useState(() => {
    try {
      const n = Number(window.localStorage.getItem('gflc_sbwidth'));
      return n >= 180 && n <= 320 ? n : 228;
    } catch {
      return 228;
    }
  });
  const pageKey = usePageKey();

  const onResizeSb = useCallback((w) => {
    setSbWidth(Math.round(w));
    try {
      window.localStorage.setItem('gflc_sbwidth', String(Math.round(w)));
    } catch {
      /* noop */
    }
  }, []);

  const toggleMini = useCallback(() => {
    setMini((v) => {
      const next = !v;
      try {
        window.localStorage.setItem(MINI_KEY, next ? '1' : '0');
      } catch {
        /* localStorage 不可用时仅内存态生效 */
      }
      return next;
    });
  }, []);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="flex h-full w-full overflow-hidden bg-page">
      <Sidebar mini={mini} onToggle={toggleMini} onLogout={onLogout} user={user} width={sbWidth} onResize={onResizeSb} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          pageKey={pageKey}
          mini={mini}
          onToggleMini={toggleMini}
          onOpenPalette={() => setPaletteOpen(true)}
          user={user}
          onLogout={onLogout}
        />
        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-shell px-6 py-5">{children}</div>
        </main>
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
