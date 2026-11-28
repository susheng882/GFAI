import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRightIcon,
  BanksIcon,
  ChevronDownIcon,
  PlayIcon,
  PlusIcon,
  SearchIcon,
  UploadIcon,
} from '../NavIcons.jsx';
import { Badge, Btn, Card, Divider, Kpi, MeterRow, Progress, SectionTitle, cx } from '../ui.jsx';
import { bankOverview, bankQueue, bankStats, bankTree, questionBanks } from '../mock/index.js';

const KIND_TONE = { 真题: 'brand', 模拟: 'warn', 章节: 'neutral', 错题: 'bad' };
const ROW_GRID =
  'grid grid-cols-[minmax(0,1fr)_74px_44px_48px_44px_88px_64px_56px] items-center gap-2';

function TreeGroup({ title, group, items, active, onPick }) {
  return (
    <div>
      <p className="px-1.5 text-[10px] leading-[16px] text-ink3">{title}</p>
      <ul className="flex flex-col gap-0.5">
        {items.map((it) => (
          <li key={it.id}>
            <button
              type="button"
              onClick={() => onPick({ group, name: it.name })}
              className={cx(
                'flex h-6 w-full items-center gap-1 rounded-[7px] pl-1.5 pr-1.5 text-left transition-colors duration-200 ease-apple',
                active.group === group && active.name === it.name ? 'bg-sel' : 'hover:bg-page',
              )}
            >
              <span
                className={cx(
                  'min-w-0 flex-1 truncate text-[12px]',
                  active.group === group && active.name === it.name ? 'text-ink' : 'text-ink2',
                )}
              >
                {it.name}
              </span>
              <span className="gf-num shrink-0 text-[10px] text-ink3">{it.count}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function QuestionBanksPage() {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState({ group: 'all', name: '全部题库' });
  const [bankList, setBankList] = useState(questionBanks);
  const [page, setPage] = useState(1);
  const pageSize = 6;

  const list = useMemo(() => {
    const q = query.trim();
    return bankList.filter((b) => {
      if (q && !b.name.includes(q)) return false;
      if (active.group === 'subject') return b.subject === active.name;
      if (active.group === 'year') {
        return active.name === '更早年份' ? Number(b.year) < 2024 : b.year === active.name;
      }
      if (active.group === 'kind') return b.kind === active.name;
      return true;
    });
  }, [bankList, query, active]);

  const totalPages = Math.max(1, Math.ceil(list.length / pageSize));
  const pageList = list.slice((page - 1) * pageSize, page * pageSize);

  const moved = (id) =>
    setBankList((prev) => prev.map((b) => (b.id === id ? { ...b, kind: b.kind === '错题' ? '真题' : '错题' } : b)));

  return (
    <div className="flex animate-fade-up flex-col gap-2.5">
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex h-8 w-[220px] shrink-0 items-center gap-1.5 rounded-[10px] border border-line bg-card px-2.5">
            <SearchIcon size={13} className="shrink-0 text-ink3" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索题库 / 试卷名"
              className="h-full w-full min-w-0 bg-transparent text-[12px] text-ink placeholder:text-ink3 focus:outline-none"
            />
          </div>
          <button
            type="button"
            onClick={() => setActive({ group: 'all', name: '全部题库' })}
            className={cx(
              'h-7 shrink-0 rounded-[8px] px-2.5 text-[11px] transition-colors duration-200 ease-apple',
              active.group === 'all' ? 'bg-ink text-white' : 'text-ink2 hover:bg-sel hover:text-ink',
            )}
          >
            全部题库
          </button>
          <span className="text-[11px] text-ink3">独立入口，与「资料（教材解析）」分开管理</span>
          <div className="ml-auto flex shrink-0 items-center gap-1.5">
            <Btn variant="line" size="sm" icon={<PlusIcon size={13} />}>新建文件夹</Btn>
            <Btn variant="solid" size="sm" icon={<UploadIcon size={13} />}>导入 PDF 建库</Btn>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-ink3">
          <span>题库 <span className="gf-num text-ink">{bankStats.banks}</span> 个</span>
          <span>题目 <span className="gf-num text-ink">{bankStats.total}</span> 道</span>
          <span>平均正确率 <span className="gf-num text-ink">{bankStats.accuracy}%</span></span>
          <span>本周新建 <span className="gf-num text-ink">{bankStats.weekNew}</span> 个</span>
          <span className="ml-auto">已从 PDF 导入 {bankStats.importedPdf} 份 · 支持拖拽归类</span>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-12">
        <Card className="xl:col-span-3">
          <SectionTitle title="题库文件夹" sub="学科 / 年份 / 类型" action={<Badge tone="line">{bankStats.folders}</Badge>} />
          <div className="flex flex-col gap-2">
            <TreeGroup title="按学科" group="subject" items={bankTree.subjects} active={active} onPick={setActive} />
            <Divider />
            <TreeGroup title="按年份" group="year" items={bankTree.years} active={active} onPick={setActive} />
            <Divider />
            <TreeGroup title="按类型" group="kind" items={bankTree.kinds} active={active} onPick={setActive} />
          </div>
          <Divider className="my-2" />
          <button
            type="button"
            className="flex h-6 w-full items-center gap-1.5 rounded-[7px] px-1.5 text-[11px] text-ink3 hover:bg-page hover:text-ink"
          >
            <PlusIcon size={12} />
            新建文件夹
          </button>

          <Divider className="my-2.5" />
          <SectionTitle
            title="解析队列"
            sub={`处理中 ${bankQueue.processing} · 排队 ${bankQueue.queued}`}
            action={<Badge tone="warn" dot>{bankQueue.processing + bankQueue.queued}</Badge>}
          />
          <div className="flex flex-col gap-2">
            {bankQueue.items.map((it) => (
              <div key={it.id} className="rounded-[10px] bg-page px-2.5 py-2">
                <div className="flex items-center gap-2">
                  <span className="min-w-0 flex-1 truncate text-[11px] leading-[16px] text-ink">{it.name}</span>
                  <Badge tone={it.tone === 'ink' ? 'neutral' : it.tone}>{it.stage}</Badge>
                </div>
                <div className="mt-1.5 flex items-center gap-2">
                  <Progress value={it.progress} tone={it.tone} height="h-1" className="flex-1" />
                  <span className="gf-num shrink-0 text-[10px] text-ink3">{it.progress}%</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <div className="flex flex-col gap-2.5 xl:col-span-9">
          <Card>
            <SectionTitle title="题库概览" sub="题库总量、解析进度与学科分布" action={<Badge tone="line">实时</Badge>} />
            <div className="grid grid-cols-2 gap-x-6 gap-y-3 lg:grid-cols-4">
              <Kpi label="题库数" value={bankOverview.banks} unit="个" hint="含真题 / 模拟 / 章节" tone="ink" />
              <Kpi label="题目总量" value={bankOverview.questions} unit="道" hint="全部题库合计" tone="brand" />
              <Kpi label="已解析" value={bankOverview.parsed} unit="个" hint="待校对 2 个" tone="ok" />
              <Kpi label="平均正确率" value={`${bankOverview.accuracy}%`} hint="近 7 天练习" tone="warn" />
            </div>
            <Divider className="my-2.5" />
            <div className="flex flex-col gap-1.5">
              {bankOverview.dist.map((d) => (
                <MeterRow key={d.label} label={d.label} value={d.value} total={bankOverview.banks} tone={d.tone} suffix={`${d.value} 个`} />
              ))}
            </div>
          </Card>

          <Card>
            <SectionTitle
              title={active.group === 'all' ? '全部题库' : active.name}
              sub="点击练习进入答题，箭头用于改归类"
              action={<Badge tone="brand" dot>{list.length} 个题库</Badge>}
            />
            <div className={cx(ROW_GRID, 'border-b border-line pb-1 text-[10px] text-ink3')}>
              <span>题库名称</span>
              <span>学科</span>
              <span>年份</span>
              <span>类型</span>
              <span className="gf-num text-right">题量</span>
              <span>正确率</span>
              <span>最近练习</span>
              <span className="text-right">操作</span>
            </div>
            <ul>
              {pageList.map((b) => (
                <li
                  key={b.id}
                  className={cx(ROW_GRID, 'h-[36px] border-b border-line transition-colors duration-200 ease-apple last:border-b-0 hover:bg-page')}
                >
                  <div className="flex min-w-0 items-center gap-1.5">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-[6px] bg-page text-ink2">
                      <BanksIcon size={12} />
                    </span>
                    <span className="truncate text-[12px] leading-[17px] text-ink">{b.name}</span>
                    {b.due ? <Badge tone="warn">{b.due} 待练</Badge> : null}
                  </div>
                  <Badge tone="neutral">{b.subject}</Badge>
                  <span className="gf-num text-[11px] text-ink2">{b.year}</span>
                  <Badge tone={KIND_TONE[b.kind] || 'neutral'}>{b.kind}</Badge>
                  <span className="gf-num text-right text-[11px] text-ink2">{b.questions}</span>
                  <div className="flex items-center gap-1.5">
                    <Progress
                      value={b.accuracy}
                      tone={b.accuracy >= 70 ? 'ok' : b.accuracy >= 60 ? 'brand' : 'warn'}
                      height="h-1"
                      className="w-[40px]"
                    />
                    <span className="gf-num text-[11px] text-ink2">{b.accuracy}%</span>
                  </div>
                  <span className="truncate text-[10px] text-ink3">{b.last}</span>
                  <div className="flex items-center justify-end gap-1.5">
                    <Link to="/study" className="flex items-center gap-0.5 text-[10px] text-ink2 hover:text-brand">
                      <PlayIcon size={10} />
                      练习
                    </Link>
                    <button
                      type="button"
                      onClick={() => moved(b.id)}
                      aria-label="改归类"
                      className="text-ink3 hover:text-ink"
                      title="改归类"
                    >
                      <ArrowRightIcon size={11} />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            {list.length === 0 ? (
              <p className="py-6 text-center text-[12px] text-ink3">没有匹配的题库，试试换个关键词</p>
            ) : null}
            <div className="mt-2 flex items-center justify-between border-t border-line pt-2">
              <span className="text-[11px] text-ink3">
                共 <span className="gf-num text-ink">{list.length}</span> 个题库 · 第 <span className="gf-num text-ink">{page}</span> / {totalPages} 页
              </span>
              <div className="flex items-center gap-1.5">
                <Btn variant="line" size="xs" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                  上一页
                </Btn>
                <Btn variant="line" size="xs" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>
                  下一页
                </Btn>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex flex-wrap items-center gap-4">
              <Kpi label="题目总量" value={bankStats.total} unit="道" hint="含真题与章节题" tone="ink" />
              <span className="h-8 w-px bg-line" />
              <Kpi label="平均正确率" value={`${bankStats.accuracy}%`} hint="近 7 天练习" tone="brand" />
              <span className="h-8 w-px bg-line" />
              <Kpi label="待练题目" value={list.reduce((s, b) => s + b.due, 0)} unit="道" hint="含 3 道错题重练" tone="warn" />
              <span className="h-8 w-px bg-line" />
              <div className="min-w-0 flex-1">
                <p className="text-[11px] text-ink3">题库与资料的关系</p>
                <p className="mt-1 text-[11px] leading-[16px] text-ink2">
                  题库独立于「资料」模块：资料负责解析教材生成笔记与卡片，题库负责组卷与错题重练，两者通过「来源资料」双向关联。
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <Link to="/docs" className="flex items-center gap-1 text-[11px] text-ink2 hover:text-ink">
                  去资料库
                  <ChevronDownIcon size={11} className="-rotate-90" />
                </Link>
                <Btn variant="ghost" size="xs">批量归类</Btn>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
