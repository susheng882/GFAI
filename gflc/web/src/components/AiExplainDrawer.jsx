import React, { useCallback, useEffect, useState } from 'react';
import { Button, Drawer, Spin } from 'antd';
import { api } from '../api.js';
import { esc } from '../utils.js';

/* AI 讲解抽屉：四段（考点 / 错因 / 步骤 / 关联知识点），只读展示。
   加载中、失败可重试、模型空返回三种形态都给出下一步动作，不留白屏。 */

const TEXT = { fontSize: 13.5, lineHeight: 1.8, color: 'var(--fg-2)' };

function Section({ label, children }) {
  return (
    <section style={{ marginBottom: 16 }}>
      <div style={{
        fontSize: 12.5, fontWeight: 500, color: 'var(--muted-foreground)', marginBottom: 8,
      }}>
        {label}
      </div>
      {children}
    </section>
  );
}

export default function AiExplainDrawer({ questionId, open, onClose }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);

  const load = useCallback(async () => {
    if (!questionId) return;
    setLoading(true);
    setError('');
    setData(null);
    try {
      const d = await api('/ai/explain', {
        method: 'POST', body: JSON.stringify({ question_id: questionId }),
      });
      setData(d || {});
    } catch (e) {
      setError((e && e.message) || '讲解暂时不可用，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [questionId]);

  useEffect(() => {
    if (open && questionId) load();
  }, [open, questionId, load]);

  const steps = (data && data.steps) || [];
  const related = (data && data.related) || [];
  const blank = !loading && !error && data
    && !(data.analysis || data.why_wrong || steps.length || related.length);

  return (
    <Drawer
      title="AI 讲解"
      placement="right"
      width="min(420px, 92vw)"
      open={open}
      onClose={onClose}
      destroyOnClose
    >
      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '24px 0' }}>
          <Spin size="small" />
          <span style={{ fontSize: 12.5, color: 'var(--muted-foreground)' }}>正在生成讲解</span>
        </div>
      )}

      {!loading && error && (
        <div>
          <div style={{ ...TEXT, marginBottom: 12 }}>{esc(error)}</div>
          <Button size="small" onClick={load}>重试</Button>
        </div>
      )}

      {blank && (
        <div>
          <div style={{ ...TEXT, marginBottom: 12 }}>这次没有生成讲解内容</div>
          <Button size="small" onClick={load}>再试一次</Button>
        </div>
      )}

      {!loading && !error && data && !blank && (
        <div>
          {data.analysis ? (
            <Section label="考点">
              <div style={TEXT}>{esc(data.analysis)}</div>
            </Section>
          ) : null}

          {data.why_wrong ? (
            <Section label="错因">
              <div style={TEXT}>{esc(data.why_wrong)}</div>
            </Section>
          ) : null}

          {steps.length ? (
            <Section label="解题步骤">
              <ol style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                {steps.map((s, i) => (
                  <li key={i} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                    <span style={{
                      fontFamily: 'var(--mono)', fontSize: 11.5, lineHeight: 1.9,
                      color: 'var(--muted-foreground)', minWidth: 16, textAlign: 'right',
                      fontVariantNumeric: 'tabular-nums',
                    }}>
                      {i + 1}
                    </span>
                    <span style={TEXT}>{esc(s)}</span>
                  </li>
                ))}
              </ol>
            </Section>
          ) : null}

          {related.length ? (
            <Section label="关联知识点">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {related.map((r, i) => (
                  <span key={i} style={{
                    border: '1px solid var(--border)', background: 'var(--secondary)',
                    borderRadius: 6, padding: '4px 8px', fontSize: 11.5, color: 'var(--fg-2)',
                  }}>
                    {esc(r)}
                  </span>
                ))}
              </div>
            </Section>
          ) : null}

          {typeof data.attempts === 'number' && (
            <div style={{ fontSize: 11.5, color: 'var(--muted-foreground)' }}>
              {data.attempts
                ? `参考了最近 ${data.attempts} 次作答`
                : '本题还没有作答记录，错因按常见错法给出'}
            </div>
          )}
        </div>
      )}
    </Drawer>
  );
}

/* 按钮 + 抽屉一体：放在列表行里即可，无需外层维护开关状态。 */
export function AiExplainButton({ questionId, label = '讲解', size = 'small' }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button size={size} onClick={() => setOpen(true)}>{label}</Button>
      <AiExplainDrawer questionId={questionId} open={open} onClose={() => setOpen(false)} />
    </>
  );
}
