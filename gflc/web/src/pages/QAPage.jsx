import React, { useEffect, useRef, useState } from 'react';
import { App as AntdApp, Button, Input, Segmented, Tag } from 'antd';
import { PaperClipOutlined, SendOutlined, ThunderboltFilled, RightOutlined } from '@ant-design/icons';
import { api, runTask, streamQA } from '../api.js';
import { esc, genFollowups, sourceTrace } from '../utils.js';
import Markdown from '../components/Markdown.jsx';
import SourceChips from '../components/SourceChips.jsx';
import EmptyState from '../components/EmptyState.jsx';

const STRATS = [
  { label: '智能', value: 'auto' }, { label: '仅资料', value: 'knowledge' },
  { label: '仅联网', value: 'web' }, { label: '仅模型', value: 'model' },
  { label: '混合', value: 'hybrid' },
];
const STRAT_TIP = {
  auto: '自动判断来源', knowledge: '只查我的资料', web: '只联网检索',
  model: '只用学科知识', hybrid: '资料与联网合并',
};
const STAGES = ['检索资料', '核对来源', '生成回答'];

/* 问答：NDJSON 流式 + 三阶段过程行与耗时 + 检索依据展开 + 追问建议 + S4 来源芯片。 */
export default function QAPage() {
  const { message } = AntdApp.useApp();
  const [msgs, setMsgs] = useState([]);
  const [strategy, setStrategy] = useState('auto');
  const [docs, setDocs] = useState([]);
  const [question, setQuestion] = useState('');
  const [suggests, setSuggests] = useState([]);
  const chatRef = useRef(null);
  const fileRef = useRef(null);

  useEffect(() => { api('/documents').then((d) => setDocs(d || [])).catch(() => {}); }, []);
  // B2：后端已有 GET /qa/suggest，拉推荐问题并做成可点按钮
  useEffect(() => { api('/qa/suggest').then((r) => setSuggests(Array.isArray(r) ? r : [])).catch(() => setSuggests([])); }, []);
  useEffect(() => { if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight; }, [msgs]);

  const ask = async (text) => {
    const q = String(text || question).trim();
    if (!q) return;
    setQuestion('');
    const idx = msgs.length + 1;
    const t0 = Date.now();
    setMsgs((prev) => [
      ...prev,
      { role: 'user', text: q },
      { role: 'bot', text: '', pending: true, showProc: true, stage: 0, elapsed: 0 },
    ]);
    let full = '', meta = null, stage = 0;
    const timer = setInterval(() => {
      setMsgs((prev) => prev.map((m, i) => i === idx ? { ...m, elapsed: (Date.now() - t0) / 1000 } : m));
    }, 200);
    const bump = (v) => { if (v > stage) stage = v; };
    const paint = () => {
      setMsgs((prev) => prev.map((m, i) => i === idx ? {
        ...m, text: full, pending: !full, streaming: true,
        mode: meta?.mode, sources: meta?.sources || [], hint: meta?.hint,
        showProc: true, stage, elapsed: (Date.now() - t0) / 1000,
      } : m));
    };
    try {
      await streamQA({
        question: q, strategy,
        onEvent: (ev) => {
          if (ev.type === 'status') { meta = { ...(meta || {}), hint: ev.hint }; bump(0); paint(); }
          else if (ev.type === 'sources' || ev.type === 'meta') {
            meta = { ...(meta || {}), mode: ev.mode, sources: ev.sources || [], hint: ev.hint, confidence: ev.confidence };
            bump(1); paint();
          } else if (ev.type === 'delta' || ev.type === 'notice') {
            full += ev.text || ''; bump(2); paint();
          } else if (ev.type === 'done') {
            if (ev.full) full = ev.full;
            bump(2); paint();
          } else if (ev.type === 'error') {
            message.error(ev.message || '生成中断');
          }
        },
      });
      clearInterval(timer);
      const srcs = meta?.sources || [];
      setMsgs((prev) => prev.map((m, i) => i === idx ? {
        ...m, text: full || '（没有返回内容）', pending: false, streaming: false,
        mode: meta?.mode, sources: srcs, showProc: false, stage: 3,
        elapsed: (Date.now() - t0) / 1000, trace: sourceTrace(srcs),
        followups: genFollowups(meta?.mode),
      } : m));
    } catch (e) {
      clearInterval(timer);
      setMsgs((prev) => prev.map((m, i) => i === idx ? { ...m, text: '出错：' + e.message, showProc: false } : m));
    }
  };

  const attach = async (file) => {
    if (!file) return;
    try {
      const fd = new FormData();
      fd.append('file', file);
      const created = await api('/documents/upload', { method: 'POST', body: fd });
      await runTask(`/documents/${created.document.id}/parse`, { method: 'POST' }, '解析资料');
      await runTask(`/documents/${created.document.id}/cards`, { method: 'POST' }, '生成卡片');
      setDocs(await api('/documents') || []);
      setMsgs((prev) => [...prev, { role: 'bot', text: `已收录《${file.name}》，现在可以就它提问了。` }]);
    } catch (e) { message.error(e.message); }
  };

  return (
    <div className="qa-wrap">
      <div className={'chat' + (msgs.length ? '' : ' chat-empty')} ref={chatRef}>
        {msgs.length ? msgs.map((m, i) => (
          <Message key={i} m={m} docs={docs} onFollowup={ask}
            question={msgs[i - 1] && msgs[i - 1].role === 'user' ? msgs[i - 1].text : ''} />
        ))
          : <EmptyState title="开始提问" desc="先在你的资料里找依据并标注页码；资料里没有就联网检索，最后还可以只用学科知识回答。" />}
      </div>
      {suggests.length > 0 && (
        <div className="qa-suggest">
          <span className="qa-suggest-h">推荐问题</span>
          {suggests.map((s, i) => (
            <button key={i} type="button" className="qa-suggest-item" onClick={() => ask(s)}>{esc(s)}</button>
          ))}
        </div>
      )}
      <div className="card composer">
        <div className="row between" style={{ marginBottom: 10 }}>
          <Segmented size="small" value={strategy} onChange={setStrategy} options={STRATS} />
          <span className="muted" style={{ fontSize: 11.5 }}>{STRAT_TIP[strategy]}</span>
        </div>
        <div className="row">
          <Button icon={<PaperClipOutlined />} onClick={() => fileRef.current?.click()}>上传资料</Button>
          <input ref={fileRef} type="file" accept="application/pdf" hidden
            onChange={(e) => { attach(e.target.files[0]); e.target.value = ''; }} />
          <Input style={{ flex: 1, minWidth: 180 }} value={question} placeholder="例如：间隔重复的复习间隔是怎么安排的？"
            onChange={(e) => setQuestion(e.target.value)} onPressEnter={() => ask()} />
          <Button type="primary" icon={<SendOutlined />} onClick={() => ask()}>提问</Button>
        </div>
      </div>
    </div>
  );
}

function Message({ m, docs, onFollowup, question }) {
  const { message } = AntdApp.useApp();
  const [traceOpen, setTraceOpen] = useState(false);
  const [saved, setSaved] = useState({});
  const [err, setErr] = useState({});
  const busy = !!(m.pending || m.streaming);
  const canSave = !busy && m.role === 'bot' && !!m.text && !!question;

  /* 四态：idle → loading → success / error；success 后禁用，防重复沉淀。 */
  const save = async (kind) => {
    if (!canSave || saved[kind] === 'loading' || saved[kind] === 'ok') return;
    setSaved((s) => ({ ...s, [kind]: 'loading' }));
    setErr((s) => ({ ...s, [kind]: '' }));
    const body = kind === 'note'
      ? {
        question,
        answer: m.text,
        sources: m.sources || [],
        title: question.length > 30 ? question.slice(0, 30) : question,
      }
      : { question, answer: m.text, tag: m.mode || undefined };
    try {
      await api(kind === 'note' ? '/qa/save-note' : '/qa/save-card', {
        method: 'POST', body: JSON.stringify(body),
      });
      setSaved((s) => ({ ...s, [kind]: 'ok' }));
      message.success(kind === 'note' ? '已存为笔记' : '已生成卡片');
    } catch (e) {
      setSaved((s) => ({ ...s, [kind]: 'idle' }));
      const text = e && e.status === 404 ? '后端未升级，暂不可用' : (e && e.message) || '保存失败';
      setErr((s) => ({ ...s, [kind]: text }));
      if (e && e.status === 404) message.warning(text); else message.error(text);
    }
  };

  const saveRow = canSave ? (
    <div className="row" style={{ gap: 4, marginTop: 4 }}>
      <Button size="small" type="text" disabled={saved.note === 'loading' || saved.note === 'ok'}
        loading={saved.note === 'loading'} onClick={() => save('note')}>
        {saved.note === 'ok' ? '已存为笔记' : '存为笔记'}
      </Button>
      <Button size="small" type="text" disabled={saved.card === 'loading' || saved.card === 'ok'}
        loading={saved.card === 'loading'} onClick={() => save('card')}>
        {saved.card === 'ok' ? '已存为卡片' : '生成卡片'}
      </Button>
      {err.note && <span style={{ fontSize: 11.5, color: 'var(--destructive)' }}>{err.note}</span>}
      {err.card && <span style={{ fontSize: 11.5, color: 'var(--destructive)' }}>{err.card}</span>}
    </div>
  ) : null;
  const proc = m.showProc ? (
    <div className="aiproc">
      {STAGES.map((s, i) => (
        <span className={'step ' + (i < (m.stage ?? 0) ? 'done' : i === (m.stage ?? 0) ? 'active' : '')} key={s}>
          <span className="dot" />{s}
        </span>
      ))}
      <span className="elapsed">{(m.elapsed || 0).toFixed(1)}s</span>
    </div>
  ) : null;
  const trace = (m.trace || []).length ? (
    <div className="think">
      <div onClick={() => setTraceOpen(!traceOpen)} style={{ cursor: 'pointer', padding: '7px 10px', fontSize: 12, color: 'var(--muted-foreground)' }}>
        <RightOutlined rotate={traceOpen ? 90 : 0} style={{ marginRight: 5 }} />
        检索依据（{m.trace.length}）
      </div>
      {traceOpen && <div className="trace">{m.trace.map((t, i) => <div key={i}>· {esc(t)}</div>)}</div>}
    </div>
  ) : null;
  return (
    <div className={'msg ' + (m.role === 'user' ? 'user' : 'bot')}>
      <div className="who">{m.role === 'user' ? '你' : 'AI'}</div>
      <div>
        {proc}{trace}
        {(m.text || m.role === 'user' || !busy) && (
          <div className="bubble">
            {m.role === 'bot' ? <Markdown text={m.text} /> : esc(m.text)}
            {m.streaming && <span className="stream-caret" />}
          </div>
        )}
        <SourceChips sources={m.sources || []} mode={m.mode} documents={docs} />
        {saveRow}
        {!busy && (m.followups || []).length > 0 && (
          <div className="followups">
            {m.followups.map((q, i) => (
              <button className="fu" key={i} onClick={() => onFollowup(q)}>
                <ThunderboltFilled style={{ color: 'var(--primary)' }} />{esc(q)}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
