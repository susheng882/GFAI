import React, { useCallback, useEffect, useState } from 'react';
import { App as AntdApp, Button, Drawer, Dropdown, Input, Segmented, Select } from 'antd';
import {
  DownOutlined, EditOutlined, FileAddOutlined, FileTextOutlined, FolderOutlined,
  FolderOpenOutlined, MenuFoldOutlined, MenuUnfoldOutlined, PlusOutlined,
  RightOutlined, RobotOutlined,
} from '@ant-design/icons';
import { api } from '../api.js';
import { esc } from '../utils.js';
import { useCollapsible } from '../hooks.js';
import { useSearchParams } from 'react-router-dom';
import Markdown from '../components/Markdown.jsx';
import EmptyState from '../components/EmptyState.jsx';
import {
  AI_MODES, AnchorBar, AiQuickView, NOTE_TEMPLATES, NoteAside, TemplatePicker, VaultStatusBar,
  parseAnchorLines,
} from '../components/NotesBlocks.jsx';

/* 三栏断点：≥1440 并排三栏；760–1439 右栏进抽屉；<760 单列堆叠。
   取 1440 而非 1280，是因为左导航 240 + 页边 56 会先吃掉视口：
   1280 视口只剩 984px，放不下 240 + 560 + 280 + 24，必然横向滚动。 */
const useLayoutMode = () => {
  const read = () => {
    if (typeof window === 'undefined') return 'wide';
    if (window.matchMedia('(max-width: 760px)').matches) return 'mobile';
    if (window.matchMedia('(max-width: 1439px)').matches) return 'mid';
    return 'wide';
  };
  const [mode, setMode] = useState(read);
  useEffect(() => {
    const mqs = [window.matchMedia('(max-width: 760px)'), window.matchMedia('(max-width: 1439px)')];
    const sync = () => setMode(read());
    mqs.forEach((mq) => mq.addEventListener('change', sync));
    return () => {
      mqs.forEach((mq) => mq.removeEventListener('change', sync));
    };
  }, []);
  return mode;
};

/* 笔记：文件夹树 + 笔记列表（分页）+ Markdown 编辑/预览 + AI 协作补写 + AI 整理。 */
export default function NotesPage() {
  const { message, modal } = AntdApp.useApp();
  // 支持 /notes?note=<id> 直达：复习页「来源」链接跳到对应笔记
  const [searchParams] = useSearchParams();
  const [folders, setFolders] = useState([]);
  const [notes, setNotes] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [folderId, setFolderId] = useState(null);
  const [current, setCurrent] = useState(null);
  const [preview, setPreview] = useState(false);
  const [aiMode, setAiMode] = useState('improve');
  const [aiText, setAiText] = useState('');
  const [thread, setThread] = useState([]);
  const [tidy, setTidy] = useState(null);
  const [links, setLinks] = useState({ outgoing: [], backlinks: [] });
  const [rightTab, setRightTab] = useState('links');
  const [q, setQ] = useState('');
  // 笔记左右栏折叠：状态记忆到 localStorage，刷新后保持
  const [leftCollapsed, toggleLeft] = useCollapsible('gflc_notes_left', false);
  const [rightCollapsed, toggleRight] = useCollapsible('gflc_notes_right', false);
  // 窄屏（<1440）右栏不进网格，改由抽屉承载
  const mode = useLayoutMode();
  const drawerRight = mode !== 'wide';
  const [rightOpen, setRightOpen] = useState(false);
  /* 三栏宽度：目录 240 / 正文 min 560 / 侧栏 280；折叠项直接不占列 */
  const gridCols = mode === 'mobile'
    ? '1fr'
    : [
      ...(leftCollapsed ? [] : ['240px']),
      mode === 'wide' ? 'minmax(560px, 1fr)' : 'minmax(0, 1fr)',
      ...(mode === 'wide' && !rightCollapsed ? ['280px'] : []),
    ].join(' ');
  const [openFolders, setOpenFolders] = useState(new Set());
  const toggleFolder = (id) => setOpenFolders((cur) => {
    const next = new Set(cur); next.has(id) ? next.delete(id) : next.add(id); return next;
  });
  // B14c 模板库 / B14d AI 速览 / B12 成卡行 / B1 vault 状态条
  const [templateOpen, setTemplateOpen] = useState(false);
  const [quickView, setQuickView] = useState('');
  const [quickNoteId, setQuickNoteId] = useState(null);
  const [quickBusy, setQuickBusy] = useState(false);
  const [anchorAck, setAnchorAck] = useState({});
  const [anchorBusy, setAnchorBusy] = useState(false);
  const [vaultInfo, setVaultInfo] = useState(null);
  const [vaultError, setVaultError] = useState('');
  const [vaultPending, setVaultPending] = useState(() => Number(localStorage.getItem('gflc_vault_pending') || 0));

  const loadLinks = useCallback(async (id) => {
    if (!id) { setLinks({ outgoing: [], backlinks: [] }); return; }
    try { setLinks(await api(`/notes/${id}/links`) || { outgoing: [], backlinks: [] }); }
    catch { setLinks({ outgoing: [], backlinks: [] }); }
  }, []);
  useEffect(() => { loadLinks(current?.id); }, [current?.id, loadLinks]);

  /* 把 [[标题]] / [[笔记#^块锚]] 预处理成可点链接；点击由 Markdown.jsx 派发跳转事件 */
  const withWiki = (md) => (md || '').replace(/\[\[([^\]\n]{1,80})\]\]/g, (_, raw) => {
    const m = raw.match(/^(.+)#\^([A-Za-z0-9_-]{1,40})$/);
    return m
      ? `[${raw}](#block:${encodeURIComponent(m[1])}--${encodeURIComponent(m[2])})`
      : `[${raw}](#wiki:${encodeURIComponent(raw)})`;
  });
  const openNoteByTitle = async (title, anchor) => {
    if (!title) return;
    try {
      const rows = await api(`/notes?q=${encodeURIComponent(title)}&limit=50`);
      const hit = (rows || []).find((n) => (n.title || '').trim() === title) || (rows || [])[0];
      if (!hit) { message.warning(`没有找到标题为「${title}」的笔记`); return; }
      setCurrent(hit); setThread([]);
      if (anchor) {
        setPreview(true);
        setTimeout(() => {
          const el = document.getElementById('blk-' + anchor);
          if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          else message.info('目标块未找到，可能该笔记没有这个块锚');
        }, 80);
      }
    } catch (err) { message.error(err.message); }
  };

  const flatFolders = (nodes, depth = 0, out = []) => {
    (nodes || []).forEach((n) => {
      out.push({ id: n.id, label: `${'　'.repeat(depth)}${n.name}` });
      flatFolders(n.children, depth + 1, out);
    });
    return out;
  };

  const renameNote = (n) => {
    let title = n.title || '';
    modal.confirm({
      title: '重命名笔记', content: <Input defaultValue={title} autoFocus onChange={(e) => { title = e.target.value; }} />,
      okText: '保存', cancelText: '取消',
      onOk: async () => {
        if (!title.trim()) return;
        try { await api(`/notes/${n.id}`, { method: 'PATCH', body: JSON.stringify({ title: title.trim() }) });
          if (current?.id === n.id) setCurrent({ ...current, title: title.trim() });
          await loadNotes(); message.success('已重命名'); } catch (e) { message.error(e.message); }
      },
    });
  };
  const moveNote = (n) => {
    let target = n.folder_id ?? null;
    const opts = [{ id: null, label: '（根目录）' }, ...flatFolders(folders)];
    modal.confirm({
      title: '移动到文件夹',
      content: <Select style={{ width: '100%' }} defaultValue={target} options={opts.map((o) => ({ value: o.id, label: o.label }))}
        onChange={(v) => { target = v; }} />,
      okText: '移动', cancelText: '取消',
      onOk: async () => {
        try { await api(`/notes/${n.id}`, { method: 'PATCH', body: JSON.stringify({ folder_id: target }) });
          await loadNotes(); await loadFolders(); message.success('已移动'); } catch (e) { message.error(e.message); }
      },
    });
  };
  const copyNote = async (n) => {
    try { const r = await api(`/notes/${n.id}/duplicate`, { method: 'POST' });
      await loadNotes(); setCurrent(r); message.success('已复制'); } catch (e) { message.error(e.message); }
  };
  const exportNote = (n) => { window.open(`/api/notes/${n.id}/export`, '_blank'); };
  const removeNote = (n) => modal.confirm({
    title: `删除《${n.title || '未命名'}》？`, okText: '删除', okButtonProps: { danger: true }, cancelText: '取消',
    onOk: async () => {
      try { await api(`/notes/${n.id}`, { method: 'DELETE' });
        if (current?.id === n.id) setCurrent(null);
        await loadNotes(); message.success('已删除'); } catch (e) { message.error(e.message); }
    },
  });
  const noteMenu = (n) => ({
    items: [
      { key: 'rename', label: '重命名' }, { key: 'move', label: '移动到…' },
      { key: 'copy', label: '复制一份' }, { key: 'export', label: '导出 Markdown' },
      { type: 'divider' }, { key: 'delete', label: '删除', danger: true },
    ],
    onClick: ({ key, domEvent }) => {
      domEvent.stopPropagation();
      if (key === 'rename') renameNote(n);
      if (key === 'move') moveNote(n);
      if (key === 'copy') copyNote(n);
      if (key === 'export') exportNote(n);
      if (key === 'delete') removeNote(n);
    },
  });

  const loadFolders = useCallback(async () => {
    try { setFolders(await api('/notes/folders') || []); } catch { setFolders([]); }
  }, []);
  const loadNotes = useCallback(async () => {
    try {
      const qs = `?limit=300${folderId ? `&folder_id=${folderId}` : ''}`;
      const r = await api('/notes' + qs);
      const list = (r && r.items) ? r.items : (r || []);
      setNotes(list); setTotal((r && r.total) || list.length);
    } catch { setNotes([]); setTotal(0); }
  }, [page, folderId, q]);
  useEffect(() => { loadFolders(); }, [loadFolders]);
  useEffect(() => { loadNotes(); }, [loadNotes]);

  const createNote = async (tplKey = 'blank') => {
    const tpl = NOTE_TEMPLATES.find((t) => t.key === tplKey) || NOTE_TEMPLATES[0];
    try {
      const n = await api('/notes', { method: 'POST', body: JSON.stringify({
        title: tpl.key === 'blank' ? '未命名笔记' : tpl.name,
        content: tpl.content, folder_id: folderId, source: 'manual',
      }) });
      message.success('已新建笔记');
      setCurrent(n); setThread([]); setPreview(false); await loadNotes();
    } catch (e) { message.error(e.message); }
  };
  /* 新笔记：正文插入一条可编辑的成卡行示例，接口同步仍由「同步卡片」显式触发 */
  const insertAnchorExample = async () => {
    if (!current) return;
    const next = (current.content || '').replace(/\s*$/, '') + '\n\n关键特征 :: 对应做法';
    setCurrent({ ...current, content: next });
    message.info('已插入成卡行，保存后即可同步');
  };
  const createFolder = async () => {
    let name = '';
    modal.confirm({
      title: '新建文件夹', content: <Input placeholder="如：考研 / 数学 / 极限" autoFocus onChange={(e) => { name = e.target.value; }} />,
      okText: '创建', cancelText: '取消',
      onOk: async () => {
        if (!name.trim()) return;
        try { await api('/notes/folders', { method: 'POST', body: JSON.stringify({ name: name.trim(), parent_id: folderId }) }); message.success('已创建'); await loadFolders(); }
        catch (e) { message.error(e.message); }
      },
    });
  };
  const save = async () => {
    if (!current) return;
    try {
      const r = await api(`/notes/${current.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ title: current.title || '未命名', content: current.content || '', summary: current.summary || '' }),
      });
      setCurrent(r); message.success('已保存'); await loadNotes();
      if (vaultInfo?.dir && !vaultError) {
        setVaultPending((p) => {
          const n = p + 1;
          localStorage.setItem('gflc_vault_pending', String(n));
          return n;
        });
      }
    } catch (e) { message.error(e.message); }
  };
  const toCards = async () => {
    if (!current) return;
    try { const r = await api(`/notes/${current.id}/to-cards`, { method: 'POST' }); message.success(`已生成 ${r.cards || 0} 张卡片`); }
    catch (e) { message.error(e.message); }
  };
  const aiSuggest = async () => {
    if (!current) return;
    try {
      const r = await api('/notes/ai-suggest', {
        method: 'POST',
        body: JSON.stringify({ note_id: current.id, title: current.title, content: current.content, instruction: aiText, mode: aiMode }),
      });
      const text = r.suggestion || r.text || '';
      setThread((t) => [...t, { role: 'me', text: aiText || AI_MODES.find((m) => m.value === aiMode)?.label }, { role: 'ai', text }]);
    } catch (e) { message.error(e.message); }
  };
  const insert = async (idx, position) => {
    const text = thread[idx]?.text;
    if (!text || !current) return;
    try {
      const r = await api('/notes/insert', { method: 'POST', body: JSON.stringify({ note_id: current.id, text, position }) });
      setCurrent(r); message.success(position === 'replace' ? '已替换全文' : '已插入');
    } catch (e) { message.error(e.message); }
  };
  const runTidy = async () => {
    try {
      const r = await api('/notes/tidy', { method: 'POST', body: JSON.stringify({ folder_id: folderId }) });
      setTidy(r);
      // 接口要求至少 2 篇笔记，前端给出可读提示而不是红色报错
      if (!r || (!(r.folders || []).length && !(r.merge || []).length)) {
        message.info('这个文件夹还没有可整理的归纳建议');
      }
    } catch (e) { message.error(e.message); }
  };
  /* 顶部「AI 润色本篇」：固定改进模式调用已有 /notes/ai-suggest，结果进线程预览，可插入应用。 */
  const polishCurrent = async () => {
    if (!current) { message.info('先选一篇笔记'); return; }
    try {
      const r = await api('/notes/ai-suggest', {
        method: 'POST',
        body: JSON.stringify({ note_id: current.id, title: current.title, content: current.content, instruction: '润色这篇笔记，保留原意、改善表达', mode: 'improve' }),
      });
      const text = r?.suggestion || r?.text || '';
      setThread((t) => [...t, { role: 'me', text: '润色本篇' }, { role: 'ai', text }]);
      setRightTab('ai');
      // 窄屏右栏在抽屉里，先打开抽屉再切到 AI；宽屏保证侧栏没被折叠
      if (drawerRight) setRightOpen(true);
      else if (rightCollapsed) toggleRight();
      if (!text) message.info('这次没有给出修改建议');
    } catch (e) { message.error(e.message); }
  };
  /* B1 笔记页状态条：显式同步，不伪装成实时双向 */
  const syncVault = async () => {
    setVaultError('');
    try {
      const r = await api('/notes/vault/export', { method: 'POST' });
      setVaultPending(0); localStorage.setItem('gflc_vault_pending', '0');
      localStorage.setItem('gflc_vault_last', new Date().toISOString());
      message.success(`已同步 ${r?.written ?? 0} 篇到本地库`);
    } catch (e) { setVaultError(e.message); message.error(e.message); }
  };
  /* B12 成卡行同步：后端 card_anchors 接口未上线时只提示，不模拟成功 */
  const syncAnchors = async () => {
    if (!current) return;
    const anchors = parseAnchorLines(current.content);
    setAnchorBusy(true);
    try {
      await api(`/notes/${current.id}/anchors/apply`, {
        method: 'POST', body: JSON.stringify({ anchors }),
      });
      const ack = {};
      anchors.forEach((a) => { ack[a.hash] = true; });
      setAnchorAck(ack);
      localStorage.setItem(`gflc_anchor_ack_${current.id}`, JSON.stringify(ack));
      message.success(`已同步 ${anchors.length} 条成卡行`);
    } catch (e) {
      // 接口已实现（POST /notes/{id}/anchors/apply）；404/405 仅代表后端版本过旧
      if (e.status === 404 || e.status === 405) {
        message.warning(`已识别 ${anchors.length} 条成卡行，但当前后端版本不支持同源同步，请升级后端后重试`);
      } else message.error(e.message);
    } finally { setAnchorBusy(false); }
  };
  /* B14d 文档级速览：复用已有 ai-suggest，结果贴在正文上方 */
  const runQuickView = async () => {
    if (!current) { message.info('先选一篇笔记'); return; }
    setQuickBusy(true);
    try {
      const r = await api('/notes/ai-suggest', {
        method: 'POST',
        body: JSON.stringify({
          note_id: current.id, title: current.title, content: current.content,
          instruction: '用两三句话概括这篇笔记的核心内容，只输出摘要正文，不要标题和列表符号',
          mode: 'summarize',
        }),
      });
      const text = r?.suggestion || r?.text || '';
      setQuickView(text); setQuickNoteId(current.id);
      if (!text) message.info('这次没有生成摘要');
    } catch (e) { message.error(e.message); } finally { setQuickBusy(false); }
  };
  const applyTidy = async (g) => {
    try {
      await api('/notes/tidy/apply', { method: 'POST', body: JSON.stringify({ name: g.name, note_ids: g.note_ids, folder_id: folderId }) });
      message.success('已整理'); setTidy(null); await loadFolders(); await loadNotes();
    } catch (e) { message.error(e.message); }
  };

  // vault 状态读取 + 双链/块锚跳转 + 命令面板指令（B1 / B14b / B13）
  useEffect(() => {
    api('/notes/vault').then((s) => setVaultInfo(s || null)).catch(() => setVaultInfo(null));
  }, []);
  // /notes?note=<id> 直达：复习页「来源」链接打开对应笔记（id 非法时静默忽略）
  useEffect(() => {
    const raw = searchParams.get('note');
    const id = Number(raw);
    if (!raw || !Number.isFinite(id) || id <= 0) return;
    let alive = true;
    api(`/notes/${id}`)
      .then((n) => { if (alive && n) { setCurrent(n); setThread([]); } })
      .catch(() => { /* 笔记不存在或已删除：保持当前视图，不报错 */ });
    return () => { alive = false; };
  }, [searchParams]);
  useEffect(() => {
    if (!current?.id) { setAnchorAck({}); return; }
    try { setAnchorAck(JSON.parse(localStorage.getItem(`gflc_anchor_ack_${current.id}`) || '{}')); }
    catch { setAnchorAck({}); }
  }, [current?.id]);
  useEffect(() => {
    const onJump = (e) => openNoteByTitle(e.detail?.title, e.detail?.anchor);
    const onCmd = (e) => {
      if (e.detail?.cmd === 'new-note') setTemplateOpen(true);
      if (e.detail?.cmd === 'tidy') runTidy();
    };
    window.addEventListener('gflc:note-jump', onJump);
    window.addEventListener('gflc:cmd', onCmd);
    return () => {
      window.removeEventListener('gflc:note-jump', onJump);
      window.removeEventListener('gflc:cmd', onCmd);
    };
  });

  /* 一体树：文件夹节点下直接挂笔记，像文件管理器 */
  const notesOf = (fid) => notes.filter((n) => (n.folder_id ?? null) === (fid ?? null));
  const renderTree = (nodes, depth = 0) => (
    <>
      {depth === 0 && notesOf(null).map((n) => (
        <div key={'n' + n.id} className={'tnode note' + (current?.id === n.id ? ' on' : '')}
          style={{ '--d': depth }} onClick={() => { setCurrent(n); setThread([]); }}>
          <span className="tic"><FileTextOutlined /></span><span className="tlabel">{esc(n.title || '未命名')}</span>
        </div>
      ))}
      {(nodes || []).map((node) => (
        <React.Fragment key={node.id}>
          <div className={'tnode' + (folderId === node.id ? ' on' : '')} style={{ '--d': depth }}
            onClick={() => { setFolderId(node.id); setPage(1); }}>
            <span className="tic">{openFolders.has(node.id) ? <FolderOpenOutlined /> : <FolderOutlined />}</span>
            <span className="tlabel">{esc(node.name)}</span>
            <span className="cnt">{noteCountDeep(node.id)}</span>
            <span className="tarrow" onClick={(e) => { e.stopPropagation(); toggleFolder(node.id); }}>
              {openFolders.has(node.id) ? <DownOutlined /> : <RightOutlined />}
            </span>
          </div>
          {openFolders.has(node.id) && (
            <>
              {notesOf(node.id).map((n) => (
                <div key={'n' + n.id} className={'tnode note' + (current?.id === n.id ? ' on' : '')}
                  style={{ '--d': depth + 1 }} onClick={() => { setCurrent(n); setThread([]); }}>
                  <span className="tic"><FileTextOutlined /></span><span className="tlabel">{esc(n.title || '未命名')}</span>
                </div>
              ))}
              {renderTree(node.children || [], depth + 1)}
            </>
          )}
        </React.Fragment>
      ))}
    </>
  );

  const noteCountDeep = (fid) => {
    const ids = new Set([fid]);
    let grew = true;
    while (grew) {
      grew = false;
      folders.forEach((f) => {
        if (f.parent_id && ids.has(f.parent_id) && !ids.has(f.id)) { ids.add(f.id); grew = true; }
      });
    }
    return notes.filter((n) => ids.has(n.folder_id)).length;
  };

  const anchors = parseAnchorLines(current?.content);
  /* 顶部工具条：只留左右栏开关 + 一个 AI 入口（三件套收进下拉） */
  const aiMenu = {
    items: [
      { key: 'quick', label: quickBusy ? 'AI 速览（生成中）' : 'AI 速览', icon: <FileTextOutlined /> },
      { key: 'tidy', label: 'AI 整理文件夹', icon: <FolderOpenOutlined /> },
      { key: 'polish', label: 'AI 润色本篇', icon: <EditOutlined /> },
    ],
    onClick: ({ key }) => {
      if (key === 'quick') runQuickView();
      if (key === 'tidy') runTidy();
      if (key === 'polish') polishCurrent();
    },
  };
  const aside = (
    <NoteAside note={current} links={links} tab={rightTab} onTabChange={setRightTab}
      thread={thread} onInsert={insert} onDiscard={(i) => setThread(thread.filter((_, j) => j !== i))}
      onSelectNote={(n) => {
        if (!n?.id) { message.warning('同名笔记不存在'); return; }
        setCurrent(n); setThread([]);
      }}
      aiMode={aiMode} onAiModeChange={setAiMode}
      aiText={aiText} onAiTextChange={setAiText} onAiSuggest={aiSuggest} />
  );
  return (
    <div className="notes-page">
      <div className="notes-toolbar">
        <div className="row" style={{ gap: 4 }}>
          <Button size="small" type="text" icon={leftCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={toggleLeft}>{leftCollapsed ? '展开目录' : '收起目录'}</Button>
          <Button size="small" type="text"
            icon={drawerRight || rightCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => { if (drawerRight) setRightOpen(true); else toggleRight(); }}>
            {drawerRight ? '侧栏' : rightCollapsed ? '展开侧栏' : '收起侧栏'}
          </Button>
        </div>
        <Dropdown menu={aiMenu} trigger={['click']} placement="bottomRight">
          <Button size="small" icon={<RobotOutlined />}>
            AI<DownOutlined style={{ fontSize: 10, marginLeft: 4 }} />
          </Button>
        </Dropdown>
      </div>
      <div className={'notebar' + (leftCollapsed ? ' no-left' : '') + (rightCollapsed ? ' no-right' : '')}
        style={{ gridTemplateColumns: gridCols }}>
        {!leftCollapsed && (
        <div className="pane folder-pane tree-pane">
        <VaultStatusBar
          state={vaultError ? 'error' : !vaultInfo?.dir ? 'off' : vaultPending > 0 ? 'pending' : 'on'}
          pending={vaultPending}
          onSync={syncVault}
          onConnect={() => { window.location.href = '/settings'; }}
        />
        <div className="pane-head">
          <span>目录</span>
          <span className="row" style={{ gap: 2 }}>
            <Button size="small" type="text" icon={<RobotOutlined />} title="AI 整理这个文件夹" onClick={runTidy} />
            <Button size="small" type="text" icon={<PlusOutlined />} title="新建文件夹" onClick={createFolder} />
            <Button size="small" type="text" icon={<FileAddOutlined />} title="新建笔记" onClick={() => setTemplateOpen(true)} />
          </span>
        </div>
        <Input size="small" allowClear placeholder="搜索标题或正文…" value={q}
          onChange={(e) => setQ(e.target.value)}
          onPressEnter={() => { setPage(1); loadNotes(); }}
          style={{ margin: '6px 8px' }} />
        <div className="pane-body tree-body">
          <div className={'fnode' + (folderId ? '' : ' on')}
            onClick={() => { setFolderId(null); setPage(1); }}>
            <span>全部笔记</span><span className="cnt">{total}</span>
          </div>
          {renderTree(folders, 0)}
          {!folders.length && !notes.length && (
            <div className="muted" style={{ fontSize: 11.5, padding: '4px 8px' }}>还没有笔记</div>
          )}
        </div>
      </div>
        )}

      <div className="pane">
        {current ? (
          <div className="editor">
            <div className="editor-head">
              <Input style={{ flex: 1, minWidth: 120 }} value={current.title || ''} onChange={(e) => setCurrent({ ...current, title: e.target.value })} placeholder="笔记标题" />
              <Segmented size="small" value={preview ? 'view' : 'edit'} onChange={(v) => {
                if (!preview && document.getElementById('noteContent')) current.content = document.getElementById('noteContent').value;
                setPreview(v === 'view');
              }} options={[{ label: '编辑', value: 'edit' }, { label: '预览', value: 'view' }]} />
              <Button size="small" type="primary" onClick={save}>保存</Button>
              <Button size="small" onClick={toCards}>转卡片</Button>
            </div>
            {quickView && quickNoteId === current.id && (
              <AiQuickView text={quickView} busy={quickBusy} onRefresh={runQuickView}
                onClose={() => setQuickView('')}
                onCopy={() => { navigator.clipboard?.writeText(quickView); message.success('已复制速览'); }} />
            )}
            <div className="editor-body" id="noteBody">
              {preview ? (
                <>
                  <Markdown text={withWiki(current.content || current.summary || '')} />
                  {anchors.length > 0 && (
                    <div className="anchor-sources">
                      {anchors.slice(0, 3).map((a) => (
                        <span key={a.line} className="as-item">来源：{esc(current.title || '未命名')} · 第 {a.line} 行</span>
                      ))}
                      {anchors.length > 3 && <span className="as-more">+{anchors.length - 3}</span>}
                    </div>
                  )}
                </>
              ) : (
                <textarea id="noteContent" value={current.content || ''} placeholder="用 Markdown 写：# 标题 / - 要点 / **重点**"
                  onChange={(e) => setCurrent({ ...current, content: e.target.value })} />
              )}
            </div>
            <AnchorBar anchors={anchors} syncedHashes={anchorAck}
              onSync={syncAnchors} onInsert={insertAnchorExample} busy={anchorBusy} />
          </div>
        ) : (
          <EmptyState title="还没有打开笔记"
            desc="笔记用来记概念、错题与摘录，写完可以转成卡片。"
            action="新建笔记" onAction={() => setTemplateOpen(true)} />
        )}
      </div>

      {mode === 'wide' && !rightCollapsed && (
        <div className="pane">{aside}</div>
      )}

      {drawerRight && (
        <Drawer open={rightOpen} onClose={() => setRightOpen(false)} placement="right"
          width={mode === 'mobile' ? 300 : 320} title={null}
          styles={{ header: { padding: '8px 12px', minHeight: 0, borderBottom: '1px solid var(--border)' }, body: { padding: 0, display: 'flex' } }}>
          <div className="pane" style={{ flex: 1, border: 0, borderRadius: 0 }}>{aside}</div>
        </Drawer>
      )}

      {tidy && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.4)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}
          onClick={() => setTidy(null)}>
          <div className="v3-card" style={{ maxWidth: 560, width: '100%', maxHeight: '80vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <div className="v3-sh">AI 整理建议 · {tidy.folder || '全部笔记'}（扫描 {tidy.scanned} 篇）</div>
            {(tidy.folders || []).map((g, i) => (
              <div className="v3-resume" key={'f' + i}>
                <div className="v3-rt"><div className="a">{esc(g.name || '新分类')}</div><div className="b">{(g.titles || []).join(' + ')}</div></div>
                <Button size="small" onClick={() => applyTidy({ name: g.name, note_ids: g.note_ids })}>应用</Button>
              </div>
            ))}
            {(tidy.merge || []).map((g, i) => (
              <div className="v3-resume" key={'m' + i}>
                <div className="v3-rt"><div className="a">可合并</div><div className="b">{(g.titles || []).join(' + ')}</div></div>
              </div>
            ))}
            <Button style={{ marginTop: 12 }} onClick={() => setTidy(null)}>关闭</Button>
          </div>
        </div>
      )}
      <TemplatePicker open={templateOpen} onCancel={() => setTemplateOpen(false)}
        onCreate={(key) => { setTemplateOpen(false); createNote(key); }} />
      </div>
    </div>
  );
}
