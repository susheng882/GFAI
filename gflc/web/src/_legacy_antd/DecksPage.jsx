import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { App as AntdApp, Button, Input, Modal, Segmented, Select, Table, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { esc, fmtTime } from '../utils.js';
import Markdown from '../components/Markdown.jsx';
import EmptyState from '../components/EmptyState.jsx';

/* 卡包：章节卡片网格 + Anki 式卡片浏览器（表格 + 筛选 + 批量操作）。 */

// 熟练度分档：优先用后端 mastery 真值（0–1），旧数据回落 difficulty
const MASTERY = {
  easy: { label: '熟练', color: 'success' },
  mid: { label: '中等', color: 'processing' },
  hard: { label: '生疏', color: 'warning' },
};
const bucketOf = (c) => {
  const m = Number(c?.mastery);
  if (c?.mastery != null && Number.isFinite(m)) return m >= 0.7 ? 'easy' : m >= 0.35 ? 'mid' : 'hard';
  return MASTERY[c?.difficulty] ? c.difficulty : 'mid';
};
const masteryOf = (c) => MASTERY[bucketOf(c)] || MASTERY.mid;

export default function DecksPage() {
  const { message, modal } = AntdApp.useApp();
  const navigate = useNavigate();
  const [decks, setDecks] = useState([]);
  const [openDeckId, setOpenDeckId] = useState(null);
  const [cards, setCards] = useState([]);
  const [form, setForm] = useState(null);
  const [view, setView] = useState('chapters');
  const [allCards, setAllCards] = useState([]);
  const [deckFilter, setDeckFilter] = useState(null);
  const [masteryFilter, setMasteryFilter] = useState(null);
  const [kw, setKw] = useState('');
  const [selectedKeys, setSelectedKeys] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setDecks(await api('/decks') || []); } catch { setDecks([]); }
  }, []);
  useEffect(() => { load(); }, [load]);

  /* 浏览器数据：复用已有 GET /api/cards，一次取回后在本地按卡包/熟练度/关键词筛选。 */
  const loadBrowser = useCallback(async () => {
    try { setAllCards(await api('/cards?limit=500') || []); } catch { setAllCards([]); }
  }, []);
  useEffect(() => { if (view === 'browser') loadBrowser(); }, [view, loadBrowser]);

  const openDeck = async (id) => {
    setOpenDeckId(id);
    try { setCards(await api(`/decks/${id}/cards`) || []); } catch { setCards([]); }
  };

  const saveCard = async () => {
    try {
      const payload = { question: form.question, answer: form.answer, deck_id: form.deck_id, tag: form.tag || '' };
      if (form.id) await api(`/cards/${form.id}`, { method: 'PATCH', body: JSON.stringify(payload) });
      else await api('/cards', { method: 'POST', body: JSON.stringify(payload) });
      message.success(form.id ? '已保存卡片' : '已创建卡片');
      setForm(null);
      await load();
      if (openDeckId) await openDeck(openDeckId);
      if (view === 'browser') await loadBrowser();
    } catch (e) { message.error(e.message); }
  };

  const del = (card) => modal.confirm({
    title: '删除这张卡片？', okText: '删除', okButtonProps: { danger: true }, cancelText: '取消',
    onOk: async () => {
      try { await api(`/cards/${card.id}`, { method: 'DELETE' }); message.success('已删除'); await load(); await openDeck(openDeckId); await loadBrowser(); }
      catch (e) { message.error(e.message); }
    },
  });

  /* 批量操作统一入口：优先一次请求走 /cards/batch-*（后端做越权过滤并返回 succeeded/failed）；
     接口 404（后端未升级）时回退逐张串行，结果口径保持一致。 */
  const runBatch = async (kind, ids) => {
    const path = kind === 'delete' ? '/cards/batch-delete' : '/cards/batch-reset';
    try {
      const r = await api(path, { method: 'POST', body: JSON.stringify({ ids }) });
      return { succeeded: Number(r?.succeeded) || 0, failed: Number(r?.failed) || 0 };
    } catch (e) {
      if (e?.status !== 404) throw e;
      let ok = 0;
      for (const id of ids) {
        try {
          if (kind === 'delete') await api(`/cards/${id}`, { method: 'DELETE' });
          else await api(`/cards/${id}/reset`, { method: 'POST' });
          ok++;
        } catch { /* 逐张失败计入 failed，不中断剩余卡片 */ }
      }
      return { succeeded: ok, failed: ids.length - ok };
    }
  };

  const reportBatch = (action, r) => {
    if (r.failed) message.warning(`已${action} ${r.succeeded} 张，${r.failed} 张未处理`);
    else message.success(`已${action} ${r.succeeded} 张卡片`);
  };

  const refreshAll = async () => {
    await load();
    await loadBrowser();
    if (openDeckId) await openDeck(openDeckId);
  };

  const batchReset = () => {
    const ids = [...selectedKeys];
    if (!ids.length) return;
    modal.confirm({
      title: `重置选中的 ${ids.length} 张卡片的复习进度？`, okText: '重置', cancelText: '取消',
      onOk: async () => {
        setBusy(true);
        try {
          const r = await runBatch('reset', ids);
          setSelectedKeys([]);
          reportBatch('重置', r);
          await refreshAll();
        } catch (e) { message.error(e.message || '批量重置失败'); }
        finally { setBusy(false); }
      },
    });
  };

  const batchDelete = () => {
    const ids = [...selectedKeys];
    if (!ids.length) return;
    modal.confirm({
      title: `删除选中的 ${ids.length} 张卡片？`, okText: '删除', okButtonProps: { danger: true }, cancelText: '取消',
      onOk: async () => {
        setBusy(true);
        try {
          const r = await runBatch('delete', ids);
          setSelectedKeys([]);
          reportBatch('删除', r);
          await refreshAll();
        } catch (e) { message.error(e.message || '批量删除失败'); }
        finally { setBusy(false); }
      },
    });
  };

  const flat = decks.flatMap((r) => (r.children || []).map((c) => ({ ...c, parent: r.name })));
  const deckName = useMemo(() => {
    const m = {};
    flat.forEach((d) => { m[d.id] = `${d.parent} / ${d.name}`; });
    return m;
  }, [decks]);

  const browserRows = useMemo(() => allCards.filter((c) => {
    if (deckFilter != null && c.deck_id !== deckFilter) return false;
    if (masteryFilter != null && bucketOf(c) !== masteryFilter) return false;
    if (kw.trim()) {
      const t = `${c.question || ''} ${c.answer || ''}`.toLowerCase();
      if (!t.includes(kw.trim().toLowerCase())) return false;
    }
    return true;
  }), [allCards, deckFilter, masteryFilter, kw]);

  const chapterColumns = [
    { title: '问题', dataIndex: 'question', render: (v) => <div style={{ maxWidth: 480 }}>{esc(v)}</div> },
    { title: '标签', dataIndex: 'tag', width: 110, render: (v) => <Tag>{v || '未分章'}</Tag> },
    { title: '页码', dataIndex: 'page', width: 70, render: (v) => v || '—' },
    { title: '操作', width: 120, render: (_, c) => (
      <span className="row" style={{ gap: 2, flexWrap: 'nowrap' }}>
        <Button size="small" type="link" onClick={() => setForm({ ...c, deck_id: c.deck_id || openDeckId })}>编辑</Button>
        <Button size="small" type="link" danger onClick={() => del(c)}>删除</Button>
      </span>
    ) },
  ];

  /* B8：列头可点击排序；间隔 / 失误 / 复习次数三列取 /cards 返回的真值。
     interval 由后端按 FSRS scheduled_days 计算，未排期的旧卡为 null，显示「—」。 */
  const browserColumns = [
    { title: '卡片内容', dataIndex: 'question',
      sorter: (a, b) => String(a.question || '').localeCompare(String(b.question || '')),
      render: (v, c) => (
        <div style={{ maxWidth: 320 }}>
          <div style={{ fontWeight: 500 }}>{esc((v || '').slice(0, 60))}</div>
          <div className="muted" style={{ fontSize: 11.5 }}>{esc((c.answer || '').slice(0, 60))}</div>
        </div>
      ) },
    { title: '卡包', dataIndex: 'deck_id', width: 150,
      sorter: (a, b) => String(deckName[a.deck_id] || '').localeCompare(String(deckName[b.deck_id] || '')),
      render: (v) => <span className="muted">{esc(deckName[v] || '—')}</span> },
    { title: '熟练度', dataIndex: 'mastery', width: 110,
      sorter: (a, b) => Number(a.mastery || 0) - Number(b.mastery || 0),
      render: (v, c) => {
        const m = masteryOf(c);
        return <Tag color={m.color}>{m.label}{v != null ? ` ${Math.round(Number(v) * 100)}%` : ''}</Tag>;
      } },
    { title: '下次复习', dataIndex: 'due_at', width: 120,
      sorter: (a, b) => String(a.due_at || '').localeCompare(String(b.due_at || '')),
      render: (v) => <span className="mono" style={{ fontSize: 12 }}>{fmtTime(v)}</span> },
    { title: '间隔', dataIndex: 'interval', width: 90,
      sorter: (a, b) => Number(a.interval ?? 0) - Number(b.interval ?? 0),
      render: (v) => (v != null ? <span className="mono">{v} 天</span> : '—') },
    { title: '失误', dataIndex: 'lapses', width: 80,
      sorter: (a, b) => Number(a.lapses || 0) - Number(b.lapses || 0),
      render: (v) => v != null ? <span className="mono">{v}</span> : '—' },
    { title: '复习次数', dataIndex: 'reps', width: 100,
      sorter: (a, b) => Number(a.reps || 0) - Number(b.reps || 0),
      render: (v) => v != null ? <span className="mono">{v}</span> : '—' },
    { title: '操作', width: 90, render: (_, c) => (
      <Button size="small" type="link" danger onClick={() => del(c)}>删除</Button>
    ) },
  ];

  const empty = decks.length === 0 && allCards.length === 0;

  return (
    <div>
      <div className="row between" style={{ marginBottom: 14 }}>
        <Segmented value={view} onChange={setView}
          options={[{ label: '章节卡包', value: 'chapters' }, { label: '卡片浏览', value: 'browser' }]} />
        <div className="row">
          {/* 题库为空时主按钮变「导入题库」并跳转资料页，避免新建卡片无处挂载 */}
          <Button type="primary" onClick={() => empty ? navigate('/docs') : setForm({ question: '', answer: '', deck_id: flat[0]?.id, tag: '' })}>
            {empty ? '导入题库' : '新建卡片'}
          </Button>
        </div>
      </div>

      {view === 'chapters' ? (
        <>
          {decks.length ? (
            <div className="grid g3" style={{ marginBottom: 18 }}>
              {decks.map((r) => (
                <div className="v3-card" key={r.id}>
                  <div className="v3-sh">{esc(r.name)}<span className="meta">{r.children?.length || 0} 个分册</span></div>
                  <div className="row" style={{ gap: 6 }}>
                    {(r.children || []).map((c) => (
                      <Button size="small" key={c.id}
                        style={openDeckId === c.id ? { background: 'var(--accent)', color: 'var(--primary)', borderColor: 'var(--primary)' } : undefined}
                        onClick={() => openDeck(c.id)}>{esc(c.name)} · {c.total}</Button>
                    ))}
                    {!(r.children || []).length && <span className="muted" style={{ fontSize: 12 }}>暂无分册</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : <EmptyState title="还没有卡包" desc="上传资料后自动生成按章节组织的卡包。"
            action="去资料页导入" onAction={() => navigate('/docs')} />}

          {openDeckId && (
            <div className="card" style={{ padding: '6px 14px' }}>
              <div className="v3-sh">卡片列表<span className="meta">{cards.length} 张</span></div>
              <Table rowKey="id" columns={chapterColumns} dataSource={cards} size="small" pagination={false} />
            </div>
          )}
        </>
      ) : (
        <div className="card" style={{ padding: '12px 14px' }}>
          <div className="row" style={{ gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
            <Input allowClear placeholder="搜索卡片内容…" value={kw} onChange={(e) => setKw(e.target.value)} style={{ width: 200 }} />
            <Select allowClear placeholder="全部卡包" value={deckFilter} onChange={setDeckFilter} style={{ width: 180 }}
              options={flat.map((d) => ({ value: d.id, label: `${d.parent} / ${d.name}` }))} />
            <Select allowClear placeholder="全部熟练度" value={masteryFilter} onChange={setMasteryFilter} style={{ width: 130 }}
              options={Object.entries(MASTERY).map(([k, v]) => ({ value: k, label: v.label }))} />
            <span className="row" style={{ marginLeft: 'auto', gap: 8 }}>
              <Button danger disabled={!selectedKeys.length} loading={busy} onClick={batchDelete}>批量删除</Button>
              <Button disabled={!selectedKeys.length} loading={busy} onClick={batchReset}>重置进度</Button>
            </span>
          </div>
          <div className="v3-sh">卡片浏览<span className="meta">{browserRows.length} 张</span></div>
          <Table rowKey="id" columns={browserColumns} dataSource={browserRows} size="small" pagination={false}
            rowSelection={{ selectedRowKeys: selectedKeys, onChange: setSelectedKeys }}
            locale={{ emptyText: allCards.length ? '没有符合条件的卡片' : '还没有卡片，去资料页生成' }} />
        </div>
      )}

      {form && (
        <Modal open onCancel={() => setForm(null)} title={form.id ? '编辑卡片' : '新建卡片'}
          okText="保存" cancelText="取消" onOk={saveCard}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div><div style={{ fontSize: 12, marginBottom: 4 }}>所属分册</div>
              <Select style={{ width: '100%' }} value={form.deck_id} onChange={(v) => setForm({ ...form, deck_id: v })}
                options={flat.map((d) => ({ label: `${d.parent} / ${d.name}`, value: d.id }))} />
            </div>
            <div><div style={{ fontSize: 12, marginBottom: 4 }}>问题</div>
              <Input.TextArea rows={3} value={form.question} onChange={(e) => setForm({ ...form, question: e.target.value })} /></div>
            <div><div style={{ fontSize: 12, marginBottom: 4 }}>答案（支持 Markdown / LaTeX）</div>
              <Input.TextArea rows={4} value={form.answer} onChange={(e) => setForm({ ...form, answer: e.target.value })} /></div>
            <div><div style={{ fontSize: 12, marginBottom: 4 }}>标签</div>
              <Input value={form.tag || ''} onChange={(e) => setForm({ ...form, tag: e.target.value })} /></div>
            {form.answer && <Markdown text={form.answer} />}
          </div>
        </Modal>
      )}
    </div>
  );
}
