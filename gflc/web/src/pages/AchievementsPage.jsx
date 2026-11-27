import React, { useEffect, useState } from 'react';
import { App as AntdApp, Button, Progress } from 'antd';
import { TrophyOutlined, FireOutlined, FieldTimeOutlined } from '@ant-design/icons';
import { api } from '../api.js';
import { esc } from '../utils.js';
import EmptyState from '../components/EmptyState.jsx';

/* 成长记录与成就（v7l plan 下半区独立页）：等级 XP / 五指标 / 能力五维 / 里程碑。
   数据全部来自 GET /achievements（后端纯聚合，无新表）。 */

const ABILITY_LABELS = {
  memory: '记忆', understand: '理解', speed: '速度',
  accuracy: '正确率', persistence: '坚持',
};

export default function AchievementsPage() {
  const { message } = AntdApp.useApp();
  const [data, setData] = useState(null);
  const load = () => api('/achievements').then(setData).catch((e) => message.error(e.message));
  useEffect(() => { load(); }, []);

  if (!data) return <EmptyState title="加载中" desc="正在聚合学习记录…" />;
  const { level, xp, xp_next, stats, streak, abilities, milestones } = data;

  return (
    <div style={{ maxWidth: 860, margin: '0 auto' }}>
      {/* 等级卡 */}
      <div className="rc-card" style={{ padding: 20, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 18 }}>
        <div style={{
          width: 64, height: 64, borderRadius: 20, background: 'var(--primary)',
          color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 26, fontWeight: 600, flexShrink: 0,
        }}>Lv{level}</div>
        <div style={{ flex: 1 }}>
          <div className="row between" style={{ marginBottom: 6 }}>
            <span style={{ fontSize: 15, fontWeight: 500 }}>成长等级</span>
            <span className="vmuted2 num" style={{ fontSize: 12 }}>{xp} / {xp_next} XP</span>
          </div>
          <Progress percent={Math.min(100, Math.round(xp / xp_next * 100))} showInfo={false}
            strokeColor="var(--primary)" trailColor="var(--sunken, var(--secondary))" size="small" />
          <div className="row" style={{ gap: 16, marginTop: 8 }}>
            <span style={{ fontSize: 12 }}><FireOutlined style={{ color: 'var(--warning)' }} /> 连续 <b className="num">{streak}</b> 天</span>
            <span className="vmuted2" style={{ fontSize: 12 }}><FieldTimeOutlined /> 累计学习 {stats.hours} 小时{stats.hours_estimate ? '（估算）' : ''}</span>
          </div>
        </div>
      </div>

      {/* 五指标 */}
      <div className="g4" style={{ marginBottom: 12 }}>
        {[
          { k: '学习天数', v: stats.days, unit: '天' },
          { k: '背卡', v: `${stats.cards}/${stats.cards_total}`, unit: '张' },
          { k: '正确率', v: stats.accuracy, unit: '%' },
          { k: '达成率', v: stats.completion, unit: '%' },
        ].map((m) => (
          <div className="rc-card" key={m.k} style={{ padding: 14 }}>
            <div className="vmuted2" style={{ fontSize: 10.5, marginBottom: 4 }}>{m.k}</div>
            <div className="num" style={{ fontSize: 22, fontWeight: 600 }}>{m.v}<small style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>{m.unit}</small></div>
          </div>
        ))}
      </div>

      {/* 能力五维热力条 */}
      <div className="rc-card" style={{ padding: 16, marginBottom: 12 }}>
        <div className="v3-sh" style={{ marginBottom: 10 }}>能力五维</div>
        {Object.entries(abilities).map(([k, v]) => (
          <div key={k} className="row" style={{ gap: 10, marginBottom: 8 }}>
            <span style={{ width: 52, fontSize: 12, color: 'var(--ink-subtle, var(--fg-2))' }}>{ABILITY_LABELS[k] || k}</span>
            <div style={{ flex: 1, display: 'flex', gap: 4 }}>
              {[0, 1, 2, 3, 4].map((i) => (
                <div key={i} style={{
                  height: 9, flex: 1, borderRadius: 2,
                  background: v >= (i + 1) * 20 ? 'var(--primary)' : 'var(--primary-wash, var(--secondary))',
                }} />
              ))}
            </div>
            <span className="num vmuted2" style={{ width: 34, fontSize: 11, textAlign: 'right' }}>{v}</span>
          </div>
        ))}
      </div>

      {/* 里程碑 */}
      <div className="rc-card" style={{ padding: 16 }}>
        <div className="v3-sh" style={{ marginBottom: 10 }}><TrophyOutlined style={{ color: 'var(--primary)', marginRight: 4 }} />里程碑</div>
        <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
          {milestones.map((m) => (
            <span key={m.name} style={{
              fontSize: 12, padding: '6px 12px', borderRadius: 99,
              background: m.done ? 'var(--success-soft)' : 'var(--secondary)',
              color: m.done ? 'var(--success)' : 'var(--muted-foreground)',
              border: `1px solid ${m.done ? 'transparent' : 'var(--line)'}`,
            }}>
              {m.done ? '✓ ' : '○ '}{esc(m.name)}
            </span>
          ))}
        </div>
      </div>

      {/* 今日任务（v7l 成长记录区）：mock 数据，勾选回写计划 */}
      <div className="rc-card" style={{ padding: 16, marginTop: 12 }}>
        <div className="row between" style={{ marginBottom: 10 }}>
          <div className="v3-sh" style={{ marginBottom: 0 }}>今日任务<span className="meta">3/6</span></div>
          <Button size="small" type="text">去计划</Button>
        </div>
        {[
          { t: '背 20 张到期卡', kind: '背诵', time: '08:30', done: true },
          { t: '解析「TCP 拥塞控制」并生成笔记', kind: '视频', time: '09:30', done: true },
          { t: '复盘昨日错题 3 道', kind: '错题', time: '10:20', done: true },
          { t: '2019 真题选择题 40 题', kind: '刷题', time: '14:00', done: false },
          { t: '整理「TCP 拥塞控制」笔记', kind: '笔记', time: '17:00', done: false },
          { t: '睡前轻量复习 10 张卡', kind: '背诵', time: '22:00', done: false },
        ].map((task, i) => (
          <div key={i} className="row" style={{ gap: 10, padding: '8px 0', borderBottom: '1px solid var(--line-soft)' }}>
            <span style={{ width: 14, height: 14, borderRadius: 4, flexShrink: 0,
              border: `1.5px solid ${task.done ? 'var(--success)' : 'var(--line-strong, var(--input))'}`,
              background: task.done ? 'var(--success)' : 'transparent', color: '#fff',
              fontSize: 10, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
              {task.done ? '✓' : ''}
            </span>
            <span style={{ flex: 1, fontSize: 12.5,
              textDecoration: task.done ? 'line-through' : 'none',
              color: task.done ? 'var(--muted-foreground)' : 'var(--ink)' }}>{task.t}</span>
            <span style={{ fontSize: 10.5, padding: '1px 8px', borderRadius: 99,
              background: 'var(--secondary)', color: 'var(--muted-foreground)' }}>{task.kind}</span>
            <span className="num vmuted2" style={{ fontSize: 11 }}>{task.time}</span>
          </div>
        ))}
      </div>

      {/* 今日任务（v7l 成长记录区）：mock 数据，勾选回写计划 */}
      <div className="rc-card" style={{ padding: 16, marginTop: 12 }}>
        <div className="row between" style={{ marginBottom: 10 }}>
          <div className="v3-sh" style={{ marginBottom: 0 }}>今日任务<span className="meta">3/6</span></div>
          <Button size="small" type="text">去计划</Button>
        </div>
        {[
          { t: '背 20 张到期卡', kind: '背诵', time: '08:30', done: true },
          { t: '解析「TCP 拥塞控制」并生成笔记', kind: '视频', time: '09:30', done: true },
          { t: '复盘昨日错题 3 道', kind: '错题', time: '10:20', done: true },
          { t: '2019 真题选择题 40 题', kind: '刷题', time: '14:00', done: false },
          { t: '整理「TCP 拥塞控制」笔记', kind: '笔记', time: '17:00', done: false },
          { t: '睡前轻量复习 10 张卡', kind: '背诵', time: '22:00', done: false },
        ].map((task, i) => (
          <div key={i} className="row" style={{ gap: 10, padding: '8px 0', borderBottom: '1px solid var(--line-soft)' }}>
            <span style={{ width: 14, height: 14, borderRadius: 4, flexShrink: 0,
              border: `1.5px solid ${task.done ? 'var(--success)' : 'var(--line-strong, var(--input))'}`,
              background: task.done ? 'var(--success)' : 'transparent', color: '#fff',
              fontSize: 10, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
              {task.done ? '✓' : ''}
            </span>
            <span style={{ flex: 1, fontSize: 12.5,
              textDecoration: task.done ? 'line-through' : 'none',
              color: task.done ? 'var(--muted-foreground)' : 'var(--ink)' }}>{task.t}</span>
            <span style={{ fontSize: 10.5, padding: '1px 8px', borderRadius: 99,
              background: 'var(--secondary)', color: 'var(--muted-foreground)' }}>{task.kind}</span>
            <span className="num vmuted2" style={{ fontSize: 11 }}>{task.time}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
