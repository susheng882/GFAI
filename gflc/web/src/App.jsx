import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { App as AntdApp, ConfigProvider, theme as antdTheme, Spin } from 'antd';
import {
  AppstoreOutlined, FormOutlined, BookOutlined, ClockCircleOutlined,
  FileTextOutlined, CreditCardOutlined, VideoCameraOutlined,
  MessageOutlined, UnorderedListOutlined, CalendarOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined, MenuOutlined, LogoutOutlined,
  MoonOutlined, SunOutlined, SettingOutlined, SearchOutlined,
} from '@ant-design/icons';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { api } from './api.js';
import AuthPage from './pages/AuthPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import DocumentsPage from './pages/DocumentsPage.jsx';
import NotesPage from './pages/NotesPage.jsx';
import DecksPage from './pages/DecksPage.jsx';
import StudyPage from './pages/StudyPage.jsx';
import ReviewPage from './pages/ReviewPage.jsx';
import QAPage from './pages/QAPage.jsx';
import VideoPage from './pages/VideoPage.jsx';
import PlansPage from './pages/PlansPage.jsx';
import TasksPage from './pages/TasksPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import TaskDock from './components/TaskDock.jsx';

const NAV_GROUPS = [
  { title: '学习', items: [
    { key: 'dash', name: '概览', icon: <AppstoreOutlined /> },
    { key: 'notes', name: '笔记', icon: <FormOutlined /> },
    { key: 'study', name: '学习', icon: <BookOutlined /> },
    { key: 'review', name: '复习', icon: <ClockCircleOutlined /> },
    { key: 'plans', name: '计划', icon: <CalendarOutlined /> },
  ] },
  { title: '资料', items: [
    { key: 'docs', name: '解析记录', icon: <FileTextOutlined /> },
    { key: 'deck', name: '卡包', icon: <CreditCardOutlined /> },
    { key: 'video', name: '视频', icon: <VideoCameraOutlined /> },
  ] },
  { title: '助手', items: [
    { key: 'qa', name: '问答', icon: <MessageOutlined /> },
  ] },
  { title: '系统', items: [
    { key: 'tasks', name: '任务', icon: <UnorderedListOutlined /> },
    { key: 'settings', name: '设置', icon: <SettingOutlined /> },
  ] },
];
const TITLES = {
  dash: ['概览', '系统与学习指标；学习任务按需生成'],
  notes: ['笔记', '文件夹管理，AI 协作补写'],
  docs: ['解析记录', '上传资料，解析并生成卡片'],
  deck: ['卡包', '按大纲章节组织的背诵卡包'],
  study: ['学习', '刷题、背诵、错题一页'],
  review: ['复习', '按遗忘曲线安排复习'],
  plans: ['计划', '目标拆解为每日任务，勾选完成'],
  qa: ['问答', '先查你的资料，再联网，最后用学科知识'],
  video: ['视频', '链接/上传 → 转写 → 结构化笔记（配图可跳转，大纲为思维导图）'],
  tasks: ['任务', '后台任务与进度'],
  settings: ['设置', '模型供应商、转录器、B 站 Cookie、诊断与监控'],
};

/* B13 全局命令面板：键盘流（↑↓ 选择 / Enter 执行 / Esc 关闭），输入框聚焦不与页面冲突 */
function CommandPalette({ open, onClose, navigate, dark, onToggleDark }) {
  const [q, setQ] = useState('');
  const [sel, setSel] = useState(0);
  const inputRef = useRef(null);
  const cmds = useMemo(() => [
    ...NAV_GROUPS.flatMap((g) => g.items.map((it) => ({
      key: 'go:' + it.key, label: '前往 ' + it.name, hint: '页面',
      run: () => navigate('/' + it.key),
    }))),
    { key: 'new-note', label: '新建笔记', hint: '笔记', run: () => {
      navigate('/notes');
      setTimeout(() => window.dispatchEvent(new CustomEvent('gflc:cmd', { detail: { cmd: 'new-note' } })), 0);
    } },
    { key: 'tidy', label: '触发 AI 整理', hint: '笔记', run: () => {
      navigate('/notes');
      setTimeout(() => window.dispatchEvent(new CustomEvent('gflc:cmd', { detail: { cmd: 'tidy' } })), 0);
    } },
    { key: 'theme', label: dark ? '切换为浅色主题' : '切换为深色主题', hint: '外观', run: onToggleDark },
  ], [navigate, dark, onToggleDark]);
  const list = cmds.filter((c) => (c.label + c.hint).toLowerCase().includes(q.trim().toLowerCase())).slice(0, 8);
  useEffect(() => {
    if (!open) return;
    setQ(''); setSel(0);
    const t = setTimeout(() => inputRef.current?.focus(), 0);
    return () => clearTimeout(t);
  }, [open]);
  useEffect(() => { setSel(0); }, [q]);
  if (!open) return null;
  const exec = (c) => { if (!c) return; c.run(); onClose(); };
  return (
    <div className="cmd-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="cmd-panel" role="dialog" aria-label="命令面板">
        <div className="cmd-input-row">
          <SearchOutlined />
          <input ref={inputRef} value={q} placeholder="搜索命令或页面…" aria-label="搜索命令"
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setSel((s) => Math.min(list.length - 1, s + 1)); }
              else if (e.key === 'ArrowUp') { e.preventDefault(); setSel((s) => Math.max(0, s - 1)); }
              else if (e.key === 'Enter') { e.preventDefault(); exec(list[sel]); }
              else if (e.key === 'Escape') { e.preventDefault(); onClose(); }
            }} />
          <span className="cmd-esc mono">Esc</span>
        </div>
        <div className="cmd-list">
          {list.length ? list.map((c, i) => (
            <button type="button" key={c.key} className={'cmd-item' + (i === sel ? ' on' : '')}
              onMouseEnter={() => setSel(i)} onClick={() => exec(c)}>
              <span>{c.label}</span><span className="cmd-hint">{c.hint}</span>
            </button>
          )) : <div className="cmd-empty">没有匹配的命令</div>}
        </div>
      </div>
    </div>
  );
}

function Shell({ user, onLogout, dark, onToggleDark }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(localStorage.getItem('gflc_sidebar') === '1');
  const [drawer, setDrawer] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const lastFocusRef = useRef(null);
  const openCmd = useCallback(() => { lastFocusRef.current = document.activeElement; setCmdOpen(true); }, []);
  const closeCmd = useCallback(() => { setCmdOpen(false); setTimeout(() => lastFocusRef.current?.focus?.(), 0); }, []);
  // Ctrl/⌘+K 全局可用；Esc 关闭；关闭后焦点回到原输入，避免打断正在输入的页面
  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && String(e.key).toLowerCase() === 'k') {
        e.preventDefault();
        if (cmdOpen) closeCmd(); else openCmd();
        return;
      }
      if (e.key === 'Escape' && cmdOpen) { e.preventDefault(); closeCmd(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [cmdOpen, openCmd, closeCmd]);
  const current = location.pathname.split('/')[1] || 'dash';
  const title = TITLES[current] || TITLES.dash;
  const go = (key) => { navigate('/' + key); setDrawer(false); };
  return (
    <div className={'gflc-app' + (dark ? ' gflc-dark' : '') + (collapsed ? ' sider-collapsed' : '')}>
      <aside className={'gflc-sider' + (collapsed ? ' collapsed' : '') + (drawer ? ' open' : '')}>
        <div className="gflc-brand">
          <span className="logo">G</span>{!collapsed && <span className="bt">GrowthForward</span>}
          <button
            className="gflc-nav-item" style={{ height: 24, width: 24, marginLeft: 'auto', padding: 0, justifyContent: 'center' }}
            onClick={() => { const v = !collapsed; setCollapsed(v); localStorage.setItem('gflc_sidebar', v ? '1' : '0'); }}
            title={collapsed ? '展开侧栏' : '收起侧栏'}
          >
            {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </button>
        </div>
        <nav className="gflc-nav">
          {NAV_GROUPS.map((g) => (
            <div className="gflc-nav-group" key={g.title}>
              <div className="gflc-nav-title">{g.title}</div>
              {g.items.map((item) => (
                <div
                  key={item.key}
                  className={'gflc-nav-item' + (current === item.key ? ' active' : '')}
                  onClick={() => go(item.key)}
                  title={item.name}
                >
                  <span className="ic">{item.icon}</span>
                  <span className="gflc-nav-label">{item.name}</span>
                </div>
              ))}
            </div>
          ))}
        </nav>
        <div className="gflc-sider-foot">
          <div className="row between" style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {String(user?.email || 'U')[0].toUpperCase()} · {user?.email}
            </span>
            <button className="gflc-nav-item" style={{ width: 24, height: 24, padding: 0, justifyContent: 'center' }} onClick={onToggleDark} title="切换主题">
              {dark ? <SunOutlined /> : <MoonOutlined />}
            </button>
          </div>
          <button className="gflc-nav-item" style={{ width: '100%', marginTop: 8 }} onClick={onLogout}>
            <span className="ic"><LogoutOutlined /></span><span className="gflc-nav-label">退出登录</span>
          </button>
        </div>
      </aside>
      <div className={'gflc-scrim' + (drawer ? ' on' : '')} onClick={() => setDrawer(false)} />
      <main className="gflc-main">
        <header className="gflc-topbar">
          <div className="row" style={{ gap: 10 }}>
            <button className="gflc-nav-item gflc-menu-btn" style={{ width: 30, height: 30, padding: 0, justifyContent: 'center' }} onClick={() => setDrawer(!drawer)} title="打开导航">
              <MenuOutlined />
            </button>
            <div><h1>{title[0]}</h1><div className="sub">{title[1]}</div></div>
          </div>
        </header>
        <div className="gflc-content page-in">
          <Routes>
            <Route path="/" element={<Navigate to="/dash" replace />} />
            <Route path="/dash" element={<DashboardPage />} />
            <Route path="/docs" element={<DocumentsPage />} />
            <Route path="/notes" element={<NotesPage />} />
            <Route path="/deck" element={<DecksPage />} />
            <Route path="/study" element={<StudyPage />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/qa" element={<QAPage />} />
            <Route path="/video" element={<VideoPage />} />
            <Route path="/plans" element={<PlansPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/dash" replace />} />
          </Routes>
        </div>
      </main>
      <TaskDock />
      <CommandPalette open={cmdOpen} onClose={closeCmd} navigate={navigate}
        dark={dark} onToggleDark={onToggleDark} />
    </div>
  );
}

function InnerApp({ user, setUser, dark, toggleDark }) {
  const { message } = AntdApp.useApp();

  useEffect(() => {
    api('/auth/me').then((d) => setUser(d?.user || null)).catch(() => setUser(null));
  }, []);

  const logout = async () => {
    try { await api('/auth/logout', { method: 'POST' }); } catch { /* 忽略登出接口错误 */ }
    setUser(null);
  };

  return (
    <>
      {user === undefined ? (
        <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Spin size="large" /></div>
      ) : !user ? (
        <AuthPage onAuth={(u) => { setUser(u); message.success('欢迎回来'); }} />
      ) : (
        <Shell user={user} onLogout={logout} dark={dark} onToggleDark={toggleDark} />
      )}
    </>
  );
}

export default function App() {
  const [user, setUser] = useState(undefined);
  const [dark, setDark] = useState(localStorage.getItem('gflc_dark') === '1');
  const toggleDark = () => {
    const next = !dark;
    setDark(next);
    localStorage.setItem('gflc_dark', next ? '1' : '0');
  };
  // 必须 memo：ConfigProvider 每次收到新 theme 对象都会重算 token 并触发内部 setState，
  // 未 memo 时与 React 19 组合会直接撞上 "Maximum update depth exceeded"（#185）白屏。
  const antdConfig = useMemo(() => ({
    algorithm: dark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
    token: {
      colorPrimary: dark ? '#8ab4d0' : '#1f4d6b',
      colorBgBase: dark ? '#0f0e0c' : '#f7f4ee',
      colorBgContainer: dark ? '#1c1915' : '#fdfbf7',
      colorText: dark ? '#ece5d8' : '#1f1b16',
      colorTextSecondary: dark ? '#bcb3a3' : '#4a4238',
      colorBorder: dark ? 'rgba(236,229,216,.13)' : 'rgba(31,27,22,.14)',
      colorSuccess: dark ? '#6fb08c' : '#2f6b4f',
      colorWarning: dark ? '#d8ab63' : '#8a6220',
      colorError: dark ? '#e0776d' : '#a8322c',
      borderRadius: 8,
      fontSize: 13.5,
      fontFamily: '"PingFang SC","Microsoft YaHei UI","Microsoft YaHei",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
      controlHeight: 34,
    },
    components: {
      Table: { headerBg: 'transparent', headerColor: 'var(--muted-foreground)', rowHoverBg: 'var(--accent)' },
      Tabs: { horizontalItemGutter: 18 },
    },
  }), [dark]);
  return (
    <ConfigProvider theme={antdConfig}>
      <AntdApp>
        <InnerApp user={user} setUser={setUser} dark={dark} toggleDark={toggleDark} />
      </AntdApp>
    </ConfigProvider>
  );
}
