import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { App as AntdApp, Button, Dropdown, Input, InputNumber, Modal, Tag } from 'antd';
import { MoreOutlined } from '@ant-design/icons';
import { api } from '../api.js';
import { esc } from '../utils.js';
import { isTypingTarget, useTodayQueue } from '../hooks.js';
import EmptyState from '../components/EmptyState.jsx';
import Markdown from '../components/Markdown.jsx';

const GOAL_KEY = 'gflc_review_goal';
/* 延后档位：调用 POST /review/{id}/defer，body {days}。 */
const DEFER_OPTIONS = [
  { key: 'defer-1', label: '明天' },
  { key: 'defer-3', label: '3 天后' },
  { key: 'defer-7', label: '7 天后' },
];
const RATINGS = [
  { r: 1, label: '忘记', hint: '稍后重现', type: 'default' },
  { r: 2, label: '费力', hint: '短间隔', type: 'default' },
  { r: 3, label: '记住', hint: '正常间隔', type: 'primary' },
  { r: 4, label: '秒懂', hint: '长间隔', type: 'default' },
];

/* 「取消掌握」的显示依据：/review/due 已直接返回 mastery（0–1），
   无需额外拉整张卡片表。本会话里标记过掌握的卡用 masteredRef 补充识别。 */

/* 天数 → 中文间隔文案（预览接口返回数字时兜底转换）。 */
function daysText(d) {
  const n = Number(d);
  if (!Number.isFinite(n)) return null;
  if (n <= 0) return '刚学完';
  if (n < 1) return '几小时后';
  if (n < 2) return '明天';
  return `${Math.round(n)} 天后`;
}

/* 归一化 /review/preview 返回值：兼容 {1:'…'} / {intervals:[…]} / 数组 / {days:…}。
   任一档拿不到就留空，按钮回退到 RATINGS.hint 占位语义，不编造天数。 */
function normalizePreview(raw) {
  if (!raw) return null;
  let src = raw;
  if (!Array.isArray(src)) src = raw.intervals || raw.preview || raw.next_intervals || raw;
  const out = {};
  for (let r = 1; r <= 4; r++) {
    const v = Array.isArray(src) ? src[r - 1] : (src[r] ?? src[String(r)]);
    if (typeof v === 'string' && v.trim()) out[r] = v.trim();
    else if (v && typeof v === 'object') {
      out[r] = v.text || v.label || v.desc || (v.days != null ? daysText(v.days) : null) || null;
    } else if (typeof v === 'number') out[r] = daysText(v);
  }
  return Object.keys(out).length ? out : null;
}

/* 复习：FSRS 到期卡片，单卡聚焦 + 底部四档评分。
   B4 评分显示下次间隔 / B5 今日队列 / B7 标记掌握 / B9 快捷键 / B10 会话内 More（含延后）。 */
export default function ReviewPage() {
  const { message, modal } = AntdApp.useApp();
  const navigate = useNavigate();
  const [due, setDue] = useState([]);
  const [revealed, setRevealed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [doneToday, setDoneToday] = useState(0);
  const [goal, setGoal] = useState(() => {
    const n = Number(localStorage.getItem(GOAL_KEY));
    return n > 0 ? n : 20;
  });
  const [preview, setPreview] = useState(null);
  const [editCard, setEditCard] = useState(null);
  const [editSaving, setEditSaving] = useState(false);
  const [deferBusy, setDeferBusy] = useState(false);
  // id → 掌握度真值（0–1）。现在 /review/due 直接返回 mastery，这里只记录本会话
  // 标记过掌握的卡，用于「取消掌握」入口判断（无需再拉 500 张卡）
  const [masteryMap, setMasteryMap] = useState({});
  const masteredRef = useRef(new Set());
  const queue = useTodayQueue();

  const changeGoal = (v) => {
    const n = Math.max(1, Math.min(500, v || 20));
    setGoal(n);
    localStorage.setItem(GOAL_KEY, String(n));
  };

  const load = useCallback(async () => {
    setLoading(true);
    try { setDue((await api('/review/due?limit=50'))?.cards || []); } catch { setDue([]); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  /* B4：当前卡变化时预览四档间隔，文案取接口真值；
     接口失败时回落到评分按钮的语义 hint，不编造天数。 */
  const cardId = due[0]?.id;
  useEffect(() => {
    if (!cardId) { setPreview(null); return; }
    let alive = true;
    setPreview(null);
    (async () => {
      try {
        const raw = await api('/review/preview', { method: 'POST', body: JSON.stringify({ card_id: cardId }) });
        if (alive) setPreview(normalizePreview(raw));
      } catch {
        if (alive) setPreview(null);
      }
    })();
    return () => { alive = false; };
  }, [cardId]);

  const rate = useCallback(async (r) => {
    const card = due[0];
    if (!card) return;
    try {
      await api(`/review/${card.id}`, { method: 'POST', body: JSON.stringify({ rating: r }) });
      setDue((d) => d.slice(1)); setRevealed(false);
      setDoneToday((n) => n + 1);
      if (due.length === 1) message.success('这一轮复习完成');
    } catch (e) { message.info(e.message || '评分暂未保存，请重试'); }
  }, [due, message]);

  /* B7：标记掌握（rating=0，后端把 mastery 置 1 并把 due 推到远期）。
     先移出当前队列，再同步服务端；同步失败只提示状态，不把卡片放回来打断节奏。 */
  const markMastered = (card) => {
    masteredRef.current.add(card.id);
    setDue((d) => d.filter((c) => c.id !== card.id));
    setRevealed(false);
    setDoneToday((n) => n + 1);
    message.success('已标记为掌握');
    api(`/review/${card.id}`, { method: 'POST', body: JSON.stringify({ rating: 0 }) })
      .catch(() => message.info('已本地标记，服务端同步失败'));
  };

  const saveEdit = async () => {
    if (!editCard) return;
    setEditSaving(true);
    try {
      await api(`/cards/${editCard.id}`, { method: 'PATCH', body: JSON.stringify({
        question: editCard.question, answer: editCard.answer,
      }) });
      setDue((d) => d.map((c) => c.id === editCard.id
        ? { ...c, question: editCard.question, answer: editCard.answer } : c));
      message.success('已保存卡片');
      setEditCard(null);
    } catch (e) { message.info(e.message || '保存失败'); }
    finally { setEditSaving(false); }
  };

  /* B10 延后：POST /review/{id}/defer {days:1|3|7}，成功后把这张卡移出当前队列。
     后端未升级（404）时只提示，不动队列，避免前端与排期状态不一致。 */
  const deferCard = async (card, days) => {
    if (deferBusy) return;
    setDeferBusy(true);
    try {
      await api(`/review/${card.id}/defer`, { method: 'POST', body: JSON.stringify({ days }) });
      setDue((d) => d.filter((c) => c.id !== card.id));
      setRevealed(false);
      message.success(days === 1 ? '已延后到明天' : `已延后 ${days} 天`);
    } catch (e) {
      if (e?.status === 404) message.info('后端尚未升级，延后暂不可用');
      else message.info(e.message || '延后失败');
    } finally { setDeferBusy(false); }
  };

  /* 取消掌握：调 POST /cards/{id}/reset，把 mastery / reps / due / FSRS 全部归零，
     卡片随后会重新进入待复习队列。二次确认防止误点。 */
  const unmasterCard = (card) => {
    modal.confirm({
      title: '取消掌握这张卡片？',
      content: '掌握度、复习次数与下次排期会一起归零，卡片将重新进入复习队列。',
      okText: '取消掌握', cancelText: '保留',
      onOk: async () => {
        try {
          await api(`/cards/${card.id}/reset`, { method: 'POST' });
          masteredRef.current.delete(card.id);
          setMasteryMap((m) => ({ ...m, [card.id]: 0 }));
          setDue((d) => d.filter((c) => c.id !== card.id));
          setRevealed(false);
          message.success('已取消掌握，将重新进入复习');
        } catch (e) { message.info(e.message || '取消掌握失败'); }
      },
    });
  };

  /* B10：会话内 More 菜单。标记掌握 / 取消掌握 / 延后 / 重置 / 编辑 / 删除全部走真实接口。 */
  const onMore = (key) => {
    const card = due[0];
    if (!card) return;
    if (key === 'mastered') { markMastered(card); return; }
    if (key === 'unmaster') { unmasterCard(card); return; }
    if (key.startsWith('defer-')) { deferCard(card, Number(key.slice(6))); return; }
    if (key === 'edit') {
      setEditCard({ id: card.id, question: card.question || '', answer: card.answer || '' });
      return;
    }
    if (key === 'delete') {
      api(`/cards/${card.id}`, { method: 'DELETE' }).then(() => {
        setDue((d) => d.filter((c) => c.id !== card.id)); setRevealed(false);
        message.success('已删除卡片');
      }).catch((e) => message.info(e.message || '删除失败'));
      return;
    }
    if (key === 'reset') {
      api(`/cards/${card.id}/reset`, { method: 'POST' }).then(() => {
        setDue((d) => d.filter((c) => c.id !== card.id)); setRevealed(false);
        message.success('已重置这张卡片');
      }).catch((e) => message.info(e.message || '重置失败'));
    }
  };
  /* 取消掌握只在「确实已掌握」时出现：掌握度 ≥ 0.99，或本会话标记过掌握（服务端可能还在同步）。
     普通卡不显示，避免把正常复习中的卡片误清进度。 */
  const currentCard = due[0];
  // 掌握度优先用卡自带 mastery（/review/due 已返回），其次看本会话是否标记过
  const canUnmaster = !!currentCard
    && ((Number(currentCard.mastery ?? masteryMap[currentCard.id]) || 0) >= 0.99
        || masteredRef.current.has(currentCard.id));
  const moreItems = [
    { key: 'mastered', label: '标记掌握' },
    ...(canUnmaster ? [{ key: 'unmaster', label: '取消掌握' }] : []),
    { key: 'defer', label: '延后复习', children: DEFER_OPTIONS },
    { type: 'divider' },
    { key: 'reset', label: '重置进度' },
    { key: 'edit', label: '编辑卡片' },
    { type: 'divider' },
    { key: 'delete', label: '删除卡片', danger: true },
  ];

  /* B9：1–4 评分、Space 翻面 / 下一题、方向键翻卡；输入框聚焦或编辑弹窗打开时不触发。 */
  useEffect(() => {
    if (editCard) return undefined;
    const onKey = (e) => {
      if (isTypingTarget(e.target)) return;
      if (e.key === ' ') {
        e.preventDefault();
        if (!revealed) setRevealed(true);
        else { setDue((d) => d.slice(1)); setRevealed(false); }
        return;
      }
      if (revealed && ['1', '2', '3', '4'].includes(e.key)) {
        e.preventDefault(); rate(Number(e.key)); return;
      }
      if (!revealed && e.key === 'ArrowRight') { e.preventDefault(); setRevealed(true); return; }
      if (revealed && e.key === 'ArrowLeft') { e.preventDefault(); setRevealed(false); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [revealed, rate, editCard]);

  if (loading) return null;
  if (!due.length) {
    return (
      <div className="rev-page">
        <div className="v3-card"><EmptyState title="今天没有到期的卡片" desc="间隔重复会在该复习时才推给你" action="去背诵" onAction={() => navigate('/study')} /></div>
      </div>
    );
  }
  const c = due[0];
  const remaining = due.length;
  const progress = Math.min(100, Math.round(doneToday / goal * 100));
  return (
    <div className="rev-page">
      {/* B5 今日队列条：复习 Y + 新学 Z = 今日 W，唯一荧光笔标 W */}
      <div className="queue-bar">
        <div className="queue-bar-t">
          <span>今日队列</span>
          <span className="muted">复习与新学合并</span>
        </div>
        <div className="queue-bar-b">
          <span>复习 <span className="mono">{queue.review}</span></span>
          <span className="queue-op">+</span>
          <span>新学 <span className="mono">{queue.fresh}</span></span>
          <span className="queue-op">=</span>
          <span>今日 <b className="hl mono">{queue.total}</b> 项</span>
        </div>
        {!queue.total && !queue.loading && (
          <div className="queue-zero">今日暂无队列，去背诵页挑一个卡包开始</div>
        )}
      </div>

      <div className="v3-card" style={{ marginBottom: 12, padding: '12px 16px' }}>
        <div className="row between" style={{ marginBottom: 8 }}>
          <span>今日目标 <span className="mono">{doneToday}/{goal}</span> 张</span>
          <span className="row" style={{ gap: 6 }}>
            <span className="muted" style={{ fontSize: 11.5 }}>目标</span>
            <InputNumber size="small" min={1} max={500} value={goal} onChange={changeGoal} style={{ width: 72 }} />
          </span>
        </div>
        <div className="prog"><i style={{ width: `${progress}%` }} /></div>
        <div className="row between" style={{ marginTop: 8, fontSize: 11.5, color: 'var(--muted-foreground)' }}>
          <span>剩余 <span className="mono" style={{ color: 'var(--foreground)' }}>{remaining}</span> 张待复习</span>
          <span>忘记 · 费力 · 记住 · 秒懂 决定下次出现间隔</span>
        </div>
      </div>

      <div className="row between" style={{ marginBottom: 12 }}>
        <span className="muted">当前卡片 · 第 {c.page || '?'} 页 · 已复习 {c.reps || 0} 次</span>
        <Dropdown menu={{ items: moreItems, onClick: ({ key }) => onMore(key) }} trigger={['click']} placement="bottomRight">
          <Button size="small" type="text" icon={<MoreOutlined />} loading={deferBusy}>更多</Button>
        </Dropdown>
      </div>

      <div className="v3-card flash">
        <div className="q">{esc(c.question)}</div>
        {c.note_title && (
          <div className="rev-source">
            <span>来源：</span>
            <button type="button" className="rev-source-link"
              onClick={() => navigate(c.source_note_id ? `/notes?note=${c.source_note_id}` : '/notes')}>
              {c.note_title}
            </button>
          </div>
        )}
        {revealed && <div className="a"><Markdown text={c.answer} /></div>}
      </div>

      <div className="rate">
        {!revealed ? (
          <>
            <Button type="primary" onClick={() => setRevealed(true)}>显示答案</Button>
            <span className="muted rate-tip">想好了再翻 · 空格翻面</span>
          </>
        ) : RATINGS.map((x) => (
          <div key={x.r} className="rate-item">
            <Button type={x.type} onClick={() => rate(x.r)}
              title={preview?.[x.r] ? `评分 ${x.r} · 下次 ${preview[x.r]}` : `评分 ${x.r} · ${x.hint}`}>
              {x.label}<span className="mono muted" style={{ fontSize: 10.5, marginLeft: 5 }}>{x.r}</span>
            </Button>
            <span className="rate-hint">{preview?.[x.r] || x.hint}</span>
          </div>
        ))}
      </div>
      {revealed && (
        <div className="row" style={{ justifyContent: 'center', marginTop: 8 }}>
          <Button size="small" type="text" onClick={() => markMastered(c)}>标记掌握</Button>
        </div>
      )}
      <div className="row" style={{ justifyContent: 'center', marginTop: 12 }}>
        <Tag>剩余 {remaining} 张</Tag>
      </div>

      {editCard && (
        <Modal open onCancel={() => setEditCard(null)} title="编辑卡片"
          okText="保存" cancelText="取消" onOk={saveEdit} confirmLoading={editSaving}>
          <div className="edit-field">
            <div className="edit-label">问题</div>
            <Input.TextArea rows={3} value={editCard.question}
              onChange={(e) => setEditCard({ ...editCard, question: e.target.value })} />
          </div>
          <div className="edit-field">
            <div className="edit-label">答案</div>
            <Input.TextArea rows={4} value={editCard.answer}
              onChange={(e) => setEditCard({ ...editCard, answer: e.target.value })} />
          </div>
        </Modal>
      )}
    </div>
  );
}
