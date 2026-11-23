import React, { useCallback, useEffect, useState } from 'react';
import { App as AntdApp, Button, Checkbox, Input, InputNumber, Modal, Tag } from 'antd';
import { api, runTask } from '../api.js';
import { esc } from '../utils.js';
import EmptyState from '../components/EmptyState.jsx';

/* 学习计划：目标 → 后台拆解逐日任务 → 勾选完成（D10 今日待办的数据源）。 */
export default function PlansPage() {
  const { message } = AntdApp.useApp();
  const [plans, setPlans] = useState([]);
  const [current, setCurrent] = useState(null);
  const [goal, setGoal] = useState('');
  const [days, setDays] = useState(7);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setPlans(await api('/plans') || []); } catch { setPlans([]); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openPlan = async (id) => {
    try { setCurrent(await api(`/plans/${id}`)); } catch (e) { message.error(e.message); }
  };

  const create = async () => {
    if (!goal.trim()) { message.warning('请填写学习目标'); return; }
    setBusy(true);
    try {
      const r = await runTask('/plans', { method: 'POST', body: JSON.stringify({ goal: goal.trim(), days }) }, '生成计划');
      message.success('计划已生成');
      setGoal(''); await load();
      if (r?.plan_id) await openPlan(r.plan_id);
    } catch (e) { message.error(e.message); } finally { setBusy(false); }
  };

  const toggle = async (task) => {
    try {
      await api(`/plans/tasks/${task.id}/toggle`, { method: 'POST' });
      await openPlan(current.id);
      await load();
    } catch (e) { message.error(e.message); }
  };

  return (
    <div className="grid g2" style={{ gridTemplateColumns: '300px 1fr', alignItems: 'start' }}>
      <div>
        <div className="v3-card" style={{ marginBottom: 14 }}>
          <div className="v3-sh">新建计划</div>
          <div style={{ fontSize: 12, marginBottom: 4 }}>学习目标</div>
          <Input.TextArea rows={3} value={goal} onChange={(e) => setGoal(e.target.value)}
            placeholder="例如：30 天备考数学期末，每天 2 小时" />
          <div className="row" style={{ marginTop: 10 }}>
            <span style={{ fontSize: 12 }}>天数</span>
            <InputNumber min={1} max={60} value={days} onChange={(v) => setDays(v || 7)} />
            <Button type="primary" loading={busy} onClick={create}>生成计划</Button>
          </div>
        </div>
        <div className="v3-card">
          <div className="v3-sh">我的计划<span className="meta">{plans.length} 个</span></div>
          {plans.length ? plans.map((p) => (
            <div className={'v3-resume' + (current?.id === p.id ? ' on' : '')} key={p.id} style={{ cursor: 'pointer' }}
              onClick={() => openPlan(p.id)}>
              <div className="v3-rt"><div className="a">{esc(p.goal)}</div><div className="b">{p.days} 天计划</div></div>
              <Tag>查看</Tag>
            </div>
          )) : <EmptyState title="还没有计划" desc="输入目标，AI 会拆成逐日任务。" />}
        </div>
      </div>
      <div className="v3-card">
        <div className="v3-sh">{current ? esc(current.goal) : '计划详情'}<span className="meta">{current?.days || 0} 天</span></div>
        {current ? (current.tasks || []).map((g) => (
          <div key={g.day} style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--primary)', marginBottom: 6 }}>第 {g.day} 天</div>
            {(g.items || []).map((t) => (
              <div className="row between" key={t.id} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                <Checkbox checked={!!t.done} onChange={() => toggle(t)}>
                  <span style={{ textDecoration: t.done ? 'line-through' : 'none', color: t.done ? 'var(--muted-foreground)' : 'inherit' }}>
                    {esc(t.title)}
                  </span>
                </Checkbox>
                <span className="muted" style={{ fontSize: 11.5 }}>{esc(t.detail || '')}</span>
              </div>
            ))}
          </div>
        )) : <EmptyState title="选择一个计划" desc="左侧计划列表点击即可查看每日任务。" />}
      </div>
    </div>
  );
}
