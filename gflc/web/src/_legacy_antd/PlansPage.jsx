import React, { useCallback, useEffect, useState } from 'react';
import { App as AntdApp, Button, Checkbox, Input, InputNumber, Segmented, Tag } from 'antd';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/react/daygrid';
import timeGridPlugin from '@fullcalendar/react/timegrid';
import { api, runTask } from '../api.js';
import { esc } from '../utils.js';
import EmptyState from '../components/EmptyState.jsx';

/* 学习计划（v7l plan 对齐）：周目标条 + 日历三视图（月/周/日）+ 计划模板 + 任务列表 + 成长记录。
   日历数据 mock：从计划任务映射到日历事件；无计划时展示 mock 排期。 */

const PLAN_TEMPLATES = [
  { id: 'ebbinghaus', name: '艾宾浩斯冲刺', desc: '按遗忘曲线自动排期', uses: 12 },
  { id: 'exam', name: '真题驱动', desc: '以真题为核心的复习节奏', uses: 8 },
  { id: 'daily2h', name: '每日 2h', desc: '固定时长均衡四科', uses: 5 },
  { id: 'chapter', name: '章节通关', desc: '逐章击破不留死角', uses: 3 },
];

export default function PlansPage() {
  const { message } = AntdApp.useApp();
  const [plans, setPlans] = useState([]);
  const [current, setCurrent] = useState(null);
  const [goal, setGoal] = useState('');
  const [days, setDays] = useState(7);
  const [busy, setBusy] = useState(false);
  const [calView, setCalView] = useState('dayGridMonth');

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

  /* 日历事件：当前计划任务 → 事件；无任务时用 mock 排期保证日历不空 */
  const calEvents = [];
  if (current && current.tasks?.length) {
    current.tasks.forEach((g) => {
      (g.items || []).forEach((t) => {
        const d = new Date();
        d.setDate(d.getDate() + ((g.day || 1) - 1));
        calEvents.push({
          title: t.title, date: d.toISOString().slice(0, 10),
          backgroundColor: t.done ? '#1A7F43' : '#0071E3',
          textColor: '#fff', extendedProps: { done: !!t.done, id: t.id },
        });
      });
    });
  } else {
    // mock 排期：本周 6 项任务
    const base = new Date();
    const mk = (offset, title, done) => {
      const d = new Date(base); d.setDate(d.getDate() + offset);
      calEvents.push({ title, date: d.toISOString().slice(0, 10),
        backgroundColor: done ? '#9DC3F5' : '#0071E3', textColor: '#fff', extendedProps: { done } });
    };
    mk(0, '数据结构·线性表复习', true);
    mk(0, '操作系统·进程管理 20 题', false);
    mk(1, '组成原理·存储系统背卡', false);
    mk(2, '计算机网络·TCP 拥塞控制', false);
    mk(3, '数学·高数极限刷题', false);
    mk(4, '英语·阅读精读 1 篇', false);
  }

  /* 周目标（mock + 真实混合） */
  const weekDone = (current?.tasks || []).flatMap((g) => g.items || []).filter((t) => t.done).length;
  const weekTotal = current?.tasks?.length ? (current.tasks || []).flatMap((g) => g.items || []).length : 6;
  const weekPct = Math.round((weekDone / Math.max(1, weekTotal)) * 100);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* 周目标条（v7l） */}
      <div className="rc-card" style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 14 }}>
        <span style={{ fontSize: 12, fontWeight: 500, whiteSpace: 'nowrap' }}>本周目标 · 第 1 周</span>
        <div className="prog" style={{ flex: 1 }}><i style={{ width: `${weekPct}%` }} /></div>
        <span className="num vmuted2" style={{ fontSize: 11.5, whiteSpace: 'nowrap' }}>
          {weekDone}/{weekTotal} 完成 · {weekPct}%
        </span>
        <Button size="small" type="text">周报</Button>
        <Button size="small" onClick={() => setCurrent(null)}>新建任务</Button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr 280px', gap: 12, alignItems: 'start' }}>
        {/* 左栏：新建计划 + 模板 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="rc-card" style={{ padding: 14 }}>
            <div className="v3-sh" style={{ marginBottom: 8 }}>新建计划</div>
            <Input.TextArea rows={3} value={goal} onChange={(e) => setGoal(e.target.value)}
              placeholder="例如：30 天备考数学期末，每天 2 小时" />
            <div className="row" style={{ marginTop: 10 }}>
              <span style={{ fontSize: 12 }}>天数</span>
              <InputNumber size="small" min={1} max={60} value={days} onChange={(v) => setDays(v || 7)} />
              <Button size="small" type="primary" loading={busy} onClick={create}>生成</Button>
            </div>
          </div>
          <div className="rc-card" style={{ padding: 14 }}>
            <div className="v3-sh" style={{ marginBottom: 8 }}>计划模板</div>
            {PLAN_TEMPLATES.map((t) => (
              <div key={t.id} className="row between" style={{ padding: '7px 0', borderBottom: '1px solid var(--line-soft)' }}>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 500 }}>{t.name}</div>
                  <div className="vmuted2" style={{ fontSize: 10.5 }}>{t.desc}</div>
                </div>
                <Tag style={{ fontSize: 10 }}>{t.uses} 次</Tag>
              </div>
            ))}
          </div>
        </div>

        {/* 中栏：日历三视图（FullCalendar） */}
        <div className="rc-card" style={{ padding: 12, minHeight: 480 }}>
          <div className="row between" style={{ marginBottom: 10 }}>
            <Segmented size="small" value={calView} onChange={setCalView}
              options={[
                { label: '月', value: 'dayGridMonth' },
                { label: '周', value: 'timeGridWeek' },
                { label: '日', value: 'timeGridDay' },
              ]} />
            <span className="vmuted2" style={{ fontSize: 11 }}>
              {new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })}
            </span>
          </div>
          <FullCalendar
            plugins={[dayGridPlugin, timeGridPlugin]}
            initialView={calView}
            events={calEvents}
            locale="zh-cn"
            headerToolbar={{ left: 'prev,next', center: 'title', right: '' }}
            height={440}
            dayMaxEvents={3}
            eventDisplay="block"
            eventContent={(info) => (
              <div style={{ fontSize: 10.5, padding: '1px 4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                textDecoration: info.event.extendedProps.done ? 'line-through' : 'none' }}>
                {info.event.title}
              </div>
            )}
          />
        </div>

        {/* 右栏：我的计划 */}
        <div className="rc-card" style={{ padding: 14 }}>
          <div className="v3-sh" style={{ marginBottom: 8 }}>我的计划<span className="meta">{plans.length} 个</span></div>
          {plans.length ? plans.map((p) => (
            <div className={'v3-resume' + (current?.id === p.id ? ' on' : '')} key={p.id} style={{ cursor: 'pointer' }}
              onClick={() => openPlan(p.id)}>
              <div className="v3-rt"><div className="a">{esc(p.goal)}</div><div className="b">{p.days} 天计划</div></div>
              <Tag>查看</Tag>
            </div>
          )) : <EmptyState title="还没有计划" desc="输入目标，AI 会拆成逐日任务。" />}

          {current && (
            <div style={{ marginTop: 10, borderTop: '1px solid var(--line-soft)', paddingTop: 10 }}>
              <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 6 }}>{esc(current.goal)}</div>
              {(current.tasks || []).map((g) => (
                <div key={g.day} style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--primary)', marginBottom: 4 }}>第 {g.day} 天</div>
                  {(g.items || []).map((t) => (
                    <div className="row between" key={t.id} style={{ padding: '5px 0' }}>
                      <Checkbox checked={!!t.done} onChange={() => toggle(t)}>
                        <span style={{ fontSize: 11.5, textDecoration: t.done ? 'line-through' : 'none',
                          color: t.done ? 'var(--muted-foreground)' : 'inherit' }}>
                          {esc(t.title)}
                        </span>
                      </Checkbox>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
