import React, { useCallback, useEffect, useState } from 'react';
import { App as AntdApp, Button, Skeleton, Tag, Tooltip } from 'antd';
import {
  ArrowLeftOutlined, FileTextOutlined, FormOutlined, CreditCardOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { api, runTask } from '../api.js';
import { esc, fmtTime, pct } from '../utils.js';
import EmptyState from '../components/EmptyState.jsx';

/* S2 资料二级枢纽：一屏回答「这份资料学到哪了」。
   四块：掌握度总览（唯一 hero）/ 笔记 / 卡片 / 题目，均带 0 数据形态与出口动作。 */

const STATUS_CN = { pending: '待解析', parsing: '解析中', ready: '就绪', failed: '失败' };
const STATUS_COLOR = { ready: 'success', failed: 'error', pending: 'processing', parsing: 'processing' };
const LEVEL_CN = { not_started: '未开始', learning: '学习中', mastered: '已掌握' };
const SOURCE_CN = { manual: '手记', ai: 'AI', video: '视频', import: '导入' };

function dueLabel(ts) {
  if (!ts) return '未排期';
  const t = new Date(ts).getTime();
  if (isNaN(t)) return '未排期';
  if (t <= Date.now()) return '已到期';
  return new Date(ts).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' }) + ' 到期';
}

export default function DocumentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [noteBusy, setNoteBusy] = useState(false);
  const [cardBusy, setCardBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setData(await api(`/documents/${id}/overview`));
    } catch (e) {
      setError(e?.status === 404 ? '资料不存在或已删除' : (e?.message || '读取失败'));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const ready = data?.document?.status === 'ready';

  const genNote = async () => {
    if (!ready) { message.info('资料解析完成后才能生成笔记'); return; }
    if (noteBusy) return;
    setNoteBusy(true);
    message.info('正在生成笔记，约需 10–20 秒');
    try {
      await api(`/documents/${id}/notes`, { method: 'POST', body: JSON.stringify({}) });
      message.success('笔记已生成');
      await load();
    } catch (e) {
      message.error(e.message || '生成失败');
    } finally {
      setNoteBusy(false);
    }
  };

  const genCards = async () => {
    if (!ready) { message.info('资料解析完成后才能生成卡片'); return; }
    if (cardBusy) return;
    setCardBusy(true);
    try {
      await runTask(`/documents/${id}/cards`, { method: 'POST' }, '生成卡片');
      message.success('卡片已生成');
      await load();
    } catch (e) {
      message.error(e.message || '生成失败');
    } finally {
      setCardBusy(false);
    }
  };

  const back = (
    <Button type="text" size="small" icon={<ArrowLeftOutlined />}
      style={{ paddingLeft: 0 }} onClick={() => navigate('/docs')}>
      返回
    </Button>
  );

  if (loading && !data) {
    return (
      <div>
        <div style={{ marginBottom: 16 }}>{back}</div>
        <div className="v3-grid">
          <section className="v3-card v3-c12"><Skeleton active paragraph={{ rows: 3 }} /></section>
          <section className="v3-card v3-c6"><Skeleton active paragraph={{ rows: 3 }} /></section>
          <section className="v3-card v3-c6"><Skeleton active paragraph={{ rows: 3 }} /></section>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div>
        <div style={{ marginBottom: 16 }}>{back}</div>
        <section className="v3-card" style={{ padding: '32px 20px', textAlign: 'center' }}>
          <div style={{ fontSize: 14.5, fontWeight: 500 }}>读取失败</div>
          <div className="muted" style={{ fontSize: 12.5, margin: '4px 0 12px', lineHeight: 1.7 }}>{error}</div>
          <Button onClick={load}>读取失败，点击重试</Button>
        </section>
      </div>
    );
  }

  const doc = data.document;
  const cards = data.cards || {};
  const questions = data.questions || {};
  const notes = data.notes || [];
  const mastery = data.mastery || { score: 0, level: 'not_started', breakdown: {} };
  const breakdown = mastery.breakdown || {};
  const obsTotal = (+breakdown['未开始'] || 0) + (+breakdown['学习中'] || 0) + (+breakdown['已掌握'] || 0);
  const segs = [
    { key: '未开始', n: +breakdown['未开始'] || 0, color: 'color-mix(in srgb, var(--muted-foreground) 32%, transparent)' },
    { key: '学习中', n: +breakdown['学习中'] || 0, color: 'color-mix(in srgb, var(--primary) 45%, transparent)' },
    { key: '已掌握', n: +breakdown['已掌握'] || 0, color: 'var(--primary)' },
  ];

  return (
    <div>
      <div className="v3-hd">
        <div className="row" style={{ gap: 12, alignItems: 'flex-start', minWidth: 0 }}>
          {back}
          <div style={{ minWidth: 0 }}>
            <h1 style={{ overflowWrap: 'anywhere' }}>{esc(doc.title || '未命名资料')}</h1>
            <div className="sub">
              {doc.source_type === 'video' ? '视频' : doc.source_type === 'note' ? '笔记' : '文档'}
              {' · '}{data.chunks} 个切片{' · '}更新于 {fmtTime(doc.updated_at || doc.created_at)}
            </div>
          </div>
          <Tag color={STATUS_COLOR[doc.status] || 'default'} style={{ marginTop: 4 }}>
            {STATUS_CN[doc.status] || doc.status}
          </Tag>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <Tooltip title={ready ? '约需 10–20 秒' : '请先解析资料'}>
            <span style={{ display: 'inline-flex' }}>
              <Button icon={<FormOutlined />} loading={noteBusy} disabled={!ready || noteBusy}
                onClick={genNote}>生成笔记</Button>
            </span>
          </Tooltip>
          <Tooltip title={ready ? '按资料内容出背诵卡' : '请先解析资料'}>
            <span style={{ display: 'inline-flex' }}>
              <Button icon={<CreditCardOutlined />} loading={cardBusy} disabled={!ready || cardBusy}
                onClick={genCards}>生成卡片</Button>
            </span>
          </Tooltip>
        </div>
      </div>

      <div className="v3-grid">
        {/* ① 掌握度总览：唯一 hero */}
        <section className="v3-card v3-hero v3-c12">
          <div className="v3-sh">掌握度总览<span className="meta">{obsTotal} 个观测</span></div>
          {obsTotal > 0 ? (
            <>
              <div className="row between" style={{ alignItems: 'flex-end', gap: 24 }}>
                <div style={{ minWidth: 0 }}>
                  <div className="lab">整体掌握度</div>
                  <div className="big" style={{ fontVariantNumeric: 'tabular-nums' }}>{pct(mastery.score)}<small>%</small></div>
                  <div className="delta">{LEVEL_CN[mastery.level] || '学习中'} · 按卡片与题目掌握度均值计算</div>
                </div>
                <div style={{ flex: 1, minWidth: 220, maxWidth: 520 }}>
                  <div style={{ display: 'flex', height: 8, borderRadius: 99, overflow: 'hidden', background: 'var(--secondary)' }}>
                    {segs.map((s) => s.n > 0 && (
                      <span key={s.key} style={{ width: `${(s.n / obsTotal) * 100}%`, background: s.color }} />
                    ))}
                  </div>
                  <div className="v3-axis">
                    {segs.map((s) => <span key={s.key}>{s.key} {s.n}</span>)}
                  </div>
                </div>
              </div>
              <div className="v3-acts">
                <Button type="primary" onClick={() => navigate('/review')}>去复习</Button>
                <span className="muted" style={{ fontSize: 12.5, fontVariantNumeric: 'tabular-nums' }}>
                  {cards.due > 0 ? `${cards.due} 张到期` : '暂无到期卡片'}
                </span>
              </div>
            </>
          ) : (
            <EmptyState icon={<CreditCardOutlined />} title="还没有掌握度数据"
              desc="生成卡片或导入题目后，这里会显示学习进度" action="生成卡片" onAction={genCards} />
          )}
        </section>

        {/* ② 笔记 */}
        <section className="v3-card v3-c6">
          <div className="v3-sh">笔记<span className="meta">{notes.length} 篇</span></div>
          {notes.length > 0 ? (
            <>
              {notes.map((n) => (
                <div className="v3-resume" key={n.id}>
                  <div className="v3-rt">
                    <div className="a" style={{
                      display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                    }}>{esc(n.title || '未命名笔记')}</div>
                    <div className="b">{SOURCE_CN[n.source] || '笔记'} · {fmtTime(n.updated_at)}</div>
                  </div>
                  <Button size="small" type="link" onClick={() => navigate(`/notes?note=${n.id}`)}>打开</Button>
                </div>
              ))}
              <div style={{
                marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--border)',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8,
              }}>
                <span className="muted" style={{ fontSize: 12.5 }}>整理成可背诵的结构</span>
                <div className="row" style={{ gap: 4 }}>
                  <Button size="small" type="text" loading={noteBusy} disabled={!ready || noteBusy}
                    onClick={genNote}>再生成</Button>
                  <Button size="small" type="text" onClick={() => navigate('/notes')}>全部笔记</Button>
                </div>
              </div>
            </>
          ) : (
            <EmptyState icon={<FormOutlined />} title="还没有笔记"
              desc={ready ? '把这份资料整理成可直接背诵的笔记' : '资料解析完成后可生成笔记'}
              action="生成笔记" onAction={genNote} />
          )}
        </section>

        {/* ③ 卡片情况 */}
        <section className="v3-card v3-c6">
          <div className="v3-sh">卡片情况<span className="meta">{cards.total || 0} 张</span></div>
          {cards.total > 0 ? (
            <>
              <div className="row" style={{ gap: 32, flexWrap: 'wrap', marginBottom: 12 }}>
                {[
                  { k: '总数', v: cards.total },
                  { k: '已掌握', v: cards.mastered || 0 },
                  { k: '到期', v: cards.due || 0 },
                ].map((m) => (
                  <div key={m.k}>
                    <div className="muted" style={{ fontSize: 11.5 }}>{m.k}</div>
                    <div style={{ fontSize: 22, fontWeight: 500, lineHeight: 1.25, letterSpacing: '-.5px', fontVariantNumeric: 'tabular-nums' }}>
                      {m.v}
                    </div>
                  </div>
                ))}
                <div style={{ marginLeft: 'auto', alignSelf: 'flex-end' }}>
                  <span className="muted" style={{ fontSize: 11.5 }}>平均掌握 </span>
                  <b style={{ fontSize: 13.5, fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>{pct(cards.avg_mastery)}%</b>
                </div>
              </div>
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: 4 }}>
                {(cards.recent || []).map((c) => (
                  <div className="v3-resume" key={c.id}>
                    <div className="v3-rt">
                      <div className="a" style={{
                        display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                      }}>{esc(c.question || '未命名卡片')}</div>
                      <div className="b" style={{ fontVariantNumeric: 'tabular-nums' }}>掌握 {pct(c.mastery)}% · {dueLabel(c.due_at)}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 12, textAlign: 'right' }}>
                <Button size="small" type="link" onClick={() => navigate('/review')}>去复习</Button>
              </div>
            </>
          ) : (
            <EmptyState icon={<CreditCardOutlined />} title="还没有卡片"
              desc="按资料内容生成背诵卡，进入间隔复习" action="生成卡片" onAction={genCards} />
          )}
        </section>

        {/* ④ 题目情况 */}
        <section className="v3-card v3-c12">
          <div className="v3-sh">题目情况<span className="meta">{questions.total || 0} 道</span></div>
          {questions.total > 0 ? (
            <div className="row between" style={{ gap: 24 }}>
              <div className="row" style={{ gap: 32, flexWrap: 'wrap' }}>
                {[
                  { k: '题目', v: questions.total, unit: '道' },
                  { k: '已答', v: questions.answered || 0, unit: '道' },
                  { k: '正确率', v: questions.answered ? `${questions.accuracy}%` : '—', unit: '' },
                ].map((m) => (
                  <div key={m.k}>
                    <div className="muted" style={{ fontSize: 11.5 }}>{m.k}</div>
                    <div style={{ fontSize: 22, fontWeight: 500, lineHeight: 1.25, letterSpacing: '-.5px', fontVariantNumeric: 'tabular-nums' }}>
                      {m.v}{m.unit && <small style={{ fontSize: 11.5, fontWeight: 400, color: 'var(--muted-foreground)', marginLeft: 4 }}>{m.unit}</small>}
                    </div>
                  </div>
                ))}
              </div>
              <Button size="small" onClick={() => navigate('/study')}>去刷题</Button>
            </div>
          ) : (
            <EmptyState icon={<FileTextOutlined />} title="还没有题目"
              desc="导入题库后，这里会显示答题进度与正确率" action="去刷题" onAction={() => navigate('/study')} />
          )}
        </section>
      </div>
    </div>
  );
}
