import React, { useCallback, useEffect, useState } from 'react';
import { Button, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.js';

/* ============================================================
   五步闭环状态条：资料 → 笔记 → 卡片 → 刷题 → 复习。
   数据源 GET /api/dashboard/loop（后端只读聚合）。
   接口 404 / 失败时降级为占位说明，绝不让概览页白屏。
   ============================================================ */
export default function LoopStatus() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api('/dashboard/loop');
      setData(r || null);
      setFailed(false);
    } catch {
      setData(null);
      setFailed(true);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  // 降级占位：接口未上线（404）或读取失败时的 0 数据形态
  if (failed || !data || !Array.isArray(data.steps)) {
    return (
      <section className="v3-card v3-c12">
        <div className="v3-sh">学习闭环<span className="meta">5 步</span></div>
        <div className="muted" style={{ fontSize: 12.5 }}>
          {failed ? '闭环进度暂时无法显示，可稍后重试' : '闭环进度加载中…'}
        </div>
        <div style={{ marginTop: 10 }}>
          <Button size="small" type="text" onClick={load}>重新加载</Button>
        </div>
      </section>
    );
  }

  const steps = data.steps;
  const doneCount = steps.filter((s) => s.done).length;

  return (
    <section className="v3-card v3-c12">
      <div className="v3-sh">
        学习闭环
        <span className="meta">{doneCount}/{steps.length} 步 · 今日待办 {data.today ?? 0}</span>
      </div>
      <div className="loop-steps">
        {steps.map((s, i) => (
          <div
            key={s.key}
            className={'loop-step' + (s.done ? ' done' : '') + (data.blocked_step === s.key ? ' blocked' : '')}
            onClick={() => s.action && navigate(s.action)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' && s.action) navigate(s.action); }}
            title={s.description || ''}
          >
            <div className="loop-step-head">
              <span className="loop-step-no mono">{String(i + 1).padStart(2, '0')}</span>
              <span className="loop-step-label">{s.label}</span>
              {s.done
                ? <Tag color="success" className="loop-step-tag">就绪</Tag>
                : <Tag color={s.warning ? 'warning' : 'default'} className="loop-step-tag">待办</Tag>}
            </div>
            <div className="loop-step-num mono">{s.count}<small> / {s.total}</small></div>
            <div className="loop-step-note">
              {s.blocker || s.warning || s.description || '暂无说明'}
            </div>
            {(s.fix_action || s.action) && (
              <div className="loop-step-fix">{s.fix_label || s.action_label || '查看'}</div>
            )}
          </div>
        ))}
      </div>
      <div className="loop-foot">
        <div className="prog" style={{ flex: 1 }}>
          <i style={{ width: `${data.overall || 0}%` }} />
        </div>
        <span className="mono muted" style={{ fontSize: 11.5 }}>{data.overall || 0}%</span>
      </div>
    </section>
  );
}
