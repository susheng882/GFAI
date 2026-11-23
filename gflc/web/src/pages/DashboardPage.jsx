import React, { useCallback, useEffect, useRef, useState } from 'react';
import { App as AntdApp, Button, Segmented, Tag, Upload } from 'antd';
import { useNavigate } from 'react-router-dom';
import { api, runTask } from '../api.js';
import { esc, fmtTime, isTodayTask, reviewsText } from '../utils.js';
import TodayQueue from '../components/TodayQueue.jsx';
import LoopStatus from '../components/LoopStatus.jsx';
import AiBoard from './AiBoard.jsx';

/* 指挥台 v3：默认「概览」（hero + 四指标带 + 最近资料 + 快速上传 + 注意事项 + D10 今日待办），
   二级 tab「AI 看板」保留原 AI 生成/拖拽布局能力。 */
export default function DashboardPage() {
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const fileRef = useRef(null);
  const [stats, setStats] = useState(null);
  const [docs, setDocs] = useState([]);
  const [dash, setDash] = useState(null);
  const [due, setDue] = useState([]);
  const [heat, setHeat] = useState(null);
  const [planTasks, setPlanTasks] = useState([]);
  const [mon, setMon] = useState(null);
  const [view, setView] = useState('overview');  // 旧值 'ai' 已废弃，避免落到空视图  // 旧值 'ai' 已废弃，避免落到空视图
  const [loading, setLoading] = useState(true);

  const loadPlans = useCallback(async () => {
    try {
      const plans = (await api('/plans')) || [];
      const details = await Promise.all(plans.slice(0, 8).map(async (p) => {
        try { return await api('/plans/' + p.id); } catch { return null; }
      }));
      const tasks = [];
      details.forEach((d) => {
        if (!d) return;
        (d.tasks || []).forEach((group) => {
          (group.items || []).forEach((t) => {
            if (isTodayTask(t)) tasks.push({ ...t, day_index: group.day, plan_goal: d.goal });
          });
        });
      });
      setPlanTasks(tasks);
    } catch { setPlanTasks([]); }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    const results = await Promise.allSettled([
      api('/dashboard/stats'), api('/documents'), api('/dashboard/latest'),
      api('/review/due?limit=50'), api('/dashboard/heatmap?days=365'),
    ]);
    if (results[0].status === 'fulfilled') setStats(results[0].value);
    if (results[1].status === 'fulfilled') setDocs(results[1].value || []);
    if (results[2].status === 'fulfilled') setDash(results[2].value || null);
    if (results[3].status === 'fulfilled') setDue((results[3].value?.cards) || []);
    if (results[4].status === 'fulfilled') setHeat(results[4].value || null);
    await loadPlans();
    try { setMon(await api('/settings/monitor')); } catch { setMon(null); }
    setLoading(false);
  }, [loadPlans]);

  useEffect(() => { load(); }, [load]);

  const upload = async (file) => {
    if (!file) return;
    try {
      const fd = new FormData();
      fd.append('file', file);
      const created = await api('/documents/upload', { method: 'POST', body: fd });
      await runTask(`/documents/${created.document.id}/parse`, { method: 'POST' }, '解析资料');
      message.success('已收录《' + file.name + '》');
      await load();
    } catch (e) { message.error(e.message); }
  };

  const reparse = async (id) => {
    try {
      await runTask(`/documents/${id}/parse`, { method: 'POST' }, '重新解析');
      message.success('已重新提交解析');
      await load();
    } catch (e) { message.error(e.message); }
  };

  const s = stats || {};
  const dueCount = +s.due || 0;
  const reviewed = +s.reviewed || 0;
  const acc = +s.accuracy || 0;
  const chapters = (s.chapters || []).slice().sort((a, b) => b.cards - a.cards);
  const maxCh = Math.max(1, ...chapters.map((c) => +c.cards || 0));
  const week = s.week || [];
  const failedDocs = docs.filter((d) => d.status === 'failed');

  return (
    <div>
      <div className="v3-hd">
        <div>
          <h1>今天</h1>
          <div className="sub">
            {new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })}
            {' · 一屏看清该做什么'}
          </div>
        </div>
        <Segmented
          value={view}
          onChange={(v) => setView(v)}
          options={[{ label: '概览', value: 'overview' }, { label: '学习任务', value: 'tasks' }]}
        />
      </div>

      {view === 'tasks' ? (
        <AiBoard dash={dash} onReload={load} />
      ) : (
        <div className="v3-grid">
          <LoopStatus />
          <section className="v3-card v3-hero v3-c8">
            <div className="lab">今天要复习</div>
            <div className="big"><span className="hl">{dueCount}</span><small>张卡片</small></div>
            <div className="delta">
              {reviewed > 0 ? `已复习 ${reviewed} 张 · ` : ''}
              {dueCount > 0 ? '建议现在开始' : '暂无到期卡片，稍后再来'}
            </div>
            <div className="v3-acts">
              <Button type="primary" disabled={dueCount === 0} onClick={() => navigate('/review')}>开始复习</Button>
              <Button onClick={() => fileRef.current?.click()}>上传资料</Button>
            </div>
            <WeekChart week={week} />
          </section>

          <section className="v3-card v3-c4">
            <div className="v3-sh">接下来要复习<span className="meta">{chapters.length} 个卡包</span></div>
            {chapters.length ? chapters.slice(0, 4).map((c) => {
              const n = +c.cards || 0;
              const p = Math.round(n / maxCh * 100);
              return (
                <div className="v3-qrow" key={c.name}>
                  <span className="v3-qfill" style={{ width: `${p}%` }} />
                  <div className="v3-qname"><div className="n">{esc(c.name || '未分章')}</div><div className="m">占今天 {p}%</div></div>
                  <div className="v3-qnum">{n}</div>
                </div>
              );
            }) : <div className="muted" style={{ fontSize: 12.5, padding: '20px 0' }}>还没有卡包，上传资料后自动生成。</div>}
            <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 12.5, color: 'var(--muted-foreground)' }}>累计复习 <b style={{ color: 'var(--fg-2)' }}>{reviewed}</b> 张</span>
              <Button size="small" type="text" onClick={() => navigate('/deck')}>全部卡包</Button>
            </div>
          </section>

          <section className="v3-card v3-c12 v3-strip">
            <Metric k="文档" v={s.documents || 0} unit="份" d={`已解析 ${s.chunks || 0} 个切片`} />
            <Metric k="卡片" v={s.cards || 0} unit="张" d={reviewsText(reviewed, s.cards)} />
            <Metric k="答题" v={s.attempts || 0} unit="次" d={`题目 ${s.questions || 0} 道`} />
            <Metric k="正确率" v={acc} unit="%" d={acc >= 80 ? '状态很好' : acc > 0 ? '继续练习' : '暂无数据'} />
          </section>

          <section className="v3-card v3-c12">
            <Heatmap heat={heat} onGo={() => navigate('/review')} />
          </section>

          <section className="v3-card v3-c6">
            <div className="v3-sh">刷题背诵<span className="meta">{dueCount} 张到期</span></div>
            <div className="row" style={{ gap: 8, marginBottom: 10 }}>
              <Button type="primary" onClick={() => navigate('/study')}>去刷题</Button>
              <Button onClick={() => navigate('/review')}>去背诵</Button>
            </div>
            <div className="vmuted2" style={{ lineHeight: 1.9 }}>
              {dueCount > 0
                ? `间隔重复到期 ${dueCount} 张，先背诵再刷题效果最好。`
                : '今天没有到期卡片，可直接刷题巩固。'}
            </div>
            {due.slice(0, 3).map((c, i) => (
              <div className="v3-resume" key={i}>
                <div className="v3-rt">
                  <div className="a">{esc((c.question || c.front || '复习卡片').slice(0, 24))}</div>
                  <div className="b">到期 · 点击去背诵</div>
                </div>
                <Button size="small" type="link" onClick={() => navigate('/review')}>复习</Button>
              </div>
            ))}
          </section>

          <section className="v3-card v3-c6">
            <div className="v3-sh">系统与用量<span className="meta">近 24h</span></div>
            {(() => {
              const ready = docs.filter((d) => d.status === 'ready').length;
              const failed = docs.filter((d) => d.status === 'failed').length;
              const rate = ready + failed > 0 ? Math.round((ready / (ready + failed)) * 100) : 100;
              const calls = mon?.today?.calls ?? 0;
              const cost = mon?.today?.cost ?? 0;
              const tokens = mon?.today?.tokens ?? 0;
              const rows = [
                { k: '解析成功率', v: `${rate}%`, d: `就绪 ${ready} · 失败 ${failed}` },
                { k: '模型调用', v: calls, d: `${(tokens / 1000).toFixed(1)}k tokens` },
                { k: '今日花费', v: `¥${Number(cost).toFixed(3)}`, d: '按调用记录累计' },
                { k: '任务队列', v: (mon?.worker?.queue_size ?? 0), d: `视频并发 ${mon?.worker?.video_workers ?? 0}` },
              ];
              return rows.map((r) => (
                <div className="v3-resume" key={r.k}>
                  <div className="v3-rt"><div className="a">{r.k}</div><div className="b">{r.d}</div></div>
                  <div style={{ fontSize: 15, fontVariantNumeric: 'tabular-nums' }}>{r.v}</div>
                </div>
              ));
            })()}
          </section>

          <section className="v3-card v3-c6">
            <div className="v3-sh">最近资料<span className="meta">{docs.length} 份</span></div>
            {docs.length ? docs.slice(0, 4).map((d) => (
              <div className="v3-resume" key={d.id}>
                <div className="v3-rt">
                  <div className="a">{esc(d.title || '未命名')}</div>
                  <div className="b">{d.source_type === 'video' ? '视频' : d.source_type === 'note' ? '笔记' : '文档'} · {fmtTime(d.updated_at || d.created_at)}</div>
                </div>
                <Tag color={d.status === 'ready' ? 'success' : d.status === 'failed' ? 'error' : 'processing'}>
                  {{ pending: '待解析', parsing: '解析中', ready: '就绪', failed: '失败' }[d.status] || d.status}
                </Tag>
              </div>
            )) : <div className="muted" style={{ fontSize: 12.5, padding: '20px 0' }}>还没有资料，上传一份 PDF 开始。</div>}
          </section>

          <section className="v3-card v3-c6">
            <div className="v3-sh">需要注意</div>
            {failedDocs.slice(0, 3).map((d) => (
              <div className="v3-resume" key={d.id}>
                <div className="v3-rt"><div className="a">{esc(d.title || '未命名')} 解析失败</div><div className="b">点击可重新解析</div></div>
                <Button size="small" type="text" onClick={() => reparse(d.id)}>重试</Button>
              </div>
            ))}
            {dueCount > 0 && (
              <div className="v3-resume">
                <div className="v3-rt"><div className="a">{dueCount} 张卡片到期</div><div className="b">间隔重复到期，建议今天补上</div></div>
                <Button size="small" type="link" onClick={() => navigate('/review')}>去复习</Button>
              </div>
            )}
            {!failedDocs.length && dueCount === 0 && !planTasks.length && (
              <div className="muted" style={{ fontSize: 12.5, padding: '20px 0' }}>一切正常，没有待处理事项。</div>
            )}
          </section>

          <section className="v3-card v3-c6">
            <div className="v3-sh">快速上传<span className="meta">PDF / Word / MD · 自动解析分卡</span></div>
            <div className="drop" onClick={() => fileRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { e.preventDefault(); upload(e.dataTransfer.files[0]); }}>
              <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--foreground)' }}>点击或拖拽 PDF / Word / MD 到此处</div>
              <div style={{ fontSize: 12.5 }}>上传后自动解析、生成背诵卡片</div>
            </div>
            <input ref={fileRef} type="file" accept=".pdf,.docx,.md,.markdown,.txt" hidden
              onChange={(e) => { upload(e.target.files[0]); e.target.value = ''; }} />
          </section>
        </div>
      )}
    </div>
  );
}

function Metric({ k, v, unit, d }) {
  return (
    <div className="m"><div className="k">{k}</div><div className="v">{v}<small>{unit}</small></div><div className="d">{d}</div></div>
  );
}

function Heatmap({ heat, onGo }) {
  const days = (heat && heat.days) || [];
  const streak = (heat && heat.streak) || { current: 0, longest: 0 };
  const summary = (heat && heat.summary) || { active_days: 0, total_reviews: 0, total_quiz: 0 };
  const active = days.some((d) => (+d.total || 0) > 0);

  // 周为列、周一在上的 7 行；首列前面补空格对齐星期
  const cells = [];
  if (days.length) {
    const firstDow = (new Date(days[0].date + 'T00:00:00').getDay() + 6) % 7;
    for (let i = 0; i < firstDow; i += 1) cells.push(null);
    days.forEach((d) => cells.push(d));
    while (cells.length % 7 !== 0) cells.push(null);
  }
  const weeks = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));

  // 4 档透明度（同一强调色），延后只留痕不计入
  const level = (t) => (t <= 0 ? 0 : t <= 2 ? 1 : t <= 5 ? 2 : t <= 9 ? 3 : 4);

  return (
    <>
      <div className="v3-sh">学习热力图<span className="meta">近 {days.length || 365} 天</span></div>
      <div className="hm-meta">
        <span>连续 <b>{streak.current}</b> 天</span>
        <span>最长 <b>{streak.longest}</b> 天</span>
        <span>活跃 <b>{summary.active_days}</b> 天</span>
        <span className="hm-legend">少
          {[1, 2, 3, 4].map((l) => <i className={'hm-cell hm-l' + l} key={l} />)}
          多
        </span>
      </div>
      <div className="hm-wrap">
        <div className="hm-weeks" aria-label="学习热力图">
          {weeks.map((wk, wi) => (
            <div className="hm-col" key={wi}>
              {wk.map((d, di) => (d ? (
                <div
                  key={d.date}
                  className={'hm-cell hm-l' + level(+d.total || 0)}
                  title={`${d.date} · 复习 ${+d.review || 0} · 刷题 ${+d.quiz || 0}`}
                />
              ) : <div className="hm-cell hm-blank" key={'b' + wi + '-' + di} />))}
            </div>
          ))}
        </div>
      </div>
      {!active && (
        <div className="hm-zero">
          还没有学习记录，去复习或刷题开始
          <Button size="small" type="link" onClick={onGo}>去复习</Button>
        </div>
      )}
    </>
  );
}

function WeekChart({ week }) {
  const max = Math.max(1, ...week.map((x) => +x.value || 0));
  const pts = week.map((x, i) => [8 + (week.length > 1 ? i * 624 / (week.length - 1) : 312), 120 - ((+x.value || 0) / max) * 96]);
  let line = '';
  if (pts.length > 1) {
    line = pts.map((p, i) => {
      if (i === 0) return `M${p[0].toFixed(1)} ${p[1].toFixed(1)}`;
      const p0 = pts[i - 1], p1 = pts[i], p2 = pts[i + 1] || p1, p3 = pts[i + 2] || p2;
      const c1x = p1[0] + (p2[0] - p0[0]) / 6, c1y = p1[1] + (p2[1] - p0[1]) / 6;
      const c2x = p2[0] - (p3[0] - p1[0]) / 6, c2y = p2[1] - (p3[1] - p1[1]) / 6;
      return ` C${c1x.toFixed(1)} ${c1y.toFixed(1)} ${c2x.toFixed(1)} ${c2y.toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
    }).join('');
  }
  return (
    <div className="v3-chart">
      <div className="t">近 {week.length || 7} 天作答</div>
      {week.some((x) => +x.value > 0) ? (
        <>
          <svg viewBox="0 0 640 120" width="100%" height="112" preserveAspectRatio="none">
            {[0, .5, 1].map((t) => (
              <line key={t} x1="0" y1={(8 + 96 * t).toFixed(1)} x2="640" y2={(8 + 96 * t).toFixed(1)}
                stroke="var(--border)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
            ))}
            {line && <>
              <path d={`${line} L632 120 L8 120 Z`} fill="var(--primary)" opacity=".05" />
              <path d={line} fill="none" stroke="var(--primary)" strokeWidth="2"
                vectorEffect="non-scaling-stroke" strokeLinecap="round" />
            </>}
          </svg>
          <div className="v3-axis">{week.map((x, i) => <span key={i}>{esc(x.label)}</span>)}</div>
        </>
      ) : <div className="muted" style={{ fontSize: 12.5, padding: '24px 0' }}>还没有作答记录，去「刷题」或「复习」开始吧。</div>}
    </div>
  );
}
