import React, { useMemo } from 'react';
import { Button, Tag } from 'antd';
import { esc, fmtTs, pct } from '../utils.js';
import { AiExplainButton } from '../components/AiExplainDrawer.jsx';

const TYPE_CN = { single: '单选', multiple: '多选', fill: '填空', short: '简答' };

/* 交卷后的练习报告：得分（含正确率与用时）→ 知识点分布 → 逐题回顾（题号索引条）。
   知识点按题目 chapter 聚合，全部来自本次 results，不请求后端。 */
export default function QuizResult({ test, score, elapsed, onJump, onRetest, onBack }) {
  const results = test.results || [];
  const cur = results[test.idx] || {};

  const chapters = useMemo(() => {
    const map = new Map();
    results.forEach((r) => {
      const key = (r.q?.chapter || '').trim();
      if (!key) return;
      const row = map.get(key) || { chapter: key, total: 0, correct: 0 };
      row.total += 1;
      if (r.correct) row.correct += 1;
      map.set(key, row);
    });
    return [...map.values()]
      .map((r) => ({ ...r, rate: r.total ? r.correct / r.total : 0 }))
      .sort((a, b) => b.total - a.total || a.rate - b.rate);
  }, [results]);

  const blank = results.filter((r) => !(r.user || '').trim()).length;
  const wrongN = results.filter((r) => r.correct === false || r.correct === 0).length;
  const rate = score.total ? Math.round((score.correct / score.total) * 100) : 0;

  return (
    <div style={{ maxWidth: 760, margin: '0 auto' }}>
      <div className="v3-card test-score">
        <div className="lab">本次得分</div>
        <div className="big">
          <span className="hl mono">{score.correct}</span>
          <small> / {score.total} 题</small>
        </div>
        <div className="score-strip">
          <div className="m">
            <div className="k">正确率</div>
            <div className="v mono">{rate}%</div>
          </div>
          <div className="m">
            <div className="k">用时</div>
            <div className="v mono">{fmtTs(elapsed)}</div>
          </div>
          <div className="m">
            <div className="k">未作答</div>
            <div className="v mono">{blank}</div>
          </div>
        </div>
        <div className="muted" style={{ fontSize: 11.5, marginTop: 12 }}>
          {wrongN ? `答错的 ${wrongN} 题已收入错题本` : '本次全部答对'}
        </div>
        <div className="row" style={{ justifyContent: 'center', gap: 8, marginTop: 12 }}>
          <Button type="primary" onClick={onRetest}>再测一套</Button>
          <Button onClick={onBack}>返回学习</Button>
        </div>
      </div>

      <div className="v3-card" style={{ marginTop: 12 }}>
        <div className="v3-sh">
          知识点分布
          <span className="meta">{chapters.length ? `${chapters.length} 个章节` : '按章节聚合'}</span>
        </div>
        {chapters.length ? (
          <div className="kp-list">
            {chapters.map((c) => (
              <div className="kp-row" key={c.chapter}>
                <div className="kp-top">
                  <span className="kp-n">{esc(c.chapter)}</span>
                  <span className="kp-v">{c.correct}/{c.total} · {pct(c.rate)}%</span>
                </div>
                <div className="kp-bar">
                  <i style={{ width: `${Math.max(2, pct(c.rate))}%` }} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="muted" style={{ fontSize: 12.5 }}>本次题目未标注章节</div>
        )}
      </div>

      <div className="v3-card" style={{ marginTop: 12 }}>
        <div className="v3-sh">
          逐题回顾
          <span className="meta">{test.idx + 1} / {results.length}</span>
        </div>
        <div className="qidx">
          {results.map((r, i) => {
            const cls = [
              'qi',
              r.correct ? 'ok' : 'bad',
              i === test.idx ? 'on' : '',
            ].filter(Boolean).join(' ');
            return (
              <button key={r.q?.id ?? i} type="button" className={cls} onClick={() => onJump(i)}
                aria-label={`第 ${i + 1} 题${r.correct ? '，正确' : '，错误'}`}>{i + 1}</button>
            );
          })}
        </div>
        <div className="test-q">{esc(cur.q?.stem)}</div>
        <div className="q-meta">
          <Tag>{cur.q?.chapter || '未分章'}</Tag>
          <Tag>{TYPE_CN[cur.q?.qtype] || '题目'}</Tag>
        </div>
        <div className="test-answers">
          <div>你的答案 <span className="mono">{esc(cur.user || '未作答')}</span></div>
          <div>正确答案 <span className="mono">{esc(cur.answer || '—')}</span></div>
          {cur.correct != null && <Tag color={cur.correct ? 'success' : 'error'}>{cur.correct ? '正确' : '错误'}</Tag>}
        </div>
        {cur.error && <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>{esc(cur.error)}</div>}
        {cur.analysis && (
          <div className="test-analysis">
            <div><b>考点：</b>{esc(cur.analysis.point || '-')}</div>
            <div><b>思路：</b>{esc(cur.analysis.approach || '-')}</div>
            <div><b>步骤：</b>{(cur.analysis.steps || []).map(esc).join(' → ') || '-'}</div>
            <div><b>易错点：</b>{(cur.analysis.pitfalls || []).map(esc).join('；') || '-'}</div>
          </div>
        )}
        <div className="row between" style={{ marginTop: 16 }}>
          <Button disabled={test.idx <= 0} onClick={() => onJump(test.idx - 1)}>上一题</Button>
          {cur.q?.id ? <AiExplainButton questionId={cur.q.id} label="AI 讲解" /> : <span />}
          <Button disabled={test.idx >= results.length - 1} onClick={() => onJump(test.idx + 1)}>下一题</Button>
        </div>
      </div>
    </div>
  );
}
