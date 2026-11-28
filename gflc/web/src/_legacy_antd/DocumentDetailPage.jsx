import React, { useCallback, useEffect, useState } from 'react';
import { App as AntdApp, Button, Drawer, Skeleton, Tag, Tooltip } from 'antd';
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
const SIDE_CN = { card: '卡片', question: '题目' };
const DIRECTION_CN = { card_from_question: '以题目为准', question_from_card: '以卡片为准' };

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
  // 掌握度画像：章节分布 + 两套掌握度的差异（全部来自只读聚合接口）
  const [chapterRows, setChapterRows] = useState([]);
  const [divergence, setDivergence] = useState([]);
  const [divTotal, setDivTotal] = useState(0);
  const [alignOpen, setAlignOpen] = useState(false);
  const [preview, setPreview] = useState(null);
  const [alignBusy, setAlignBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [overview, insight] = await Promise.all([
        api(`/documents/${id}/overview`),
        // 画像失败不影响主页面：章节分布与差异榜降级为隐藏
        api(`/mastery/insight?document_id=${id}`).catch(() => null),
      ]);
      setData(overview);
      setChapterRows(insight?.by_chapter || []);
      setDivergence(insight?.divergence || []);
      setDivTotal(insight?.divergence_total || 0);
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

  // 对齐工具：先 preview（只读）看影响清单，再 reconcile（只写 mastery）
  const openAlign = () => {
    setPreview(null);
    setAlignOpen(true);
  };

  const closeAlign = () => {
    setAlignOpen(false);
    setPreview(null);
  };

  const previewAlign = async (chapter, direction) => {
    if (alignBusy) return;
    setAlignBusy(true);
    setPreview(null);
    try {
      const qs = new URLSearchParams({ chapter, direction, document_id: String(id) });
      setPreview(await api(`/mastery/reconcile/preview?${qs.toString()}`));
    } catch (e) {
      message.error(e.message || '预览失败');
    } finally {
      setAlignBusy(false);
    }
  };

  const applyAlign = async () => {
    if (!preview || alignBusy) return;
    setAlignBusy(true);
    try {
      const res = await api('/mastery/reconcile', {
        method: 'POST',
        body: JSON.stringify({
          chapter: preview.chapter,
          direction: preview.direction,
          document_id: Number(id),
        }),
      });
      message.success(`已对齐 ${res.updated} 处`);
      setPreview(null);
      await load();
    } catch (e) {
      message.error(e.message || '对齐失败');
    } finally {
      setAlignBusy(false);
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
              <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                <div className="row between" style={{ gap: 8, marginBottom: 12 }}>
                  <span style={{ fontSize: 12.5, color: 'var(--fg-2)' }}>按章节分布</span>
                  <span className="muted" style={{ fontSize: 11.5 }}>加权掌握 · 卡 / 题</span>
                </div>
                {chapterRows.length > 0 ? (
                  chapterRows.slice(0, 8).map((c) => (
                    <div key={c.chapter} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8, minWidth: 0 }}>
                      <span title={c.chapter} style={{
                        flex: '0 0 84px', fontSize: 11.5, color: 'var(--fg-2)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>{c.chapter}</span>
                      <span style={{
                        flex: 1, minWidth: 0, height: 8, borderRadius: 99,
                        background: 'var(--secondary)', overflow: 'hidden',
                      }}>
                        <span style={{
                          display: 'block', height: '100%', borderRadius: 99,
                          width: `${Math.max(2, pct(c.score))}%`,
                          background: 'color-mix(in srgb, var(--primary) 45%, transparent)',
                        }} />
                      </span>
                      <span className="muted" style={{
                        flex: '0 0 auto', fontSize: 11.5, whiteSpace: 'nowrap',
                        fontVariantNumeric: 'tabular-nums',
                      }}>{pct(c.score)}% · 卡 {c.cards} · 题 {c.questions}</span>
                    </div>
                  ))
                ) : (
                  <div className="muted" style={{ fontSize: 12.5 }}>该资料题目未标注章节</div>
                )}
              </div>
              <div className="v3-acts">
                <Button type="primary" onClick={() => navigate('/review')}>去复习</Button>
                <span className="muted" style={{ fontSize: 12.5, fontVariantNumeric: 'tabular-nums' }}>
                  {cards.due > 0 ? `${cards.due} 张到期` : '暂无到期卡片'}
                </span>
              </div>
              {divTotal > 0 && (
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                  <Button type="link" size="small" style={{ paddingLeft: 0 }} onClick={openAlign}>
                    卡片与题目掌握度差异 {divTotal} 处
                  </Button>
                </div>
              )}
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

      {/* 掌握度对齐：preview 只读看影响 → 确认后 reconcile（只改 mastery） */}
      <Drawer title="掌握度对齐" width="min(480px, 100vw)" open={alignOpen} onClose={closeAlign}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.7 }}>
            同一章节下，卡片与题目给出了不同结论。选一侧为准，把它的均值写到另一侧，只改掌握度，不动复习排期。
          </div>

          {divergence.length === 0 ? (
            <div className="muted" style={{ fontSize: 12.5 }}>当前没有需要对齐的章节</div>
          ) : divergence.map((d) => (
            <div key={d.chapter} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 16 }}>
              <div className="row between" style={{ gap: 12, alignItems: 'baseline' }}>
                <div title={d.chapter} style={{
                  minWidth: 0, fontSize: 13.5, fontWeight: 500,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>{d.chapter}</div>
                <div className="muted" style={{
                  flex: '0 0 auto', fontSize: 11.5, whiteSpace: 'nowrap',
                  fontVariantNumeric: 'tabular-nums',
                }}>差距 {Math.round(d.gap * 100)} 个百分点</div>
              </div>
              <div className="row" style={{
                gap: 16, marginTop: 8, fontSize: 12.5, color: 'var(--fg-2)',
                fontVariantNumeric: 'tabular-nums',
              }}>
                <span>卡片 {pct(d.card_score)}%</span>
                <span>题目 {pct(d.question_score)}%</span>
              </div>
              <div className="row" style={{ gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
                <Button size="small" disabled={alignBusy}
                  onClick={() => previewAlign(d.chapter, 'card_from_question')}>以卡片为准</Button>
                <Button size="small" disabled={alignBusy}
                  onClick={() => previewAlign(d.chapter, 'question_from_card')}>以题目为准</Button>
              </div>

              {preview && preview.chapter === d.chapter && (
                <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                  <div style={{ fontSize: 12.5, color: 'var(--fg-2)', lineHeight: 1.7 }}>
                    {DIRECTION_CN[preview.direction] || '对齐'}：把{SIDE_CN[preview.source.side]}均值{' '}
                    <b style={{ fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>{pct(preview.source.score)}%</b>
                    {' '}写入 {preview.target.count} {SIDE_CN[preview.target.side]}
                  </div>
                  <div style={{ maxHeight: 160, overflowY: 'auto', marginTop: 8 }}>
                    {(preview.items || []).map((it) => (
                      <div key={it.id} className="row between" style={{
                        gap: 8, padding: '8px 0', borderBottom: '1px solid var(--border)',
                        fontSize: 11.5,
                      }}>
                        <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {esc(it.title || '未命名')}
                        </span>
                        <span className="muted" style={{
                          flex: '0 0 auto', whiteSpace: 'nowrap',
                          fontVariantNumeric: 'tabular-nums',
                        }}>{pct(it.before)}% → {pct(it.after)}%</span>
                      </div>
                    ))}
                  </div>
                  {preview.items_total > (preview.items || []).length && (
                    <div className="muted" style={{ fontSize: 11.5, marginTop: 4 }}>
                      另有 {preview.items_total - (preview.items || []).length} 条未展示
                    </div>
                  )}
                  <div className="row" style={{ gap: 8, marginTop: 12, justifyContent: 'flex-end' }}>
                    <Button size="small" type="text" disabled={alignBusy}
                      onClick={() => setPreview(null)}>取消</Button>
                    <Button size="small" type="primary" loading={alignBusy} onClick={applyAlign}>确认对齐</Button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </Drawer>
    </div>
  );
}
