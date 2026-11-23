import React, { useState } from 'react';
import { App as AntdApp, Button, Input, Segmented, Tag } from 'antd';
import { api, runTask } from '../api.js';
import { esc } from '../utils.js';

/* AI 看板（旧版 aiDashBoard + dashGrid）：主题生成 / 日周月切换 / 卡片渲染与单卡编辑。 */
export default function AiBoard({ dash, onReload }) {
  const { message } = AntdApp.useApp();
  const [theme, setTheme] = useState(dash?.theme || '');
  const [scope, setScope] = useState(dash?.scope || 'week');
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);

  React.useEffect(() => { if (dash) { setTheme(dash.theme || ''); setScope(dash.scope || 'week'); } }, [dash]);

  const generate = async (nextScope = scope) => {
    const t = theme.trim();
    if (!t) { message.warning('请输入主题'); return; }
    setBusy(true);
    try {
      await runTask('/dashboard/generate', { method: 'POST', body: JSON.stringify({ theme: t, scope: nextScope }) }, '生成仪表盘');
      setScope(nextScope);
      message.success('已生成专属仪表盘');
      onReload?.();
    } catch (e) { message.error(e.message); } finally { setBusy(false); }
  };

  const changeScope = async (v) => {
    if (!dash) { setScope(v); return; }
    await generate(v);
  };

  const saveCard = async (card) => {
    const payload = { card_id: card.id };
    ['title', 'value', 'unit', 'hint'].forEach((f) => { if (card[f] != null) payload[f] = card[f]; });
    if (card.items != null) payload.items = card.items;
    if (card.data != null) payload.data = card.data;
    try {
      await api(`/dashboard/${dash.id}/card`, { method: 'PATCH', body: JSON.stringify(payload) });
      setEditing(null);
      message.success('已保存卡片');
      onReload?.();
    } catch (e) { message.error(e.message); }
  };

  const cards = dash?.config?.cards || [];
  return (
    <div>
      <div className="row" style={{ marginBottom: 16 }}>
        <Input style={{ maxWidth: 460 }} placeholder="输入主题，AI 生成专属仪表盘（如：考研冲刺计划 / 期末复习 / 英语六级）"
          value={theme} onChange={(e) => setTheme(e.target.value)} onPressEnter={() => generate()} />
        <Button type="primary" loading={busy} onClick={() => generate()}>AI 生成</Button>
        <Segmented value={scope} onChange={changeScope}
          options={[{ label: '日', value: 'day' }, { label: '周', value: 'week' }, { label: '月', value: 'month' }]} />
        {dash && <Button type="text" onClick={async () => {
          try { await api('/dashboard/' + dash.id, { method: 'DELETE' }).catch(() => {}); } catch { /* 后端无删除布局接口时仅本地重置 */ }
          onReload?.();
        }}>默认视图</Button>}
      </div>
      {cards.length ? (
        <div className="dashgrid">
          {cards.map((cd) => (
            <div className="dcard" key={cd.id} style={{ flex: `${cd.span || 4} 1 0` }}>
              <div className="dflip">
                <div className="dfront" onDoubleClick={() => setEditing(cd.id)}>
                  <div className="row between" style={{ fontSize: 12, color: 'var(--muted-foreground)', marginBottom: 12 }}>
                    <span>{esc(cd.title || '')}</span><span>{esc((cd.hint || '').replace(/^真实数据[:：]\s*/, ''))}</span>
                  </div>
                  <CardBody card={cd} />
                </div>
                {editing === cd.id && (
                  <div className="dback">
                    <CardEdit card={cd} onSave={saveCard} onCancel={() => setEditing(null)} />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="muted" style={{ padding: '36px 0', textAlign: 'center', fontSize: 13 }}>
          还没有 AI 看板。输入主题点「AI 生成」，或切回「概览」看默认指挥台。
        </div>
      )}
    </div>
  );
}

function CardBody({ card }) {
  const unit = card.unit || '';
  if (['bar', 'line'].includes(card.type)) {
    const data = card.data || [];
    const max = Math.max(1, ...data.map((x) => +x.value || 0));
    if (!data.length || data.every((x) => !(+x.value))) {
      return <div className="muted" style={{ fontSize: 12 }}>暂无数据</div>;
    }
    return (
      <div className="bars">
        {data.map((x, i) => (
          <div className="b" key={i}>
            <i style={{ height: `${Math.max(6, (+x.value || 0) / max * 74)}px` }} />
            <span>{esc(x.label)}</span>
          </div>
        ))}
      </div>
    );
  }
  if (card.type === 'list') {
    return <ul className="dlist">{(card.items || []).map((x, i) => <li key={i}>{esc(x)}</li>)}</ul>;
  }
  const v = card.value ?? 0;
  return <div className="dv">{unit === '张' ? <span className="hl">{esc(v)}</span> : esc(v)}<small>{esc(unit)}</small></div>;
}

function CardEdit({ card, onSave, onCancel }) {
  const [draft, setDraft] = useState({ ...card });
  const set = (k, v) => setDraft((d) => ({ ...d, [k]: v }));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, height: '100%' }}>
      <div style={{ fontSize: 11, color: 'var(--muted-foreground)' }}>标题</div>
      <Input size="small" value={draft.title || ''} onChange={(e) => set('title', e.target.value)} />
      {draft.type !== 'list' && !['bar', 'line'].includes(draft.type) && (
        <>
          <div style={{ fontSize: 11, color: 'var(--muted-foreground)' }}>数值 / 单位 / 说明</div>
          <div className="row" style={{ gap: 4 }}>
            <Input size="small" value={draft.value ?? ''} onChange={(e) => set('value', e.target.value)} />
            <Input size="small" style={{ width: 60 }} value={draft.unit || ''} onChange={(e) => set('unit', e.target.value)} />
          </div>
          <Input size="small" value={draft.hint || ''} onChange={(e) => set('hint', e.target.value)} />
        </>
      )}
      {draft.type === 'list' && (
        <textarea className="mini" value={(draft.items || []).join('\n')}
          onChange={(e) => set('items', e.target.value.split('\n').filter(Boolean))} />
      )}
      {['bar', 'line'].includes(draft.type) && (
        <textarea className="mini" value={(draft.data || []).map((x) => `${x.label}:${x.value}`).join('\n')}
          onChange={(e) => set('data', e.target.value.split('\n').filter(Boolean).map((line) => {
            const [label, value] = line.split(':');
            return { label: label?.trim(), value: Number(value || 0) };
          }))} />
      )}
      <div className="row" style={{ marginTop: 'auto', justifyContent: 'flex-end' }}>
        <Tag>{draft.type}</Tag>
        <Button size="small" onClick={onCancel}>取消</Button>
        <Button size="small" type="primary" onClick={() => onSave(draft)}>保存</Button>
      </div>
    </div>
  );
}
