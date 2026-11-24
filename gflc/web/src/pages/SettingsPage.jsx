import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  App as AntdApp, Alert, Button, Descriptions, Empty, Form, Input, InputNumber, Modal,
  Select, Space, Switch, Table, Tabs, Tag,
} from 'antd';
import {
  CloudUploadOutlined, CopyOutlined, DatabaseOutlined, DownloadOutlined, FolderOpenOutlined, SyncOutlined,
} from '@ant-design/icons';
import { api, downloadText } from '../api.js';
import { esc } from '../utils.js';

/* 设置中心（对标 BiliNote）：供应商 / 模型 / 转录器 / Cookie / 诊断 / 监控。
   所有密钥由后端加密存储，这里只会看到掩码。 */
const PURPOSES = [
  { value: 'note', label: '笔记生成' }, { value: 'vision', label: '视觉识图' },
  { value: 'long', label: '长文理解' }, { value: 'chat', label: '对话' },
];
const KINDS = [{ value: 'ark', label: '火山方舟' }, { value: 'deepseek', label: 'DeepSeek' },
  { value: 'openai', label: 'OpenAI 兼容' }, { value: 'groq', label: 'Groq' }];

/* 告警阈值来源：/settings/alerts 的 thresholds.*.source 有三种形态 ——
   default（内置默认值）/ env:NAME（环境变量覆盖）/ invalid(NAME)->default（变量写了但解析失败）。
   这里把机器码翻成中文，阈值数字本身仍用接口返回值，不在前端硬编码。 */
function thresholdSourceText(t) {
  const s = String(t?.source || 'default');
  if (s === 'default') return '默认阈值';
  if (s.startsWith('env:')) return `环境变量 ${s.slice(4)}`;
  if (s.startsWith('invalid')) return t?.env ? `变量 ${t.env} 取值非法，已回退默认` : '变量取值非法，已回退默认';
  return s;
}

/* 告警数值口径：失败率转百分比、成本带货币符号、积压取整；null/NaN 一律显示 0，不留空白 */
function alertValueText(code, v) {
  const n = Number(v);
  const safe = Number.isFinite(n) ? n : 0;
  if (code === 'FAILURE_RATE') return `${(safe * 100).toFixed(1)}%`;
  if (code === 'DAILY_COST') return `¥${safe.toFixed(2)}`;
  return String(Math.round(safe));
}

/* 超限后的下一步动作：只说看哪里，不臆造结论 */
const ALERT_ADVICE = {
  FAILURE_RATE: '查看下方「最近失败」核对失败原因',
  QUEUE_BACKLOG: '检查 Worker 健康状态与视频并发设置',
  DAILY_COST: '查看下方「模型用量」核对调用成本',
};

/* 备份恢复：只在页面上给出运维命令，不调用任何后端接口执行 shell。
   路径按仓库默认部署口径书写，实际部署时按环境替换。 */
const BACKUP_CMDS = [
  {
    key: 'backup', label: '创建备份',
    cmd: 'python gflc/scripts/backup_restore.py backup --db-path gflc/backend/data/gflc.db --storage-dir gflc/backend/data/uploads --backup-dir gflc/backups',
    note: '在线安全备份 SQLite，并复制对象存储目录；产出 manifest.json 记录 sha256',
  },
  {
    key: 'verify', label: '校验备份',
    cmd: 'python gflc/scripts/backup_restore.py verify --backup-dir gflc/backups --backup-id <时间戳>',
    note: '按清单逐项比对数据库与存储文件的哈希',
  },
  {
    key: 'restore', label: '恢复（需显式确认）',
    cmd: 'python gflc/scripts/backup_restore.py restore --backup-dir gflc/backups --backup-id <时间戳> --db-path gflc/backend/data/gflc.db --storage-dir gflc/backend/data/uploads --confirm',
    note: '不带 --confirm 拒绝写盘；建议先加 --dry-run 只打印计划，恢复前会自动保留 .pre-restore 副本',
  },
  {
    key: 'drill', label: '恢复演练',
    cmd: 'bash gflc/scripts/drill.sh',
    note: '在临时目录用样本数据走备份→破坏→恢复→校验，输出仅为本机参考值',
  },
];

export default function SettingsPage() {
  const { message } = AntdApp.useApp();
  const [tab, setTab] = useState('providers');
  const [providers, setProviders] = useState([]);
  const [models, setModels] = useState([]);
  const [runtime, setRuntime] = useState({});
  const [cookies, setCookies] = useState([]);
  const [diag, setDiag] = useState(null);
  const [mon, setMon] = useState(null);
  // B15 告警：null 表示「没取到或还没取」，此时整块不渲染，避免空壳与报红
  const [alerts, setAlerts] = useState(null);
  const [editProv, setEditProv] = useState(null);
  const [editModel, setEditModel] = useState(null);
  const [busy, setBusy] = useState(false);
  const [cookieDraft, setCookieDraft] = useState({});
  const [rtDraft, setRtDraft] = useState({});
  // 账号数据：导出与注销（后端已有 /auth/export、/auth/delete，需二次确认）
  const [exportBusy, setExportBusy] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  // B1 本地文件库：状态四态由 dir / 错误 / 待同步数派生，不做静默覆盖
  const [vault, setVault] = useState(null);
  const [vaultDir, setVaultDir] = useState('');
  const [vaultAuto, setVaultAuto] = useState(() => localStorage.getItem('gflc_vault_auto') !== '0');
  const [vaultEnabled, setVaultEnabled] = useState(false);
  const [vaultError, setVaultError] = useState('');
  const [vaultPending, setVaultPending] = useState(() => Number(localStorage.getItem('gflc_vault_pending') || 0));
  const [vaultLast, setVaultLast] = useState(() => localStorage.getItem('gflc_vault_last') || '');
  const [dirName, setDirName] = useState('');
  const [importFiles, setImportFiles] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [vaultBusy, setVaultBusy] = useState(false);
  const dirHandleRef = useRef(null);
  const folderRef = useRef(null);
  const importRef = useRef(null);
  const cmdRefs = useRef({});

  const loadAll = useCallback(async () => {
    const [p, m, r, c] = await Promise.all([
      api('/settings/providers').catch(() => []), api('/settings/models').catch(() => []),
      api('/settings/runtime').catch(() => ({})), api('/settings/cookies').catch(() => []),
    ]);
    setProviders(p || []); setModels(m || []); setRuntime(r || {}); setRtDraft(r || {}); setCookies(c || []);
  }, []);
  useEffect(() => { loadAll(); }, [loadAll]);

  const loadDiag = async () => { setDiag(await api('/settings/diagnostics').catch(() => null)); };
  const loadMon = async () => { setMon(await api('/settings/monitor').catch(() => null)); };
  useEffect(() => { if (tab === 'diag') loadDiag(); if (tab === 'monitor') loadMon(); }, [tab]);

  /* 告警轮询：只在「监控」页可见时请求，切走或离开页面立即停表，间隔 30s（阈值只读、开销很小） */
  const loadAlerts = useCallback(async () => {
    try { setAlerts(await api('/settings/alerts')); } catch { setAlerts(null); }
  }, []);
  useEffect(() => {
    if (tab !== 'monitor') return undefined;
    loadAlerts();
    const timer = setInterval(loadAlerts, 30000);
    return () => clearInterval(timer);
  }, [tab, loadAlerts]);

  /* ---------- B1 本地文件库（Web 边界：显式同步，不伪装实时挂载） ---------- */
  const loadVault = useCallback(async () => {
    try {
      const s = await api('/notes/vault');
      setVault(s || null);
      setVaultDir(s?.dir || '');
      setVaultEnabled(!!s?.dir);
    } catch (e) { setVaultError(e.message); }
  }, []);
  useEffect(() => { if (tab === 'vault') loadVault(); }, [tab, loadVault]);
  const vaultState = vaultError ? 'error' : !vaultEnabled ? 'off' : vaultPending > 0 ? 'pending' : 'on';
  const markPending = (n) => {
    setVaultPending(n);
    localStorage.setItem('gflc_vault_pending', String(n));
  };

  const toggleVault = async (on) => {
    setVaultError('');
    if (!on) {
      try {
        await api('/notes/vault', { method: 'PUT', body: JSON.stringify({ dir: '', auto: false }) });
        setVaultEnabled(false); setVault((s) => ({ ...(s || {}), dir: '', exists: false }));
        message.success('已停用本地库');
      } catch (e) { setVaultError(e.message); message.error(e.message); }
      return;
    }
    if (!vaultDir.trim()) { message.info('先填写服务端目录，或点「选择本地目录」授权'); return; }
    try {
      await api('/notes/vault', { method: 'PUT', body: JSON.stringify({ dir: vaultDir.trim(), auto: vaultAuto }) });
      await loadVault(); message.success('已启用本地库');
    } catch (e) { setVaultError(e.message); message.error(e.message); }
  };
  /* Chromium 有 File System Access API：用户授权后拿到目录句柄；
     否则退化为上传文件夹（webkitdirectory）+ 显式同步。两种方式都不宣称桌面级挂载。 */
  const chooseDir = async () => {
    setVaultError('');
    if (typeof window.showDirectoryPicker === 'function') {
      try {
        const handle = await window.showDirectoryPicker({ mode: 'readwrite' });
        dirHandleRef.current = handle;
        setDirName(handle.name);
        message.success(`已授权「${handle.name}」，服务端同步仍使用下方目录路径`);
      } catch (e) { if (e.name !== 'AbortError') { setVaultError(e.message); message.error(e.message); } }
      return;
    }
    message.info('浏览器不支持目录授权，请用「上传文件夹」导入并显式同步');
    folderRef.current?.click();
  };
  const onFolderPick = (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setImportFiles(files);
    setDirName((files[0].webkitRelativePath || files[0].name).split('/')[0]);
    message.success(`已选择 ${files.length} 个本地文件，点「导入」开始同步`);
    e.target.value = '';
  };
  const readMdFiles = async (files) => {
    const out = [];
    for (const f of files) {
      if (!/\.(md|markdown|txt)$/i.test(f.name)) continue;
      const text = await f.text();
      const title = ((text.split(/\r?\n/).find((l) => /^#\s+/.test(l)) || '')
        .replace(/^#\s+/, '').trim() || f.name.replace(/\.[^.]+$/, '')).slice(0, 200);
      out.push({ title, content: text });
    }
    return out;
  };
  const finishSync = (written = 0) => {
    markPending(0);
    const now = new Date().toISOString();
    setVaultLast(now); localStorage.setItem('gflc_vault_last', now); message.success(`已同步 ${written} 篇`);
  };
  const syncVaultNow = async () => {
    setVaultError(''); setVaultBusy(true);
    try { const r = await api('/notes/vault/export', { method: 'POST' }); finishSync(r?.written ?? 0); }
    catch (e) { setVaultError(e.message); message.error(e.message); }
    finally { setVaultBusy(false); }
  };
  /* 导出：后端写服务端目录 + 浏览器下载一份 Markdown 汇总，确保「导出能下载」 */
  const exportVault = async () => {
    setVaultError(''); setVaultBusy(true);
    try {
      const r = await api('/notes/vault/export', { method: 'POST' });
      const res = await api('/notes?limit=300'); const list = (res && res.items) ? res.items : (res || []);
      const bundle = list.map((n) => `# ${n.title || '未命名'}\n\n${n.content || ''}`).join('\n\n---\n\n') || '（暂无笔记）';
      // 浏览器授权目录可直接写文件（仅 Chromium FS Access API），未授权则只走下载
      if (dirHandleRef.current) {
        try { const fh = await dirHandleRef.current.getFileHandle('gflc-notes.md', { create: true }); const w = await fh.createWritable(); await w.write(bundle); await w.close(); }
        catch (e) { message.warning('授权目录写入失败：' + e.message); }
      }
      downloadText('gflc-notes-' + new Date().toISOString().slice(0, 10) + '.md', bundle);
      finishSync(r?.written ?? list.length);
    } catch (e) { setVaultError(e.message); message.error(e.message); }
    finally { setVaultBusy(false); }
  };
  const importVault = async (picked) => {
    setVaultError(''); setVaultBusy(true);
    try {
      const parsed = await readMdFiles(picked || importFiles);
      let created = 0;
      const clash = [];
      for (const item of parsed) {
        const rows = await api(`/notes?q=${encodeURIComponent(item.title)}&limit=50`);
        const hit = (rows || []).find((n) => (n.title || '').trim() === item.title);
        if (hit) clash.push({ note: hit, content: item.content });
        else { await api('/notes', { method: 'POST', body: JSON.stringify({ title: item.title, content: item.content, source: 'import' }) }); created++; }
      }
      setConflicts(clash);
      markPending(created + clash.length);
      message.success(`已导入 ${created} 篇${clash.length ? `，${clash.length} 篇待确认冲突` : ''}`);
    } catch (e) { setVaultError(e.message); message.error(e.message); }
    finally { setVaultBusy(false); importRef.current && (importRef.current.value = ''); }
  };
  /* 冲突二选一：本地=刚上传的文件，云端=现有笔记；不静默覆盖 */
  const resolveConflicts = async (keepLocal) => {
    try {
      if (keepLocal) {
        for (const c of conflicts) {
          await api(`/notes/${c.note.id}`, { method: 'PATCH', body: JSON.stringify({ content: c.content }) });
        }
      }
      message.success(keepLocal ? `已用本地文件覆盖 ${conflicts.length} 篇` : `已保留云端 ${conflicts.length} 篇`);
      setConflicts([]); markPending(0);
    } catch (e) { setVaultError(e.message); message.error(e.message); }
  };

  const saveProvider = async (v) => {
    setBusy(true);
    try {
      if (editProv?.id) await api(`/settings/providers/${editProv.id}`, { method: 'PATCH', body: JSON.stringify(v) });
      else await api('/settings/providers', { method: 'POST', body: JSON.stringify(v) });
      setEditProv(null); await loadAll(); message.success('已保存');
    } catch (e) { message.error(e.message); } finally { setBusy(false); }
  };
  const delProvider = async (id) => {
    try { await api(`/settings/providers/${id}`, { method: 'DELETE' }); await loadAll(); message.success('已删除'); }
    catch (e) { message.error(e.message); }
  };
  const saveModel = async (v) => {
    setBusy(true);
    try {
      if (editModel?.id) await api(`/settings/models/${editModel.id}`, { method: 'PATCH', body: JSON.stringify(v) });
      else await api('/settings/models', { method: 'POST', body: JSON.stringify(v) });
      setEditModel(null); await loadAll(); message.success('已保存');
    } catch (e) { message.error(e.message); } finally { setBusy(false); }
  };
  const probe = async (id) => {
    try {
      const r = await api(`/settings/models/${id}/probe`, { method: 'POST' });
      message[r.probe_status === 'ok' ? 'success' : 'warning'](
        `${r.probe_status}${r.latency_ms ? ` · ${r.latency_ms}ms` : ''}${r.probe_note ? ` · ${r.probe_note}` : ''}`);
      await loadAll();
    } catch (e) { message.error(e.message); }
  };
  const saveRuntime = async () => {
    try { await api('/settings/runtime', { method: 'PUT', body: JSON.stringify(rtDraft) }); message.success('已生效（下一任务起）'); await loadAll(); }
    catch (e) { message.error(e.message); }
  };
  const saveCookie = async (platform) => {
    try {
      await api('/settings/cookies', { method: 'PUT', body: JSON.stringify({ platform, cookie: cookieDraft[platform] || '' }) });
      setCookieDraft((s) => ({ ...s, [platform]: '' }));
      await loadAll(); message.success('已保存（加密存储）');
    } catch (e) { message.error(e.message); }
  };

  /* 导出：后端 GET /auth/export 返回带 Content-Disposition 的文件流，
     需 confirm=true 或密码二次因子；用 window.open 走浏览器下载，避免 api() 把文件当 JSON 解析。 */
  const exportData = () => {
    setExportBusy(true);
    try { window.open('/api/auth/export?confirm=true', '_blank'); message.success('已开始下载数据归档'); }
    catch (e) { message.error(e.message); }
    finally { setExportBusy(false); }
  };
  /* 注销：后端 POST /auth/delete 需 confirm=true 或当前密码；前端已做二次确认弹窗。 */
  const confirmDelete = async () => {
    try {
      await api('/auth/delete', { method: 'POST', body: JSON.stringify({ confirm: true, password: deletePassword || undefined }) });
      message.success('账号已注销');
      setDeleteOpen(false);
      window.location.href = '/';
    } catch (e) { message.error(e.message); }
  };

  const provName = (id) => providers.find((p) => p.id === id)?.name || id;

  /* 复制命令：优先 navigator.clipboard（https 或 localhost 可用）；
     不可用时选中命令原文交给用户自行复制，不伪造「已复制」。 */
  const copyCmd = async (text, key) => {
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) throw new Error('clipboard unavailable');
      await navigator.clipboard.writeText(text);
      message.success('已复制');
      return;
    } catch { /* 走下方的选中降级 */ }
    const el = cmdRefs.current[key];
    if (el) {
      try {
        const range = document.createRange();
        range.selectNodeContents(el);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
      } catch { /* 选中失败时仍给出提示 */ }
    }
    try {
      const ok = document.execCommand && document.execCommand('copy');
      if (ok) message.success('已复制');
      else message.info('已选中命令，请按 Ctrl+C 复制');
    } catch { message.info('已选中命令，请按 Ctrl+C 复制'); }
  };

  const provCols = [
    { title: '名称', dataIndex: 'name' },
    { title: '类型', dataIndex: 'kind', width: 110, render: (v) => <Tag>{v}</Tag> },
    { title: 'Base URL', dataIndex: 'base_url', ellipsis: true },
    { title: 'Key', dataIndex: 'api_key_masked', width: 170, render: (v) => <code>{v || '—'}</code> },
    { title: '默认', dataIndex: 'is_default', width: 70, render: (v) => (v ? <Tag color="green">默认</Tag> : '') },
    { title: '启用', dataIndex: 'enabled', width: 70, render: (v) => (v ? '是' : '否') },
    {
      title: '操作', width: 130, render: (_, r) => (
        <Space size={4}>
          <Button size="small" type="link" onClick={() => setEditProv(r)}>编辑</Button>
          <Button size="small" type="link" danger onClick={() => delProvider(r.id)}>删除</Button>
        </Space>
      ),
    },
  ];

  const modelCols = [
    { title: '供应商', dataIndex: 'provider_id', width: 130, render: provName },
    { title: '模型 ID', dataIndex: 'model_id', ellipsis: true },
    { title: '用途', dataIndex: 'purpose', width: 110, render: (v) => PURPOSES.find((p) => p.value === v)?.label || v },
    { title: '默认', dataIndex: 'is_default', width: 70, render: (v) => (v ? <Tag color="green">默认</Tag> : '') },
    {
      title: '探活', dataIndex: 'probe_status', width: 110,
      render: (v, r) => <Tag color={v === 'ok' ? 'green' : v === 'not_activated' ? 'orange' : v === 'error' ? 'red' : 'default'}>{v}</Tag>,
    },
    {
      title: '操作', width: 160, render: (_, r) => (
        <Space size={4}>
          <Button size="small" type="link" onClick={() => probe(r.id)}>探测</Button>
          <Button size="small" type="link" onClick={() => setEditModel(r)}>编辑</Button>
          <Button size="small" type="link" danger
            onClick={async () => { try { await api(`/settings/models/${r.id}`, { method: 'DELETE' }); await loadAll(); } catch (e) { message.error(e.message); } }}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="v3-card" style={{ padding: 18 }}>
      <Tabs activeKey={tab} onChange={setTab} items={[
        {
          key: 'providers', label: '供应商',
          children: (
            <>
              <div className="row between" style={{ marginBottom: 10 }}>
                <span className="vmuted2">Key 由后端 Fernet 加密存储，接口只回掩码；未在库中配置时自动回落 .env。</span>
                <Button type="primary" size="small"
                  onClick={() => setEditProv({ name: '', kind: 'ark', base_url: '', api_key: '', enabled: true, is_default: false })}>
                  新建供应商
                </Button>
              </div>
              <Table rowKey="id" size="small" columns={provCols} dataSource={providers} pagination={false} />
            </>
          ),
        },
        {
          key: 'models', label: '模型',
          children: (
            <>
              <div className="row between" style={{ marginBottom: 10 }}>
                <span className="vmuted2">同一个用途只认「默认」那条；探测会真发一次请求，能识别“未开通”。</span>
                <Button type="primary" size="small"
                  onClick={() => setEditModel({ provider_id: providers[0]?.id, model_id: '', label: '', purpose: 'note', enabled: true, is_default: false })}>
                  新建模型
                </Button>
              </div>
              <Table rowKey="id" size="small" columns={modelCols} dataSource={models} pagination={false} />
            </>
          ),
        },
        {
          key: 'transcriber', label: '转录器',
          children: (
            <Form layout="vertical" style={{ maxWidth: 560 }}>
              <Form.Item label="取材策略">
                <Select value={rtDraft.transcriber} onChange={(v) => setRtDraft({ ...rtDraft, transcriber: v })}
                  options={[
                    { value: 'auto', label: 'auto：官方字幕 → 必剪云转写 → 本地 Whisper' },
                    { value: 'subtitle', label: '只用平台字幕（需 Cookie）' },
                    { value: 'bcut', label: '优先必剪云转写' },
                    { value: 'whisper', label: '只用本地 Whisper' },
                  ]} />
              </Form.Item>
              <Space size={16} wrap>
                <Form.Item label="Whisper 模型">
                  <Select style={{ width: 130 }} value={rtDraft.whisper_model}
                    onChange={(v) => setRtDraft({ ...rtDraft, whisper_model: v })}
                    options={['tiny', 'base', 'small', 'medium'].map((v) => ({ value: v, label: v }))} />
                </Form.Item>
                <Form.Item label="并行片数">
                  <InputNumber min={1} max={12} value={Number(rtDraft.whisper_parallel || 6)}
                    onChange={(v) => setRtDraft({ ...rtDraft, whisper_parallel: String(v) })} />
                </Form.Item>
                <Form.Item label="视频并发任务">
                  <InputNumber min={1} max={10} value={Number(rtDraft.video_concurrency || 5)}
                    onChange={(v) => setRtDraft({ ...rtDraft, video_concurrency: String(v) })} />
                </Form.Item>
              </Space>
              <Space size={24} wrap>
                <Form.Item label="必剪云转写">
                  <Switch checked={rtDraft.bcut_enabled === '1'}
                    onChange={(v) => setRtDraft({ ...rtDraft, bcut_enabled: v ? '1' : '0' })} />
                </Form.Item>
                <Form.Item label="网格 OCR 图文（慢，默认关）">
                  <Switch checked={rtDraft.frames_ocr === '1'}
                    onChange={(v) => setRtDraft({ ...rtDraft, frames_ocr: v ? '1' : '0' })} />
                </Form.Item>
                <Form.Item label="笔记自动配图">
                  <Switch checked={rtDraft.screenshot_enabled === '1'}
                    onChange={(v) => setRtDraft({ ...rtDraft, screenshot_enabled: v ? '1' : '0' })} />
                </Form.Item>
              </Space>
              <Button type="primary" onClick={saveRuntime}>保存并生效</Button>
            </Form>
          ),
        },
        {
          key: 'cookie', label: 'Cookie',
          children: (
            <Space direction="vertical" size={14} style={{ width: '100%', maxWidth: 720 }}>
              <Alert type="info" showIcon message="B 站 AI 字幕需要登录态：粘贴 SESSDATA=xxx 或整段 Cookie，配好后可跳过语音转写（秒级取材）。" />
              {cookies.map((c) => (
                <div key={c.platform}>
                  <div className="row between" style={{ marginBottom: 6 }}>
                    <b>{c.platform}</b>
                    <Tag color={c.has_cookie ? 'green' : 'default'}>{c.has_cookie ? '已配置' : '未配置'}</Tag>
                  </div>
                  <Space.Compact style={{ width: '100%' }}>
                    <Input.Password value={cookieDraft[c.platform] || ''} placeholder={c.has_cookie ? '已保存（重新填写可覆盖）' : 'SESSDATA=...'}
                      onChange={(e) => setCookieDraft((s) => ({ ...s, [c.platform]: e.target.value }))} />
                    <Button type="primary" onClick={() => saveCookie(c.platform)}>保存</Button>
                  </Space.Compact>
                </div>
              ))}
            </Space>
          ),
        },
        {
          key: 'diag', label: '诊断',
          children: diag ? (
            <Descriptions column={1} size="small" bordered>
              {diag.checks.map((c) => (
                <Descriptions.Item key={c.item} label={c.item}>
                  <Tag color={c.ok ? 'green' : 'red'}>{c.ok ? 'OK' : '缺失'}</Tag>
                  <span className="vmuted2">{c.detail}</span>
                </Descriptions.Item>
              ))}
              <Descriptions.Item label="运行环境">{diag.app_env} / {diag.database}</Descriptions.Item>
            </Descriptions>
          ) : <Empty description="加载中" />,
        },
        {
          key: 'monitor', label: '监控',
          children: (
            <Space direction="vertical" size={14} style={{ width: '100%' }}>
              {/* 系统状态：三类阈值告警。接口失败时 alerts=null，整块不渲染（不报红、不白屏） */}
              {alerts && (
                <div style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12 }}>
                  <div className="row between" style={{ gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 13, fontWeight: 500 }}>系统状态</span>
                    <span className="vmuted2" style={{ fontSize: 11.5, fontVariantNumeric: 'tabular-nums' }}>
                      {alerts.any_alert ? '有指标超过阈值' : '各项指标正常'} · 每 30 秒刷新
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                    {(alerts.alerts || []).map((a) => {
                      const warn = !!a.exceeded;
                      const th = alerts.thresholds || {};
                      const src = a.code === 'FAILURE_RATE' ? th.failure_rate
                        : a.code === 'QUEUE_BACKLOG' ? th.queue_backlog : th.daily_cost_cny;
                      return (
                        <div key={a.code} style={{
                          flex: '1 1 180px', minWidth: 0, padding: '8px 12px', borderRadius: 8,
                          background: 'var(--secondary)',
                        }}>
                          <div className="row between" style={{ gap: 8 }}>
                            <span style={{ fontSize: 12.5, fontWeight: 500 }}>{a.name}</span>
                            <span style={{ fontSize: 11.5, color: warn ? 'var(--warning)' : 'var(--muted-foreground)' }}>
                              {warn ? '超阈值' : '正常'}
                            </span>
                          </div>
                          <div style={{
                            marginTop: 4, fontSize: 20, fontWeight: 400, lineHeight: 1.3,
                            fontVariantNumeric: 'tabular-nums',
                            color: warn ? 'var(--warning)' : 'var(--foreground)',
                          }}>
                            {alertValueText(a.code, a.current)}
                          </div>
                          <div className="vmuted2" style={{ marginTop: 2, fontSize: 11.5, fontVariantNumeric: 'tabular-nums' }}>
                            阈值 {alertValueText(a.code, a.threshold)} · {thresholdSourceText(src)}
                          </div>
                          {warn && (
                            <div style={{ marginTop: 4, fontSize: 11.5, color: 'var(--warning)', lineHeight: 1.7 }}>
                              {ALERT_ADVICE[a.code] || '请到监控数据里核对对应指标'}
                            </div>
                          )}
                        </div>
                      );
                    })}
                    {(!alerts.alerts || alerts.alerts.length === 0) && (
                      <div className="vmuted2" style={{ fontSize: 11.5, lineHeight: 1.7 }}>
                        还没有告警指标，后端未返回数据
                      </div>
                    )}
                  </div>
                  <div className="vmuted2" style={{ marginTop: 8, fontSize: 11.5, lineHeight: 1.7 }}>
                    {alerts.any_alert
                      ? '超过阈值的指标会标黄，含义是「需要看」，不影响已有任务继续运行。'
                      : `近 ${alerts.window_hours ?? 24} 小时没有超过阈值：失败率按同一窗口统计，积压取主队列与视频队列之和，成本取近 24 小时模型调用`}
                  </div>
                </div>
              )}
              {mon ? (<>
              <div className="row" style={{ gap: 12, flexWrap: 'wrap' }}>
                <div className="v3-card" style={{ padding: '10px 16px', minWidth: 130 }}>
                  <div className="vmuted2">今日模型调用</div>
                  <div style={{ fontSize: 22 }}>{mon.today?.calls ?? 0}</div>
                </div>
                <div className="v3-card" style={{ padding: '10px 16px', minWidth: 130 }}>
                  <div className="vmuted2">今日成本（元）</div>
                  <div style={{ fontSize: 22 }}>{mon.today?.cost ?? 0}</div>
                </div>
                <div className="v3-card" style={{ padding: '10px 16px', minWidth: 130 }}>
                  <div className="vmuted2">今日 tokens</div>
                  <div style={{ fontSize: 22 }}>{mon.today?.tokens ?? 0}</div>
                </div>
                <div className="v3-card" style={{ padding: '10px 16px', minWidth: 130 }}>
                  <div className="vmuted2">队列 / 视频并发</div>
                  <div style={{ fontSize: 22 }}>{mon.worker?.queue_size ?? 0} / {mon.worker?.video_workers ?? 0}</div>
                </div>
                <Button size="small" style={{ marginLeft: 'auto' }} onClick={loadMon}>刷新</Button>
              </div>

              <Descriptions column={4} size="small" bordered>
                {Object.entries(mon.tasks_by_status || {}).map(([k, v]) => (
                  <Descriptions.Item key={k} label={`任务·${k}`}>{v}</Descriptions.Item>
                ))}
                {Object.entries(mon.tasks_by_type || {}).map(([k, v]) => (
                  <Descriptions.Item key={'t' + k} label={`类型·${k}`}>{v}</Descriptions.Item>
                ))}
              </Descriptions>

              {/* 趋势图 + 调用分布：让「用了多少」一眼可见，而不是只堆数字 */}
              <div className="row" style={{ gap: 12, flexWrap: 'wrap' }}>
                <div className="v3-card" style={{ flex: '1 1 320px', padding: 14 }}>
                  <div className="v3-sh">近 7 天用量趋势</div>
                  <MonitorTrend series={mon.cost_series || []} />
                </div>
                <div className="v3-card" style={{ flex: '1 1 260px', padding: 14 }}>
                  <div className="v3-sh">模型调用分布</div>
                  <MonitorBars models={mon.model_usage || []} />
                </div>
              </div>

              <div>
                <div className="v3-sh">模型用量（按成本排序）</div>
                <Table rowKey="model" size="small" pagination={false}
                  dataSource={mon.model_usage || []}
                  columns={[
                    { title: '模型', dataIndex: 'model', ellipsis: true },
                    { title: '调用', dataIndex: 'calls', width: 80 },
                    { title: '输入 tok', dataIndex: 'in', width: 110 },
                    { title: '输出 tok', dataIndex: 'out', width: 110 },
                    { title: '成本(元)', dataIndex: 'cost', width: 100 },
                  ]}
                  locale={{ emptyText: '还没有调用记录' }} />
              </div>
              <div>
                <div className="v3-sh">最近失败</div>
                {(!mon.recent_failures || mon.recent_failures.length === 0) && <div className="vmuted2">没有失败任务</div>}
                {(mon.recent_failures || []).map((f) => (
                  <div className="vseg" key={f.id}>
                    <span className="vt">#{f.id}</span>
                    <span>{f.type} · {esc(f.error)}</span>
                  </div>
                ))}
              </div>
              </>) : <Empty description="加载中" />}
            </Space>
          ),
        },
        {
          key: 'vault', label: '本地文件库',
          children: (
            <Space direction="vertical" size={16} style={{ width: '100%', maxWidth: 760 }}>
              <div>
                <div className="row between" style={{ marginBottom: 4 }}>
                  <div className="row" style={{ gap: 8 }}>
                    <DatabaseOutlined style={{ color: 'var(--primary)' }} />
                    <span style={{ fontSize: 14, fontWeight: 500 }}>本地文件库</span>
                    <span className={'vault-state vs-' + vaultState}>{{ off: '未启用', on: '已连接', pending: '待同步', error: '同步失败' }[vaultState]}</span>
                  </div>
                  <Switch checked={vaultEnabled} onChange={toggleVault} checkedChildren="启用" unCheckedChildren="停用" />
                </div>
                <div className="vmuted2" style={{ lineHeight: 1.8 }}>浏览器不能默认读写任意目录。Chromium 可在你授权后访问所选目录；其他浏览器用上传/下载文件夹加显式同步。服务端写入由下方目录决定，同名冲突需二选一。</div>
              </div>
              <div className="vault-status-rows"><div><span>已连接目录</span><b className="mono">{vault?.dir || '未连接'}{dirName ? ` · ${dirName}` : ''}</b></div><div><span>上次同步</span><b className="mono">{vaultLast ? new Date(vaultLast).toLocaleString('zh-CN') : '—'}</b></div><div><span>待同步变更</span><b className="mono">{vaultPending}</b></div></div>
              <div className="row" style={{ gap: 8 }}>
                <Switch size="small" checked={vaultAuto} onChange={(v) => { setVaultAuto(v); localStorage.setItem('gflc_vault_auto', v ? '1' : '0'); if (vaultDir.trim()) api('/notes/vault', { method: 'PUT', body: JSON.stringify({ dir: vaultDir.trim(), auto: v }) }).catch((e) => message.error(e.message)); }} />
                <span className="vmuted2">保存后自动写文件，关闭则只显式同步</span>
              </div>
              <Input value={vaultDir} placeholder="服务端目录，如 /data/gflc/vault"
                onChange={(e) => setVaultDir(e.target.value)} />
              <div className="row" style={{ gap: 8 }}>
                <Button icon={<FolderOpenOutlined />} onClick={chooseDir}>选择本地目录</Button>
                <Button type="primary" icon={<SyncOutlined />} loading={vaultBusy} onClick={syncVaultNow}>立即同步</Button>
                <Button icon={<DownloadOutlined />} loading={vaultBusy} onClick={exportVault}>导出</Button>
                <Button icon={<CloudUploadOutlined />} loading={vaultBusy} onClick={() => importRef.current?.click()}>导入</Button>
                <Button type="link" size="small" onClick={() => folderRef.current?.click()}>上传整个文件夹</Button>
              </div>
              <input ref={folderRef} type="file" hidden multiple webkitdirectory="" directory="" onChange={onFolderPick} />
              <input ref={importRef} type="file" hidden multiple accept=".md,.markdown,.txt" onChange={(e) => { const fs = Array.from(e.target.files || []); e.target.value = ''; if (fs.length) importVault(fs); }} />
              {importFiles.length > 0 && <div className="vmuted2">已选择 {importFiles.length} 个本地文件 · {dirName || '未命名目录'}</div>}
              {vaultError && <Alert type="warning" showIcon message={vaultError} />}
            </Space>
          ),
        },
        {
          key: 'backup', label: '数据备份',
          children: (
            <Space direction="vertical" size={16} style={{ width: '100%', maxWidth: 760 }}>
              <div>
                <div className="row" style={{ gap: 8, marginBottom: 4 }}>
                  <DatabaseOutlined style={{ color: 'var(--primary)' }} />
                  <span style={{ fontSize: 14, fontWeight: 500 }}>数据备份</span>
                  <Tag>运维命令行</Tag>
                </div>
                <div className="vmuted2" style={{ lineHeight: 1.8 }}>
                  备份与恢复由服务器上的脚本完成。本页只提供命令与状态提示，未在 Web 内执行 shell，避免服务器命令执行风险。
                </div>
              </div>

              <div style={{ border: '1px solid var(--border)', borderRadius: 8 }}>
                {[
                  ['备份脚本', 'gflc/scripts/backup_restore.py'],
                  ['演练脚本', 'gflc/scripts/drill.sh'],
                  ['执行方式', '运维登录服务器手动执行'],
                ].map(([k, v], i) => (
                  <div key={k} style={{
                    display: 'flex', gap: 12, padding: '8px 12px', alignItems: 'baseline', flexWrap: 'wrap',
                    borderBottom: i < 2 ? '1px solid var(--border)' : 0,
                  }}>
                    <span className="vmuted2" style={{ minWidth: 56 }}>{k}</span>
                    <b className="mono" style={{ fontSize: 12, fontWeight: 500, wordBreak: 'break-all' }}>{v}</b>
                  </div>
                ))}
              </div>

              <div className="vmuted2" style={{ lineHeight: 1.8 }}>
                两个脚本随仓库提供；Web 端不探测服务器文件系统，是否可用以命令输出为准。本页不读取备份目录，也不记录上次备份时间。
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {BACKUP_CMDS.map((c) => (
                  <div key={c.key} style={{ border: '1px solid var(--border)', borderRadius: 8, padding: 12 }}>
                    <div className="row between" style={{ marginBottom: 8 }}>
                      <span style={{ fontSize: 13, fontWeight: 500 }}>{c.label}</span>
                      <Button size="small" type="text" icon={<CopyOutlined />}
                        onClick={() => copyCmd(c.cmd, c.key)}>复制</Button>
                    </div>
                    <div ref={(el) => { cmdRefs.current[c.key] = el; }} className="mono" style={{
                      fontSize: 11.5, lineHeight: 1.8, wordBreak: 'break-all', color: 'var(--fg-2)',
                      background: 'var(--secondary)', borderRadius: 6, padding: '8px 12px',
                    }}>
                      {c.cmd}
                    </div>
                    <div className="vmuted2" style={{ marginTop: 8, lineHeight: 1.7 }}>{c.note}</div>
                  </div>
                ))}
              </div>

              <Alert type="info" showIcon
                message="脚本处理 SQLite 数据库文件与本地存储目录；生产若使用 PostgreSQL，数据库部分需另用 pg_dump / pg_restore"
                description="drill.sh 的输出只是本机样本参考值，不构成生产 RTO / RPO 证据。" />
            </Space>
          ),
        },
        {
          key: 'account', label: '账号与安全',
          children: (
            <Space direction="vertical" size={16} style={{ width: '100%', maxWidth: 640 }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 4 }}>导出数据</div>
                <div className="vmuted2" style={{ marginBottom: 10 }}>
                  把你的资料、笔记、卡片、题目与计划打包成机器可读的 JSON 归档下载到本地。
                </div>
                <Button icon={<DownloadOutlined />} loading={exportBusy} onClick={exportData}>导出全部数据</Button>
              </div>
              <div className="divider" style={{ margin: 0 }} />
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 4 }}>注销账号</div>
                <div className="vmuted2" style={{ marginBottom: 10 }}>
                  注销后资料、笔记、卡片、题目、计划与任务记录将被永久清除，无法恢复。
                </div>
                <Button danger onClick={() => { setDeletePassword(''); setDeleteOpen(true); }}>注销账号</Button>
              </div>
            </Space>
          ),
        },
      ]} />

      <Modal open={conflicts.length > 0} title="导入冲突" width={520}
        okText="保留本地（覆盖云端）" cancelText="保留云端（跳过）"
        onOk={() => resolveConflicts(true)} onCancel={() => resolveConflicts(false)}>
        <div className="vault-conflict">
          <div className="vmuted2" style={{ marginBottom: 8 }}>
            以下 {conflicts.length} 篇在云端已有同名笔记，请选择处理方式，不会静默覆盖。
          </div>
          {conflicts.slice(0, 5).map((c, i) => (
            <div className="vault-conflict-row" key={i}>
              <b>{c.note.title}</b><span className="vmuted2">本地文件 {c.content.length} 字</span>
            </div>
          ))}
          {conflicts.length > 5 && <div className="vmuted2">另有 {conflicts.length - 5} 篇…</div>}
        </div>
      </Modal>

      <Modal open={deleteOpen} title="注销账号" okText="确认注销" cancelText="取消"
        okButtonProps={{ danger: true }} onOk={confirmDelete} onCancel={() => setDeleteOpen(false)}>
        <div style={{ lineHeight: 1.9 }}>
          <div>这是不可撤销的操作，账号下的全部学习数据会被永久删除。</div>
          <div className="vmuted2" style={{ margin: '8px 0' }}>可留空以二次确认，或填写当前密码后再注销。</div>
          <Input.Password value={deletePassword} autoFocus placeholder="当前密码（可留空）"
            onChange={(e) => setDeletePassword(e.target.value)} />
        </div>
      </Modal>

      <Modal open={!!editProv} title={editProv?.id ? '编辑供应商' : '新建供应商'} footer={null}
        onCancel={() => setEditProv(null)} destroyOnClose>
        {editProv && (
          <Form layout="vertical" initialValues={editProv} onFinish={saveProvider}>
            <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="kind" label="类型"><Select options={KINDS} /></Form.Item>
            <Form.Item name="base_url" label="Base URL"><Input placeholder="https://ark.cn-beijing.volces.com/api/v3" /></Form.Item>
            <Form.Item name="api_key" label="API Key" extra="留空表示不修改"><Input.Password placeholder="sk-..." /></Form.Item>
            <Space size={20}>
              <Form.Item name="enabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
              <Form.Item name="is_default" label="设为默认" valuePropName="checked"><Switch /></Form.Item>
            </Space>
            <div className="row" style={{ justifyContent: 'flex-end', gap: 8 }}>
              <Button onClick={() => setEditProv(null)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={busy}>保存</Button>
            </div>
          </Form>
        )}
      </Modal>

      <Modal open={!!editModel} title={editModel?.id ? '编辑模型' : '新建模型'} footer={null}
        onCancel={() => setEditModel(null)} destroyOnClose>
        {editModel && (
          <Form layout="vertical" initialValues={editModel} onFinish={saveModel}>
            <Form.Item name="provider_id" label="供应商" rules={[{ required: true }]}>
              <Select options={providers.map((p) => ({ value: p.id, label: p.name }))} />
            </Form.Item>
            <Form.Item name="model_id" label="模型 ID" rules={[{ required: true }]}>
              <Input placeholder="deepseek-v4-1-flash-261017" />
            </Form.Item>
            <Form.Item name="label" label="备注名"><Input placeholder="笔记生成（方舟）" /></Form.Item>
            <Form.Item name="purpose" label="用途"><Select options={PURPOSES} /></Form.Item>
            <Space size={20}>
              <Form.Item name="enabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
              <Form.Item name="is_default" label="该用途默认" valuePropName="checked"><Switch /></Form.Item>
            </Space>
            <div className="row" style={{ justifyContent: 'flex-end', gap: 8 }}>
              <Button onClick={() => setEditModel(null)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={busy}>保存</Button>
            </div>
          </Form>
        )}
      </Modal>
    </div>
  );
}


/* 近 7 天用量趋势：双线（成本 / tokens），内联 SVG，无第三方依赖 */
function MonitorTrend({ series }) {
  const W = 520, H = 150, PAD_L = 40, PAD_R = 12, PAD_T = 14, PAD_B = 26;
  if (!series || series.length < 2) {
    return <div className="vmuted2" style={{ padding: '24px 0', textAlign: 'center' }}>数据不足，再跑几次模型调用就会画出来</div>;
  }
  const maxTok = Math.max(1, ...series.map((p) => +p.tokens || 0));
  const maxCost = Math.max(1, ...series.map((p) => +p.cost || 0));
  const n = series.length;
  const X = (i) => PAD_L + i * ((W - PAD_L - PAD_R) / (n - 1));
  const Ytok = (v) => H - PAD_B - (+v / maxTok) * (H - PAD_T - PAD_B);
  const Ycost = (v) => H - PAD_B - (+v / maxCost) * (H - PAD_T - PAD_B);
  const lineTok = series.map((p, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)} ${Ytok(+p.tokens || 0).toFixed(1)}`).join(' ');
  const lineCost = series.map((p, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)} ${Ycost(+p.cost || 0).toFixed(1)}`).join(' ');
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="150" preserveAspectRatio="none">
        {[0, 0.5, 1].map((t) => (
          <line key={t} x1={PAD_L} y1={(H - PAD_B - t * (H - PAD_T - PAD_B)).toFixed(1)}
            x2={W - PAD_R} y2={(H - PAD_B - t * (H - PAD_T - PAD_B)).toFixed(1)}
            stroke="var(--border)" strokeWidth="1" />
        ))}
        <path d={lineTok} fill="none" stroke="var(--primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d={lineCost} fill="none" stroke="var(--warning, #8a6220)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="5 3" />
        {series.map((p, i) => (
          <circle key={i} cx={X(i)} cy={Ytok(+p.tokens || 0)} r="2.5" fill="var(--primary)" />
        ))}
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--muted)' }}>
        {series.map((p, i) => <span key={i}>{p.day.slice(5)}</span>)}
      </div>
      <div style={{ display: 'flex', gap: 16, marginTop: 6, fontSize: 12 }}>
        <span><i style={{ display: 'inline-block', width: 14, height: 2, background: 'var(--primary)', verticalAlign: 'middle', marginRight: 4 }} />tokens（左）</span>
        <span><i style={{ display: 'inline-block', width: 14, height: 2, borderTop: '2px dashed #8a6220', verticalAlign: 'middle', marginRight: 4 }} />成本（右，最大 {maxCost} 元）</span>
      </div>
    </div>
  );
}

/* 模型调用分布：横向条形（调用次数），内联 SVG */
function MonitorBars({ models }) {
  if (!models || models.length === 0) {
    return <div className="vmuted2" style={{ padding: '24px 0', textAlign: 'center' }}>还没有调用记录</div>;
  }
  const maxCalls = Math.max(1, ...models.map((m) => +m.calls || 0));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {models.slice(0, 8).map((m) => (
        <div key={m.model}>
          <div className="row between" style={{ fontSize: 11.5, marginBottom: 2 }}>
            <span className="ellipsis" style={{ maxWidth: 200 }} title={m.model}>{m.model}</span>
            <span className="vmuted2">{m.calls} 次</span>
          </div>
          <div style={{ height: 8, background: 'var(--bg, #eee9df)', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${Math.round((+m.calls / maxCalls) * 100)}%`,
              background: 'var(--primary)', borderRadius: 4 }} />
          </div>
        </div>
      ))}
    </div>
  );
}
