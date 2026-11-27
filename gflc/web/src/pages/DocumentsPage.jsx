import React, { useCallback, useEffect, useRef, useState } from 'react';
import { App as AntdApp, Button, Input, InputNumber, Modal, Segmented, Table, Tag, Tooltip, Upload } from 'antd';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api, runTask } from '../api.js';
import { esc, fmtTime } from '../utils.js';
import DocumentJumpModal from '../components/DocumentJumpModal.jsx';

/* 资料上传与列表；同时承接 S4 文档类来源跳转：/docs?doc=<id>&page=<n> 打开定位抽屉。 */
export default function DocumentsPage() {
  const { message, modal } = AntdApp.useApp();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [viewMode, setViewMode] = useState(localStorage.getItem('gflc_docs_view') || 'list');
  const [groups, setGroups] = useState(null);          // 左树分组
  const [filterGroup, setFilterGroup] = useState('');  // 当前筛选分组
  const [search, setSearch] = useState('');            // 搜索词
  const [docs, setDocs] = useState([]);
  const [notes, setNotes] = useState([]);
  const [busy, setBusy] = useState(false);
  const [noteBusy, setNoteBusy] = useState({});
  const [noteDone, setNoteDone] = useState({});
  const [noteErr, setNoteErr] = useState({});
  const [paperDoc, setPaperDoc] = useState(null);
  const [paperCount, setPaperCount] = useState(10);
  const [paperBusy, setPaperBusy] = useState(false);
  const fileRef = useRef(null);

  const loadGroups = () => api('/documents/groups').then((r) => setGroups(r)).catch(() => setGroups(null));
  useEffect(() => { loadGroups(); }, []);
  const load = useCallback(async () => {
    const [d, n] = await Promise.allSettled([api('/documents'), api('/notes')]);
    setDocs(d.status === 'fulfilled' ? d.value || [] : []);
    setNotes(n.status === 'fulfilled' ? n.value || [] : []);
  }, []);
  useEffect(() => { load(); }, [load]);

  const jumpDoc = params.get('doc');
  const jumpPage = Number(params.get('page')) || 1;
  const closeJump = () => {
    const next = new URLSearchParams(params);
    next.delete('doc'); next.delete('page');
    setParams(next, { replace: true });
  };

  const upload = async (file) => {
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const created = await api('/documents/upload', { method: 'POST', body: fd });
      await runTask(`/documents/${created.document.id}/parse`, { method: 'POST' }, '解析资料');
      message.success('已上传《' + file.name + '》并解析');
      await load();
    } catch (e) { message.error(e.message); } finally { setBusy(false); }
  };

  const act = async (doc, kind) => {
    try {
      if (kind === 'parse') await runTask(`/documents/${doc.id}/parse`, { method: 'POST' }, '重新解析');
      if (kind === 'cards') await runTask(`/documents/${doc.id}/cards`, { method: 'POST' }, '生成卡片');
      await load();
    } catch (e) { message.error(e.message); }
  };

  /* 资料 → 笔记：同步生成，可能较慢；四态 idle / loading / success / error。 */
  const genNote = async (doc) => {
    if (doc.status !== 'ready' || noteBusy[doc.id]) return;
    setNoteBusy((s) => ({ ...s, [doc.id]: true }));
    setNoteErr((s) => ({ ...s, [doc.id]: '' }));
    message.info('正在生成笔记，约需 10–20 秒');
    try {
      const r = await api(`/documents/${doc.id}/notes`, { method: 'POST', body: JSON.stringify({}) });
      setNoteDone((s) => ({ ...s, [doc.id]: (r && r.id) || '' }));
      message.success('笔记已生成');
      await load();
    } catch (e) {
      const text = e && e.status === 404 ? '后端未升级，暂不可用' : (e && e.message) || '生成失败';
      setNoteErr((s) => ({ ...s, [doc.id]: text }));
      message.error(text);
    } finally {
      setNoteBusy((s) => ({ ...s, [doc.id]: false }));
    }
  };

  /* S3 用我的资料出模拟卷：读已解析内容 → 模型命题 → 落库成题库，成功后进刷题页。 */
  const genPaper = async () => {
    if (!paperDoc) return;
    setPaperBusy(true);
    try {
      const r = await api('/ai/mock-paper', {
        method: 'POST', body: JSON.stringify({ document_id: paperDoc.id, count: paperCount }),
      });
      setPaperDoc(null);
      message.success(`已生成 ${r?.count || 0} 题模拟卷${r?.note ? `（${r.note}）` : ''}`);
      navigate('/study');
    } catch (e) {
      message.error(e.message || '模拟卷生成失败');
    } finally {
      setPaperBusy(false);
    }
  };

  const rename = (doc) => {
    let value = doc.title || '';
    Modal.confirm({
      title: '重命名资料',
      content: <Input defaultValue={value} onChange={(e) => { value = e.target.value; }} autoFocus />,
      okText: '保存', cancelText: '取消',
      onOk: async () => {
        try { await api(`/documents/${doc.id}`, { method: 'PATCH', body: JSON.stringify({ title: value }) }); message.success('已改名'); await load(); }
        catch (e) { message.error(e.message); }
      },
    });
  };

  const del = (doc) => {
    modal.confirm({
      title: '删除这份资料？', content: `《${doc.title}》及其切片、卡片会一并删除。`,
      okText: '删除', okButtonProps: { danger: true }, cancelText: '取消',
      onOk: async () => {
        try { await api(`/documents/${doc.id}`, { method: 'DELETE' }); message.success('已删除'); await load(); }
        catch (e) { message.error(e.message); }
      },
    });
  };

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title', render: (v, d) => (
      <div>
        <Button type="link" size="small" title="查看资料详情"
          style={{ padding: 0, height: 'auto', fontWeight: 500, color: 'var(--foreground)', textAlign: 'left' }}
          onClick={() => navigate(`/docs/${d.id}`)}>
          {esc(v || '未命名')}
        </Button>
        <div className="muted" style={{ fontSize: 11.5 }}>
          {d.source_type === 'video' ? '视频' : d.source_type === 'note' ? '笔记' : '文档'} · {fmtTime(d.updated_at || d.created_at)}
        </div>
      </div>
    ) },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v) => (
      <Tag color={v === 'ready' ? 'success' : v === 'failed' ? 'error' : 'processing'}>
        {{ pending: '待解析', parsing: '解析中', ready: '就绪', failed: '失败' }[v] || v}
      </Tag>
    ) },
    { title: '切片', dataIndex: 'chunks', key: 'chunks', width: 80, render: (v) => v ?? '—' },
    { title: '操作', key: 'op', width: 480, render: (_, d) => {
      const done = noteDone[d.id];
      const loading = !!noteBusy[d.id];
      return (
        <div>
          <div className="row" style={{ gap: 4, flexWrap: 'nowrap' }}>
            <Button size="small" type="link" onClick={() => setParams({ doc: d.id, page: 1 })}>定位</Button>
            <Button size="small" type="link" onClick={() => act(d, 'parse')}>解析</Button>
            <Button size="small" type="link" onClick={() => act(d, 'cards')}>生成卡片</Button>
            <Tooltip title={d.status === 'ready' ? '按这份资料的内容出题' : '请先解析'}>
              <span style={{ display: 'inline-flex' }}>
                <Button size="small" type="link" disabled={d.status !== 'ready'}
                  onClick={() => { setPaperCount(10); setPaperDoc(d); }}>出模拟卷</Button>
              </span>
            </Tooltip>
            {done ? (
              <Button size="small" type="text" onClick={() => navigate(`/notes?note=${done}`)}>已生成，去查看</Button>
            ) : (
              <Tooltip title={d.status === 'ready' ? '约需 10–20 秒' : '请先解析'}>
                <span style={{ display: 'inline-flex' }}>
                  <Button size="small" type="text" loading={loading} disabled={d.status !== 'ready' || loading}
                    onClick={() => genNote(d)}>
                    {loading ? '生成中…' : '生成笔记'}
                  </Button>
                </span>
              </Tooltip>
            )}
            <Button size="small" type="link" onClick={() => rename(d)}>改名</Button>
            <Button size="small" type="link" danger onClick={() => del(d)}>删除</Button>
            <Button size="small" type="link" onClick={() => navigate(`/docs/${d.id}`)}>详情</Button>
          </div>
          {noteErr[d.id] && (
            <div style={{ fontSize: 11.5, color: 'var(--destructive)', marginTop: 4 }}>{noteErr[d.id]}</div>
          )}
        </div>
      );
    } },
  ];

  /* 按分组/搜索过滤 */
  const shown = docs.filter((d) => {
    if (filterGroup) {
      const g = (groups?.groups || []).find((x) => x.name === filterGroup);
      if (!g) return true;
      const keys = (g.children || []).map((c) => c.name);
      return keys.some((k) => (d.title || '').includes(k));
    }
    if (search) return (d.title || '').toLowerCase().includes(search.toLowerCase());
    return true;
  });

  return (
    <div style={{ display: 'flex', gap: 12, alignItems: 'start' }}>
      {/* 左树（v7l 分组） */}
      <aside className="rc-card" style={{ width: 200, flexShrink: 0, padding: '10px 8px', position: 'sticky', top: 60 }}>
        <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--muted-foreground)', padding: '4px 8px 8px' }}>
          资料库{groups ? ` · ${groups.total}` : ''}
        </div>
        <div className="ft-row" style={{ padding: '6px 8px', borderRadius: 6, cursor: 'pointer',
          background: filterGroup === '' ? 'var(--secondary)' : 'transparent', fontSize: 11.5 }}
          onClick={() => setFilterGroup('')}>
          全部资料 <span className="num vmuted2" style={{ float: 'right' }}>{groups?.total ?? docs.length}</span>
        </div>
        {(groups?.groups || []).map((g) => (
          <div key={g.name}>
            <div className="ft-row" style={{ padding: '6px 8px', borderRadius: 6, cursor: 'pointer',
              background: filterGroup === g.name ? 'var(--secondary)' : 'transparent',
              fontSize: 11.5, fontWeight: filterGroup === g.name ? 500 : 400 }}
              onClick={() => setFilterGroup(filterGroup === g.name ? '' : g.name)}>
              {g.name} <span className="num vmuted2" style={{ float: 'right' }}>{g.count}</span>
            </div>
            {(g.children || []).map((c) => (
              <div key={c.name} style={{ padding: '4px 8px 4px 18px', fontSize: 11, color: 'var(--muted-foreground)', cursor: 'pointer' }}
                onClick={() => { setFilterGroup(g.name); setSearch(c.name); }}>
                {c.name} <span className="num" style={{ float: 'right' }}>{c.count}</span>
              </div>
            ))}
          </div>
        ))}
      </aside>

      {/* 右主区 */}
      <div style={{ flex: 1, minWidth: 0 }}>
      <div className="vmuted2" style={{ marginBottom: 10 }}>
        这里是「教材/讲义」解析 → 生成笔记与背诵卡片；要导入真题试卷练题，请去 <a onClick={() => navigate('/banks')} style={{ color: 'var(--primary)', cursor: 'pointer' }}>题库页</a>
      </div>
      <div className="row between" style={{ marginBottom: 14 }}>
        <div className="drop" style={{ padding: '20px 24px', flex: 1, maxWidth: 560 }}
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); upload(e.dataTransfer.files[0]); }}>
          <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--ink)' }}>点击或拖拽 PDF / Word / MD 到此处</div>
          <div style={{ fontSize: 10.5, color: 'var(--ink-subtle)', marginTop: 3 }}>
            支持批量上传 · 自动解析分卡 · 本地文件不离开设备
          </div>
        </div>
        <Button type="primary" loading={busy} onClick={() => fileRef.current?.click()}>上传资料</Button>
        <input ref={fileRef} type="file" accept=".pdf,.docx,.md,.markdown,.txt" hidden
          onChange={(e) => { upload(e.target.files[0]); e.target.value = ''; }} />
      </div>
      <div className="row between" style={{ marginBottom: 10 }}>
        <Segmented size="small"
          value={viewMode}
          onChange={(v) => { setViewMode(v); localStorage.setItem('gflc_docs_view', v); }}
          options={[
            { label: '列表', value: 'list' },
            { label: '网格', value: 'grid' },
          ]} />
        <span className="vmuted2" style={{ fontSize: 11.5 }}>{docs.length} 份资料</span>
      </div>
      {viewMode === 'grid' ? (
        <div className="g3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
          {docs.length ? docs.map((d) => (
            <div key={d.id} className="rc-card" style={{ padding: 14, cursor: 'pointer' }}
              onClick={() => navigate(`/docs/${d.id}`)}>
              <div className="row between" style={{ marginBottom: 8 }}>
                <Tag color={d.status === 'ready' ? 'success' : d.status === 'failed' ? 'error' : 'processing'}>
                  {{ pending: '待解析', parsing: '解析中', ready: '就绪', failed: '失败' }[d.status] || d.status}
                </Tag>
                <span className="vmuted2" style={{ fontSize: 10.5 }}>
                  {d.source_type === 'video' ? '视频' : d.source_type === 'note' ? '笔记' : '文档'}
                </span>
              </div>
              <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {esc(d.title || '未命名')}
              </div>
              <div className="row between">
                <span className="vmuted2" style={{ fontSize: 11 }}>{d.chunks ?? '—'} 切片</span>
                <span className="vmuted2" style={{ fontSize: 11 }}>{fmtTime(d.updated_at || d.created_at)}</span>
              </div>
            </div>
          )) : <div className="vmuted2" style={{ padding: '40px 0', textAlign: 'center' }}>还没有资料，上传一份 PDF 开始。</div>}
        </div>
      ) : (
        <div className="card" style={{ padding: '6px 14px' }}>
          <Table rowKey="id" columns={columns} dataSource={shown} size="small" pagination={false}
            scroll={{ x: 'max-content' }}
            locale={{ emptyText: '还没有资料，上传一份 PDF 开始。' }} />
        </div>
      )}
      {notes.length > 0 && (
        <>
          <h2 style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-2)', margin: '24px 0 10px' }}>资料下的笔记</h2>
          <div className="card" style={{ padding: '6px 14px' }}>
            {notes.slice(0, 8).map((n) => (
              <div className="row between" key={n.id} style={{ padding: '9px 0', borderBottom: '1px solid var(--border)' }}>
                <span>{esc(n.title || '未命名')}</span>
                <Button size="small" type="link" onClick={() => navigate(`/notes?note=${n.id}`)}>去笔记</Button>
              </div>
            ))}
          </div>
        </>
      )}
      <DocumentJumpModal open={!!jumpDoc} docId={jumpDoc} page={jumpPage} documents={docs} onClose={closeJump} />
      <Modal
        title="出一份模拟卷"
        open={!!paperDoc}
        onCancel={() => { if (!paperBusy) setPaperDoc(null); }}
        onOk={genPaper}
        okText="生成"
        cancelText="取消"
        confirmLoading={paperBusy}
        destroyOnClose
      >
        <div className="muted" style={{ fontSize: 12.5, marginBottom: 12 }}>
          《{paperDoc?.title || ''}》已解析的内容会用来命题
        </div>
        <div className="row" style={{ gap: 8 }}>
          <span className="muted" style={{ fontSize: 12.5 }}>题量</span>
          <InputNumber min={3} max={20} value={paperCount}
            onChange={(v) => setPaperCount(v || 10)} style={{ width: 80 }} />
        </div>
      </Modal>
      </div>
    </div>
  );
}
