import React, { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowRightIcon,
  BanksIcon,
  CheckIcon,
  CloseIcon,
  DeckIcon,
  DocsIcon,
  NotesIcon,
  SparkIcon,
} from '../NavIcons.jsx';
import { Badge, Btn, Card, Divider, Kpi, Progress, SectionTitle, cx } from '../ui.jsx';
import { documentDetail } from '../mock/index.js';

function Ring({ value, size = 92 }) {
  const r = size / 2 - 7;
  const c = 2 * Math.PI * r;
  const dash = (c * value) / 100;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0" aria-hidden="true">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#EFEFF2" strokeWidth="8" />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="#0071E3"
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={`${dash} ${c - dash}`}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text x="50%" y="48%" textAnchor="middle" dominantBaseline="central" fontSize="19" fontWeight="500" fill="#1D1D1F">
        {value}%
      </text>
      <text x="50%" y="69%" textAnchor="middle" dominantBaseline="central" fontSize="10" fill="#86868B">
        总掌握度
      </text>
    </svg>
  );
}

function ReconcileModal({ mastery, onClose, onConfirm }) {
  const { reconcile } = documentDetail;
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center px-6">
      <button type="button" aria-label="关闭预览" onClick={onClose} className="absolute inset-0 bg-ink/20" />
      <div className="relative w-[520px] animate-fade-up overflow-hidden rounded-[16px] border border-line bg-card shadow-pop">
        <div className="flex h-12 items-center gap-2 border-b border-line px-4">
          <SparkIcon size={15} className="shrink-0 text-brand" />
          <p className="min-w-0 flex-1 truncate text-[13px] font-medium text-ink">掌握度对齐 · 只读预览</p>
          <Badge tone="line">{reconcile.source}</Badge>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] text-ink3 hover:bg-sel hover:text-ink"
          >
            <CloseIcon size={14} />
          </button>
        </div>
        <div className="px-4 py-3">
          <p className="text-[11px] leading-[16px] text-ink3">{reconcile.desc}</p>
          <div className="mt-2 overflow-hidden rounded-[10px] border border-line">
            <div className="grid grid-cols-[minmax(0,1fr)_64px_64px_56px] gap-2 border-b border-line bg-page px-2.5 py-1.5 text-[10px] text-ink3">
              <span>章节</span>
              <span className="gf-num text-right">当前</span>
              <span className="gf-num text-right">对齐后</span>
              <span className="gf-num text-right">变化</span>
            </div>
            {reconcile.items.map((it) => {
              const delta = it.after - it.before;
              return (
                <div
                  key={it.label}
                  className="grid grid-cols-[minmax(0,1fr)_64px_64px_56px] items-center gap-2 border-b border-line px-2.5 py-1.5 last:border-b-0"
                >
                  <span className="truncate text-[12px] text-ink">{it.label}</span>
                  <span className="gf-num text-right text-[11px] text-ink3">{it.before}%</span>
                  <span className="gf-num text-right text-[11px] text-ink">{it.after}%</span>
                  <span
                    className={cx(
                      'gf-num text-right text-[11px]',
                      delta > 0 ? 'text-[#248A3D]' : delta < 0 ? 'text-[#C4322B]' : 'text-ink3',
                    )}
                  >
                    {delta > 0 ? `+${delta}` : delta}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="mt-2 text-[11px] leading-[16px] text-ink3">
            总掌握度 {mastery}% → <span className="text-ink">{reconcile.after}%</span>；笔记 {documentDetail.notes.length} 条、卡片{' '}
            {documentDetail.cards} 张、题目 {documentDetail.questions} 道均不受影响。
          </p>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-line px-4 py-2.5">
          <Btn variant="line" size="sm" onClick={onClose}>取消</Btn>
          <Btn variant="solid" size="sm" icon={<CheckIcon size={13} />} onClick={onConfirm}>确认对齐</Btn>
        </div>
      </div>
    </div>
  );
}

export default function DocumentDetailPage() {
  const { id } = useParams();
  const d = documentDetail;
  const [mastery, setMastery] = useState(d.mastery);
  const [aligned, setAligned] = useState(false);
  const [preview, setPreview] = useState(false);

  const confirmAlign = () => {
    setMastery(d.reconcile.after);
    setAligned(true);
    setPreview(false);
  };

  return (
    <div className="flex animate-fade-up flex-col gap-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <Link to="/docs" className="text-[11px] text-ink3 hover:text-ink">资料</Link>
        <span className="text-[11px] text-ink3">/</span>
        <h2 className="min-w-0 truncate text-[14px] font-medium text-ink">{d.title}</h2>
        <Badge tone="brand">{d.subject}</Badge>
        <Badge tone="ok" dot>已解析</Badge>
        <span className="text-[11px] text-ink3">{d.pages} 页 · {d.size} · 解析于 {d.parsedAt}</span>
        <div className="ml-auto flex shrink-0 items-center gap-1.5">
          <Btn variant="line" size="sm" icon={<NotesIcon size={13} />}>生成笔记</Btn>
          <Btn variant="solid" size="sm" icon={<SparkIcon size={13} />} onClick={() => setPreview(true)}>
            掌握度对齐
          </Btn>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-12">
        <Card className="xl:col-span-5">
          <SectionTitle title="掌握度总览" sub={`已掌握 ${d.masteredPages} / ${d.pages} 页`} action={aligned ? <Badge tone="ok" dot>已对齐</Badge> : <Badge tone="line">{id === d.id ? '最近解析' : 'v8 解析'}</Badge>} />
          <div className="flex items-center gap-4">
            <Ring value={mastery} />
            <div className="grid min-w-0 flex-1 grid-cols-2 gap-y-2.5">
              <Kpi label="关联笔记" value={d.notes.length} unit="条" hint="含 12 处双链" />
              <Kpi label="卡片" value={d.cards} unit="张" hint={`今日到期 ${d.dueCards} 张`} tone="brand" />
              <Kpi label="题目" value={d.questions} unit="道" hint={`正确率 ${d.accuracy}%`} tone="ok" />
              <Kpi label="薄弱章节" value="3" unit="个" hint="掌握度 < 65%" tone="warn" />
            </div>
          </div>
        </Card>

        <Card className="xl:col-span-7">
          <SectionTitle title="章节掌握度明细" sub="按解析切片聚合，低于 65% 标记为薄弱" action={<Link to="/review" className="text-[11px] text-ink3 hover:text-ink">去复习</Link>} />
          <div className="grid grid-cols-[minmax(0,1fr)_52px_88px_96px] gap-2 border-b border-line pb-1 text-[10px] text-ink3">
            <span>章节</span>
            <span className="gf-num text-right">页数</span>
            <span>掌握度</span>
            <span className="text-right">卡片 / 题目</span>
          </div>
          <ul>
            {d.chapters.map((c) => (
              <li
                key={c.id}
                className="grid h-[34px] grid-cols-[minmax(0,1fr)_52px_88px_96px] items-center gap-2 border-b border-line last:border-b-0"
              >
                <span className="truncate text-[12px] text-ink">{c.name}</span>
                <span className="gf-num text-right text-[11px] text-ink3">{c.pages}</span>
                <div className="flex items-center gap-1.5">
                  <Progress value={c.mastery} tone={c.mastery >= 75 ? 'ok' : c.mastery >= 65 ? 'brand' : 'warn'} height="h-1" className="w-[46px]" />
                  <span className="gf-num text-[11px] text-ink2">{c.mastery}%</span>
                </div>
                <span className="gf-num text-right text-[11px] text-ink3">{c.cards} / {c.questions}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-12">
        <Card className="xl:col-span-5">
          <SectionTitle title="笔记" sub="解析时自动归档到本章节" action={<Link to="/notes" className="text-[11px] text-ink3 hover:text-ink">全部笔记</Link>} />
          <ul>
            {d.notes.map((n) => (
              <li key={n.id} className="border-b border-line py-1.5 last:border-b-0">
                <Link to="/notes" className="flex items-center gap-2 rounded-[8px] px-1 transition-colors duration-200 ease-apple hover:bg-page">
                  <NotesIcon size={12} className="shrink-0 text-ink3" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[12px] leading-[16px] text-ink">{n.title}</p>
                    <p className="truncate text-[10px] leading-[14px] text-ink3">{n.excerpt}</p>
                  </div>
                  <span className="shrink-0 text-[10px] text-ink3">{n.links} 双链</span>
                  <span className="shrink-0 text-[10px] text-ink3">{n.time}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="xl:col-span-3">
          <SectionTitle title="卡片情况" sub={`共 ${d.cards} 张`} action={<Badge tone="warn" dot>{d.dueCards} 到期</Badge>} />
          <ul className="flex flex-col gap-2">
            {d.deckGroups.map((g) => (
              <li key={g.label} className="min-w-0">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-[12px] text-ink">{g.label}</span>
                  <span className="gf-num shrink-0 text-[10px] text-ink3">{g.cards} 张</span>
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <Progress value={g.mastery} tone={g.mastery >= 70 ? 'ok' : 'brand'} height="h-1" className="flex-1" />
                  <span className="gf-num w-[34px] shrink-0 text-right text-[10px] text-ink3">{g.due ? `到期 ${g.due}` : '无到期'}</span>
                </div>
              </li>
            ))}
          </ul>
          <Divider className="my-2.5" />
          <Link to="/deck" className="flex items-center justify-between text-[11px] text-ink2 hover:text-ink">
            <span className="flex items-center gap-1.5"><DeckIcon size={12} />打开卡包</span>
            <ArrowRightIcon size={12} />
          </Link>
        </Card>

        <Card className="xl:col-span-4">
          <SectionTitle title="题目情况" sub={`来自本资料 ${d.questions} 道`} action={<Badge tone="ok">正确率 {d.accuracy}%</Badge>} />
          <ul className="flex flex-col gap-1.5">
            {d.questionTypes.map((q) => (
              <li key={q.label} className="flex items-center gap-2">
                <span className="w-[76px] shrink-0 truncate text-[12px] text-ink2">{q.label}</span>
                <Progress value={q.accuracy} tone={q.accuracy >= 70 ? 'ok' : q.accuracy >= 60 ? 'brand' : 'warn'} height="h-1" className="flex-1" />
                <span className="gf-num w-[34px] shrink-0 text-right text-[11px] text-ink2">{q.accuracy}%</span>
                <span className="gf-num w-[46px] shrink-0 text-right text-[10px] text-ink3">{q.total} 道</span>
              </li>
            ))}
          </ul>
          <Divider className="my-2.5" />
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-[11px] text-ink3"><BanksIcon size={12} />错题已同步到题库</span>
            <Link to="/banks" className="text-[11px] text-ink2 hover:text-ink">去刷题</Link>
          </div>
        </Card>
      </div>

      <Card pad={false}>
        <div className="flex flex-wrap items-center gap-2 px-4 py-2.5">
          <DocsIcon size={13} className="shrink-0 text-ink3" />
          <p className="min-w-0 flex-1 truncate text-[11px] text-ink3">
            掌握度对齐来源：GFLC 解析 v8 章节权重模型 · 只读预览确认后仅回写掌握度，笔记 / 卡片 / 题目不受影响
          </p>
          <Btn variant="ghost" size="xs" onClick={() => setPreview(true)}>查看影响</Btn>
        </div>
      </Card>

      {preview ? <ReconcileModal mastery={mastery} onClose={() => setPreview(false)} onConfirm={confirmAlign} /> : null}
    </div>
  );
}
