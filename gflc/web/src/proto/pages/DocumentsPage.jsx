import React, { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  ArrowRightIcon,
  BanksIcon,
  CloseIcon,
  DocsIcon,
  NotesIcon,
  SearchIcon,
  SparkIcon,
  UploadIcon,
  VideoIcon,
} from '../NavIcons.jsx';
import { Badge, Btn, Card, Divider, Kpi, Progress, SectionTitle, cx } from '../ui.jsx';
import {
  docKinds,
  docQueue,
  docReader,
  docStats,
  docStorage,
  docSubjects,
  documents as seedDocuments,
} from '../mock/index.js';

const KIND_TONE = { 教材: 'brand', 讲义: 'neutral', 真题卷: 'ok', 视频: 'warn' };
const KIND_ICON = { 教材: DocsIcon, 讲义: NotesIcon, 真题卷: BanksIcon, 视频: VideoIcon };
const ROW_GRID = 'grid grid-cols-[18px_minmax(0,1fr)_72px_50px_80px_126px] items-center gap-2';

function Chip({ active, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        'h-7 shrink-0 rounded-[8px] px-2.5 text-[11px] transition-colors duration-200 ease-apple',
        active ? 'bg-ink text-white' : 'text-ink2 hover:bg-sel hover:text-ink',
      )}
    >
      {children}
    </button>
  );
}

/** S4 文档类来源跳转 /docs?doc=<id>&page=<n> 时打开的只读定位抽屉 */
function ReaderDrawer({ doc, page, onClose }) {
  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <button type="button" aria-label="关闭定位抽屉" onClick={onClose} className="absolute inset-0 bg-ink/20" />
      <aside className="relative flex h-full w-[420px] animate-fade-up flex-col border-l border-line bg-card shadow-pop">
        <div className="flex h-12 shrink-0 items-center gap-2 border-b border-line px-4">
          <DocsIcon size={15} className="shrink-0 text-ink3" />
          <p className="min-w-0 flex-1 truncate text-[13px] font-medium text-ink">{doc ? doc.title : '未知资料'}</p>
          <Badge tone="brand">第 {page} 页</Badge>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] text-ink3 hover:bg-sel hover:text-ink"
          >
            <CloseIcon size={14} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
          <p className="text-[11px] text-ink3">{docReader.chapter} · 原文切片（只读）</p>
          <ul className="mt-2 rounded-[10px] border border-line bg-page/60 py-1.5">
            {docReader.lines.map((l) => (
              <li
                key={l.n}
                className={cx(
                  'flex items-start gap-2 px-2.5 py-1 leading-[18px]',
                  l.hit && 'bg-brandSoft',
                )}
              >
                <span className="gf-num w-6 shrink-0 text-right text-[10px] text-ink3">{l.n}</span>
                <span className={cx('text-[12px]', l.hit ? 'text-brand' : 'text-ink2')}>{l.text}</span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] leading-[16px] text-ink3">
            来源：资料解析切片 · 该页已生成 6 张卡片、2 条笔记。定位抽屉只读，不修改任何内容。
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2 border-t border-line px-4 py-2.5">
          <Btn variant="solid" size="sm" onClick={onClose}>知道了</Btn>
          {doc ? (
            <Link
              to={`/docs/${doc.id}`}
              className="gf-btn gf-btn-line h-8 px-3 text-[12px]"
            >
              在详情中打开
              <ArrowRightIcon size={12} />
            </Link>
          ) : null}
        </div>
      </aside>
    </div>
  );
}

export default function DocumentsPage() {
  const [view, setView] = useState('list');
  const [query, setQuery] = useState('');
  const [subject, setSubject] = useState('全部');
  const [kind, setKind] = useState('全部');
  const [docs, setDocs] = useState(seedDocuments);
  const [params, setParams] = useSearchParams();

  const anchorId = params.get('doc');
  const anchorPage = params.get('page') || '1';
  const anchorDoc = useMemo(() => docs.find((d) => d.id === anchorId), [docs, anchorId]);

  const filtered = useMemo(() => {
    const q = query.trim();
    return docs.filter(
      (d) =>
        (subject === '全部' || d.subject === subject) &&
        (kind === '全部' || d.kind === kind) &&
        (!q || d.title.includes(q)),
    );
  }, [docs, query, subject, kind]);

  const closeDrawer = () => {
    const next = new URLSearchParams(params);
    next.delete('doc');
    next.delete('page');
    setParams(next, { replace: true });
  };

  const parseOne = (id) =>
    setDocs((list) =>
      list.map((d) => (d.id === id ? { ...d, status: '解析中', statusTone: 'warn', mastery: Math.min(99, d.mastery + 2) } : d)),
    );

  const removeOne = (id) => setDocs((list) => list.filter((d) => d.id !== id));

  return (
    <div className="flex animate-fade-up flex-col gap-2.5">
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex h-8 w-[220px] shrink-0 items-center gap-1.5 rounded-[10px] border border-line bg-card px-2.5">
            <SearchIcon size={13} className="shrink-0 text-ink3" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索资料名称"
              className="h-full w-full min-w-0 bg-transparent text-[12px] text-ink placeholder:text-ink3 focus:outline-none"
            />
          </div>
          <div className="flex shrink-0 items-center rounded-[10px] bg-sel p-0.5">
            {[
              ['list', '列表'],
              ['grid', '网格'],
            ].map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setView(key)}
                className={cx(
                  'h-7 rounded-[8px] px-2.5 text-[11px] transition-colors duration-200 ease-apple',
                  view === key ? 'bg-card text-ink shadow-[0_1px_2px_rgba(0,0,0,0.06)]' : 'text-ink3 hover:text-ink',
                )}
              >
                {label}
              </button>
            ))}
          </div>
          <span className="mx-1 hidden h-5 w-px shrink-0 bg-line sm:block" />
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-0.5">
            {docSubjects.map((s) => (
              <Chip key={s} active={subject === s} onClick={() => setSubject(s)}>{s}</Chip>
            ))}
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <Btn variant="line" size="sm" icon={<UploadIcon size={13} />}>导入链接</Btn>
            <Btn variant="solid" size="sm" icon={<UploadIcon size={13} />}>上传资料</Btn>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-ink3">类型</span>
          <div className="flex items-center gap-0.5">
            {docKinds.map((k) => (
              <Chip key={k} active={kind === k} onClick={() => setKind(k)}>{k}</Chip>
            ))}
          </div>
          <span className="ml-auto text-[11px] text-ink3">
            共 <span className="gf-num text-ink">{filtered.length}</span> 份 · 本周新增 {docStats.weekNew} 份 · 占用 {docStats.size}
          </span>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-12">
        <Card className="xl:col-span-8">
          <SectionTitle
            title="资料库"
            sub="教材 / 讲义 / 真题卷 / 视频转写，解析后自动生成笔记与卡片"
            action={<span className="text-[11px] text-ink3">按最近解析排序</span>}
          />
          {filtered.length === 0 ? (
            <div className="flex h-[240px] items-center justify-center text-[12px] text-ink3">没有匹配的资料，试试换个筛选条件</div>
          ) : view === 'list' ? (
            <div>
              <div className={cx(ROW_GRID, 'h-[18px] border-b border-line px-1 text-[10px] text-ink3')}>
                <span />
                <span>资料名称</span>
                <span>科目</span>
                <span className="gf-num text-right">页数</span>
                <span>掌握度</span>
                <span className="text-right">操作</span>
              </div>
              <ul>
                {filtered.map((d) => {
                  const Icon = KIND_ICON[d.kind] || DocsIcon;
                  return (
                    <li
                      key={d.id}
                      className={cx(ROW_GRID, 'h-[36px] border-b border-line px-1 transition-colors duration-200 ease-apple last:border-b-0 hover:bg-page')}
                    >
                      <span className="flex h-5 w-5 items-center justify-center rounded-[6px] bg-page text-ink2">
                        <Icon size={12} />
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-[12px] leading-[16px] text-ink">{d.title}</p>
                        <p className="truncate text-[10px] leading-[13px] text-ink3">
                          {d.kind} · {d.size} · {d.updated} · {d.cards} 卡片 / {d.questions} 题
                        </p>
                      </div>
                      <Badge tone={KIND_TONE[d.kind] || 'neutral'}>{d.subject}</Badge>
                      <span className="gf-num text-right text-[11px] text-ink2">{d.pages || '—'}</span>
                      <div className="flex items-center gap-1.5">
                        <Progress value={d.mastery} tone={d.mastery >= 70 ? 'ok' : d.mastery >= 50 ? 'brand' : 'warn'} height="h-1" className="w-[38px]" />
                        <span className="gf-num text-[11px] text-ink2">{d.mastery}%</span>
                      </div>
                      <div className="flex items-center justify-end gap-1.5 text-[10px]">
                        <Link to={`/docs/${d.id}`} className="text-ink2 hover:text-brand">详情</Link>
                        <button type="button" onClick={() => parseOne(d.id)} className="text-ink2 hover:text-ink">解析</button>
                        <Link to="/study" className="text-ink2 hover:text-ink">模拟卷</Link>
                        <button type="button" onClick={() => removeOne(d.id)} className="text-ink3 hover:text-bad">删除</button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {filtered.map((d) => {
                const Icon = KIND_ICON[d.kind] || DocsIcon;
                return (
                  <Link
                    key={d.id}
                    to={`/docs/${d.id}`}
                    className="rounded-[10px] border border-line px-2.5 py-2 transition-colors duration-200 ease-apple hover:bg-page"
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-[6px] bg-page text-ink2">
                        <Icon size={12} />
                      </span>
                      <Badge tone={KIND_TONE[d.kind] || 'neutral'}>{d.kind}</Badge>
                      <span className="gf-num ml-auto text-[10px] text-ink3">{d.mastery}%</span>
                    </div>
                    <p className="mt-1.5 truncate text-[12px] text-ink">{d.title}</p>
                    <p className="truncate text-[10px] text-ink3">{d.subject} · {d.pages || 0} 页 · {d.size}</p>
                    <Progress value={d.mastery} tone={d.mastery >= 70 ? 'ok' : 'brand'} height="h-1" className="mt-1.5" />
                  </Link>
                );
              })}
            </div>
          )}
        </Card>

        <div className="flex flex-col gap-2.5 xl:col-span-4">
          <Card>
            <SectionTitle title="解析队列" sub="后台任务，完成后自动归档" action={<Badge tone="warn" dot>3 个</Badge>} />
            <ul className="flex flex-col gap-2">
              {docQueue.map((q) => (
                <li key={q.id} className="min-w-0">
                  <div className="flex items-baseline justify-between gap-2">
                    <p className="truncate text-[12px] leading-[17px] text-ink">{q.name}</p>
                    <span className="gf-num shrink-0 text-[10px] text-ink3">{q.progress}%</span>
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <Progress value={q.progress} tone={q.tone} height="h-1" className="flex-1" />
                    <span className="shrink-0 text-[10px] text-ink3">{q.stage}</span>
                  </div>
                </li>
              ))}
            </ul>
            <Divider className="my-2.5" />
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-ink3">支持 PDF / DOCX / Markdown / 视频链接</span>
              <Btn variant="ghost" size="xs">查看任务</Btn>
            </div>
          </Card>

          <Card>
            <SectionTitle title="资料概况" sub="全部科目合计" />
            <div className="grid grid-cols-2 gap-y-3">
              <Kpi label="资料份数" value={docStats.total} unit="份" hint={`已解析 ${docStats.parsed} 份`} />
              <Kpi label="生成卡片" value={docStats.cards} unit="张" hint="含视频转写 12 张" tone="brand" />
              <Kpi label="关联题目" value={docStats.questions} unit="道" hint="题库可筛选来源" />
              <Kpi label="存储占用" value={docStats.size} hint="本地磁盘，不上传云端" />
            </div>
          </Card>

          <Card>
            <SectionTitle
              title="存储占用"
              sub="按资料类型分布"
              action={<Badge tone="warn">{docStorage.usedPercent}% 已用</Badge>}
            />
            <div className="flex h-2 w-full overflow-hidden rounded-full bg-sel">
              {docStorage.items.map((it) => (
                <div
                  key={it.key}
                  title={`${it.label} · ${it.value}`}
                  className={cx(
                    'h-full',
                    it.tone === 'brand' && 'bg-brand',
                    it.tone === 'warn' && 'bg-warn',
                    it.tone === 'ok' && 'bg-ok',
                    it.tone === 'ink' && 'bg-ink',
                  )}
                  style={{ width: `${it.pct}%` }}
                />
              ))}
            </div>
            <div className="mt-2 flex flex-col gap-1.5">
              {docStorage.items.map((it) => (
                <div key={it.key} className="flex items-center gap-2 text-[11px]">
                  <span
                    className={cx(
                      'h-2 w-2 shrink-0 rounded-[3px]',
                      it.tone === 'brand' && 'bg-brand',
                      it.tone === 'warn' && 'bg-warn',
                      it.tone === 'ok' && 'bg-ok',
                      it.tone === 'ink' && 'bg-ink',
                    )}
                  />
                  <span className="w-[52px] shrink-0 text-ink2">{it.label}</span>
                  <span className="gf-num ml-auto text-ink3">{it.value}</span>
                </div>
              ))}
            </div>
            <div className="mt-2.5 flex items-center justify-between border-t border-line pt-2 text-[11px]">
              <span className="text-ink3">已用 <span className="gf-num text-ink">{docStorage.used}</span> / {docStorage.total}</span>
              <span className="text-ink3">剩余 <span className="gf-num text-ink">18.6 GB</span></span>
            </div>
          </Card>

          <Card>
            <SectionTitle title="快捷操作" sub="批量处理当前资料库" />
            <div className="grid grid-cols-1 gap-1.5">
              <Btn variant="line" size="sm" className="justify-center" icon={<SparkIcon size={13} />}>
                批量生成卡片
              </Btn>
              <Btn variant="line" size="sm" className="justify-center" icon={<SparkIcon size={13} />}>
                AI 整理笔记
              </Btn>
              <Btn variant="line" size="sm" className="justify-center" icon={<UploadIcon size={13} />}>
                导出资料清单
              </Btn>
            </div>
          </Card>
        </div>
      </div>

      {anchorDoc ? <ReaderDrawer doc={anchorDoc} page={anchorPage} onClose={closeDrawer} /> : null}
    </div>
  );
}
