import React, { useState } from 'react';
import { App as AntdApp, Button, Tag, Typography } from 'antd';
import { ClockCircleOutlined, CalendarOutlined, CheckOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.js';

/* ============================================================
   D10 今日待办：把「复习 due」与「计划任务」合并为一个队列。
   复习 due 来自 GET /review/due；计划任务来自 GET /plans + /plans/{id}，
   用 isTodayTask() 判定今天（优先后端 due 字段，缺省回退 day_index===1）。
   勾选计划任务调用 POST /plans/tasks/{id}/toggle。
   ============================================================ */
export default function TodayQueue({ dueCards = [], planTasks = [], onChanged }) {
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const [busy, setBusy] = useState(null);
  const toggle = async (task) => {
    setBusy(task.id);
    try {
      await api(`/plans/tasks/${task.id}/toggle`, { method: 'POST' });
      message.success('已完成：' + task.title);
      onChanged?.();
    } catch (e) {
      message.error(e.message);
    } finally {
      setBusy(null);
    }
  };
  const items = [
    ...dueCards.map((c) => ({
      key: 'r' + c.id, kind: 'review', title: c.question || '复习卡片',
      meta: `第 ${c.page || '?'} 页 · 已复习 ${c.reps || 0} 次`, to: '/review',
    })),
    ...planTasks.map((t) => ({
      key: 'p' + t.id, kind: 'plan', id: t.id, title: t.title || '计划任务',
      meta: t.detail || (t.plan_goal ? '来自计划：' + t.plan_goal : '今日计划'), to: '/plans',
    })),
  ];
  if (!items.length) {
    return <div className="muted" style={{ fontSize: 12.5, padding: '14px 0' }}>今天没有待办，去「学习」或「复习」练几题吧。</div>;
  }
  return (
    <div>
      {items.slice(0, 10).map((it) => (
        <div className="v3-resume" key={it.key}>
          <Tag color={it.kind === 'review' ? 'blue' : 'green'} style={{ flex: '0 0 auto', margin: 0 }}>
            {it.kind === 'review' ? <ClockCircleOutlined /> : <CalendarOutlined />}
            {' '}{it.kind === 'review' ? '复习' : '计划'}
          </Tag>
          <div className="v3-rt" onClick={() => navigate(it.to)} style={{ cursor: 'pointer' }}>
            <div className="a" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{it.title}</div>
            <div className="b">{it.meta}</div>
          </div>
          {it.kind === 'plan' ? (
            <Button size="small" type="text" icon={<CheckOutlined />} loading={busy === it.id}
              onClick={() => toggle(it)} title="标记完成" />
          ) : (
            <Button size="small" type="link" onClick={() => navigate(it.to)}>去复习</Button>
          )}
        </div>
      ))}
      {items.length > 10 && (
        <Typography.Link style={{ fontSize: 12 }} onClick={() => navigate('/plans')}>
          还有 {items.length - 10} 项，查看全部计划
        </Typography.Link>
      )}
    </div>
  );
}
