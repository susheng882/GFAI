import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRightIcon,
  ChevronDownIcon,
  CloseIcon,
  NotesIcon,
  PlusIcon,
  SearchIcon,
  SparkIcon,
} from '../NavIcons.jsx';
import { Badge, Btn, Card, Divider, Kpi, MeterRow, SectionTitle, cx } from '../ui.jsx';
import { noteFolders, noteList, noteOpen, noteStats, notesRecent } from '../mock/index.js';

/** 把 [[双链]] 渲染为可高亮的胶囊，双链高亮开关关闭时只显示文字 */
function RichText({ text, highlight }) {
  const parts = String(text).split(/(\[\[[^\]]+\]\])/g);
  return parts.map((part, i) => {
    if (part.startsWith('[[') && part.endsWith(']]')) {
      const label = part.slice(2, -2);
      return (
        <span
          key={i}
          className={highlight ? 'rounded-[4px] bg-brandSoft px-0.5 text-brand' : 'text-ink underline decoration-line2 underline-offset-2'}
        >
          {label}
        </span>
      );
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}


/* AI 整理抽屉：mock 建议列表，可一键应用 */
function AiTidyDrawer({ open, onClose, onApply }) {
  const [suggestions, setSuggestions] = useState([
    { id: 1, from: '数据结构', to: '计算机基础', note: '《红黑树笔记》', reason: '内容属于基础章节' },
    { id: 2, from: '操作系统', to: '进程与调度', note: '《死锁条件》', reason: '与进程调度主题一致' },
    { id: 3, from: '未分类', to: '数学一', note: '《极限计算要点》', reason: '检测到数学公式内容' },
  ]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-ink/30" onClick={onClose} />
      <aside className="absolute right-0 top-0 flex h-full w-[360px] animate-slide-in flex-col bg-card shadow-pop">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <div>
            <p className="text-[13px] font-medium text-ink">AI 整理建议</p>
            <p className="text-[10px] text-ink3">根据内容与双链关系自动归类</p>
          </div>
          <button type="button" onClick={onClose} className="flex h-6 w-6 items-center justify-center rounded-[6px] text-ink3 hover:bg-page">
            <CloseIcon size={13} />
          </button>
        </div>
        <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto p-3">
          {suggestions.map((sg) => (
            <div key={sg.id} className="rounded-[10px] border border-line bg-page p-2.5">
              <div className="flex items-center gap-1.5 text-[11px]">
                <SparkIcon size={12} className="shrink-0 text-brand" />
                <span className="min-w-0 flex-1 truncate font-medium text-ink">{sg.note}</span>
                <Badge tone="brand">移动</Badge>
              </div>
              <p className="mt-1.5 text-[11px] leading-[16px] text-ink2">
                {sg.from} <ArrowRightIcon size={11} className="mx-0.5 inline-block" /> {sg.to}
              </p>
              <p className="mt-0.5 text-[10px] leading-[14px] text-ink3">{sg.reason}</p>
              <button
                type="button"
                onClick={() => {
                  setSuggestions((arr) => arr.filter((x) => x.id !== sg.id));
                  onApply?.(sg);
                }}
                className="mt-2 h-6 w-full rounded-[6px] bg-brand text-[11px] font-medium text-white transition-colors duration-150 ease-apple hover:bg-brand/90"
              >
                应用
              </button>
            </div>
          ))}
          {suggestions.length === 0 && (
            <div className="flex flex-1 flex-col items-center justify-center gap-1 py-10 text-center">
              <SparkIcon size={16} className="text-ink3" />
              <p className="text-[11px] text-ink3">整理完成，笔记已全部归类</p>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}

function FolderTree({ active, onPickNote, activeNote, folders, notes }) {
  const [open, setOpen] = useState(() => new Set(folders.map((f) => f.id)));
  const toggle = (id) => {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };
  return (
    <>
      <SectionTitle title="文件树" sub="文件夹与笔记统一浏览" action={<Badge tone="line">{folders.length} 夹</Badge>} />
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <ul className="flex flex-col gap-0.5">
          {folders.map((f) => {
            const kids = notes.filter((n) => n.folder === f.name);
            const isOpen = open.has(f.id);
            return (
              <li key={f.id}>
                {/* 文件夹行：可展开 */}
                <button
                  type="button"
                  onClick={() => toggle(f.id)}
                  className={cx(
                    'flex h-6 w-full items-center gap-1 rounded-[7px] pr-1.5 text-left transition-colors duration-200 ease-apple',
                    active === f.id ? 'bg-sel' : 'hover:bg-page',
                    f.depth ? 'pl-5' : 'pl-1.5',
                  )}
                >
                  <span className={cx('flex h-3 w-3 shrink-0 items-center justify-center transition-transform duration-200 ease-apple', isOpen ? '' : '-rotate-90')}>
                    <ChevronDownIcon size={10} />
                  </span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-[#C8A24B]">
                    <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                  </svg>
                  <span className={cx('min-w-0 flex-1 truncate text-[12px]', active === f.id ? 'text-ink' : 'text-ink2')}>
                    {f.name}
                  </span>
                  <span className="gf-num shrink-0 text-[10px] text-ink3">{kids.length}</span>
                </button>
                {/* 文件夹下笔记（资源管理器式） */}
                {isOpen && kids.length > 0 && (
                  <ul className="ml-2.5 flex flex-col gap-0.5 border-l border-line pl-1.5">
                    {kids.map((n) => (
                      <li key={n.id}>
                        <button
                          type="button"
                          onClick={() => onPickNote(n.id)}
                          className={cx(
                            'flex h-6 w-full items-center gap-1 rounded-[7px] pr-1 text-left transition-colors duration-200 ease-apple',
                            activeNote === n.id ? 'bg-brandSoft' : 'hover:bg-page',
                          )}
                        >
                          <NotesIcon size={11} className="shrink-0 text-ink3" />
                          <span className={cx('min-w-0 flex-1 truncate text-[11.5px]', activeNote === n.id ? 'font-medium text-brand' : 'text-ink2')}>
                            {n.title}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </div>
      <Divider className="my-2" />
      <button type="button" className="flex h-6 w-full items-center gap-1.5 rounded-[7px] px-1.5 text-[11px] text-ink3 hover:bg-page hover:text-ink">
        <PlusIcon size={12} />
        新建文件夹
      </button>
    </>
  );
}

function NoteEditor({ note, highlight, onClose }) {
  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="flex items-center gap-2">
        <Badge tone="brand">{note.folder}</Badge>
        <span className="min-w-0 flex-1 truncate text-[10px] text-ink3">{note.source}</span>
        {onClose ? (
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭编辑器"
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[7px] text-ink3 hover:bg-sel hover:text-ink"
          >
            <CloseIcon size={13} />
          </button>
        ) : null}
      </div>
      <h3 className="mt-1.5 truncate text-[15px] font-medium leading-[22px] text-ink">{note.title}</h3>
      <p className="mt-1 text-[10px] text-ink3">
        更新于 {note.updated} · {note.words} 字 · 约 {note.readMinutes} 分钟读完
      </p>
      <div className="mt-1.5 flex flex-wrap items-center gap-1">
        {note.tags.map((t) => (
          <Badge key={t} tone="neutral">{t}</Badge>
        ))}
      </div>
      <Divider className="my-2.5" />
      <div className="flex flex-col gap-2">
        {note.blocks.map((b, i) => {
          if (b.type === 'h2') {
            return (
              <p key={i} className="text-[13px] font-medium leading-[20px] text-ink">
                {b.text}
              </p>
            );
          }
          if (b.type === 'quote') {
            return (
              <p key={i} className="border-l-2 border-line2 pl-2 text-[11px] leading-[17px] text-ink2">
                <RichText text={b.text} highlight={highlight} />
              </p>
            );
          }
          return (
            <p key={i} className="text-[12px] leading-[19px] text-ink2">
              <RichText text={b.text} highlight={highlight} />
            </p>
          );
        })}
      </div>
      <Divider className="my-2.5" />
      <p className="text-[11px] text-ink3">反向链接 · {note.backlinks.length} 条</p>
      <ul className="mt-1 flex flex-col gap-1">
        {note.backlinks.map((b) => (
          <li key={b.id} className="flex items-center gap-2">
            <NotesIcon size={11} className="shrink-0 text-ink3" />
            <span className="min-w-0 flex-1 truncate text-[11px] text-ink2">{b.title}</span>
            <span className="shrink-0 text-[10px] text-ink3">{b.time}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function NotesPage() {
  const [activeFolder, setActiveFolder] = useState('f3');
  const [activeNote, setActiveNote] = useState('n1');
  const [query, setQuery] = useState('');
  const [highlight, setHighlight] = useState(true);
  const [sort, setSort] = useState('recent');
  const [editorOpen, setEditorOpen] = useState(false);
  const [aiTidyOpen, setAiTidyOpen] = useState(false);

  const list = useMemo(() => {
    const q = query.trim();
    const base = noteList.filter((n) => !q || n.title.includes(q) || n.excerpt.includes(q));
    if (sort === 'words') return [...base].sort((a, b) => b.words - a.words);
    return base;
  }, [query, sort]);

  const picked = list.find((n) => n.id === activeNote) || list[0] || noteList[0];
  const editorNote = picked
    ? {
        ...noteOpen,
        id: picked.id,
        title: picked.title,
        folder: picked.folder,
        updated: picked.updated,
        words: picked.words,
        readMinutes: Math.max(1, Math.round(picked.words / 300)),
        blocks:
          picked.id === noteOpen.id
            ? noteOpen.blocks
            : [
                { type: 'p', text: picked.excerpt },
                { type: 'p', text: `本节内容来自《${picked.folder}》目录下的沉淀，关联 [[${noteList[0].title}]] 与 [[${noteList[1].title}]]。` },
                { type: 'quote', text: '提示：原型阶段笔记正文为 mock 摘要，编辑后自动保存到本地草稿。' },
              ],
      }
    : noteOpen;

  return (
    <div className="flex animate-fade-up flex-col gap-2.5">
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <Btn variant="solid" size="sm" icon={<PlusIcon size={13} />}>新建笔记</Btn>
          <div className="flex h-8 w-[200px] shrink-0 items-center gap-1.5 rounded-[10px] border border-line bg-card px-2.5">
            <SearchIcon size={13} className="shrink-0 text-ink3" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索标题或正文"
              className="h-full w-full min-w-0 bg-transparent text-[12px] text-ink placeholder:text-ink3 focus:outline-none"
            />
          </div>
          <div className="flex shrink-0 items-center rounded-[10px] bg-sel p-0.5">
            {[
              ['recent', '最近编辑'],
              ['words', '字数'],
            ].map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setSort(key)}
                className={cx(
                  'h-7 rounded-[8px] px-2.5 text-[11px] transition-colors duration-200 ease-apple',
                  sort === key ? 'bg-card text-ink shadow-[0_1px_2px_rgba(0,0,0,0.06)]' : 'text-ink3 hover:text-ink',
                )}
              >
                {label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setHighlight((v) => !v)}
            className={cx(
              'flex h-7 shrink-0 items-center gap-1.5 rounded-[8px] px-2.5 text-[11px] transition-colors duration-200 ease-apple',
              highlight ? 'bg-brandSoft text-brand' : 'text-ink3 hover:bg-sel hover:text-ink',
            )}
          >
            <span className={cx('h-1.5 w-1.5 rounded-full', highlight ? 'bg-brand' : 'bg-line2')} />
            双链高亮
          </button>
          <span className="ml-auto hidden text-[11px] text-ink3 sm:block">
            共 <span className="gf-num text-ink">{list.length}</span> 条 · 本周新增 4 条
          </span>
          <Btn variant="line" size="sm" className="min-[1440px]:hidden" icon={<NotesIcon size={13} />} onClick={() => setEditorOpen(true)}>
            打开编辑器
          </Btn>
          <Btn variant="line" size="sm" icon={<SparkIcon size={13} />}>AI 补写</Btn>
          <Btn variant="line" size="sm" icon={<SparkIcon size={13} />} onClick={() => setAiTidyOpen(true)}>AI 整理</Btn>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-2.5 min-[760px]:grid-cols-12">
        <Card className="min-[760px]:col-span-4">
          <FolderTree active={activeFolder} onPickNote={setActiveNote} activeNote={activeNote} folders={noteFolders} notes={noteList} />
          <Divider className="my-2.5" />
          <SectionTitle title="笔记统计" sub="全部笔记概览" action={<Badge tone="brand">{noteStats.total} 篇</Badge>} />
          <div className="flex flex-col gap-2">
            <div className="grid grid-cols-2 gap-2">
              <Kpi label="总字数" value={noteStats.words} unit="字" tone="ink" />
              <Kpi label="双链" value={noteStats.links} unit="条" tone="brand" />
            </div>
            <div className="flex flex-col gap-1.5 pt-1">
              {noteStats.dist.map((d) => (
                <MeterRow key={d.label} label={d.label} value={d.value} total={noteStats.total} tone={d.tone} suffix={`${d.value} 篇`} />
              ))}
            </div>
          </div>
        </Card>

        {/* 编辑器（原笔记列表已并入文件树，此处直接放大） */}
        <Card className="hidden min-[760px]:col-span-5 min-[1440px]:flex">
          <NoteEditor note={editorNote} highlight={highlight} />
        </Card>

        {/* 右侧：链接相关笔记 */}
        <Card className="hidden min-[1440px]:col-span-3 min-[1440px]:flex">
          <SectionTitle title="相关笔记" sub="反链与同文件夹" action={<Badge tone="brand">{editorNote.backlinks?.length || 0} 链</Badge>} />
          <div className="flex flex-col gap-1">
            {(editorNote.backlinks || []).map((b) => (
              <button
                key={b.id}
                type="button"
                onClick={() => {
                  const target = noteList.find((x) => x.title === b.title);
                  if (target) setActiveNote(target.id);
                }}
                className="flex w-full flex-col items-start rounded-[8px] border-b border-line px-1.5 py-1.5 text-left transition-colors duration-200 ease-apple last:border-b-0 hover:bg-page"
              >
                <span className="min-w-0 max-w-full truncate text-[11.5px] leading-[16px] text-ink2">{b.title}</span>
                <span className="gf-num text-[10px] leading-[14px] text-ink3">{b.time}</span>
              </button>
            ))}
            {(!editorNote.backlinks || editorNote.backlinks.length === 0) && (
              <p className="py-6 text-center text-[11px] text-ink3">暂无反向链接</p>
            )}
          </div>
          <Divider className="my-2" />
          <SectionTitle title="同文件夹" sub={editorNote.folder || ''} />
          <div className="flex flex-col gap-1">
            {noteList
              .filter((x) => x.id !== editorNote.id && x.folder === (editorNote.folder || '').split(' / ').pop())
              .slice(0, 5)
              .map((x) => (
                <button
                  key={x.id}
                  type="button"
                  onClick={() => setActiveNote(x.id)}
                  className="flex items-center gap-1.5 rounded-[8px] px-1.5 py-1.5 text-left transition-colors duration-200 ease-apple hover:bg-page"
                >
                  <span className="h-1 w-1 shrink-0 rounded-full bg-line2" />
                  <span className="min-w-0 flex-1 truncate text-[11.5px] leading-[16px] text-ink2">{x.title}</span>
                </button>
              ))}
          </div>
        </Card>
      </div>

      <Card>
        <SectionTitle title="最近编辑" sub="最新变动的 4 条笔记" action={<Badge tone="line">时间线</Badge>} />
        <ul className="flex flex-col">
          {notesRecent.map((r, i) => (
            <li key={r.id} className="relative flex items-start gap-2.5 pb-3 last:pb-0">
              <span className={cx('mt-1 flex h-2 w-2 shrink-0 rounded-full', i === 0 ? 'bg-brand' : 'bg-line2')} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="min-w-0 flex-1 truncate text-[12px] leading-[17px] text-ink">{r.title}</p>
                  <span className="shrink-0 text-[10px] text-ink3">{r.time}</span>
                </div>
                <p className="mt-0.5 text-[10px] leading-[14px] text-ink3">
                  <Badge tone="neutral">{r.folder}</Badge>
                  <span className="ml-1.5">{r.action}</span>
                </p>
              </div>
            </li>
          ))}
        </ul>
      </Card>

      {editorOpen ? (
        <div className="fixed inset-0 z-40 flex justify-end min-[1440px]:hidden">
          <button type="button" aria-label="关闭编辑器" onClick={() => setEditorOpen(false)} className="absolute inset-0 bg-ink/20" />
          <aside className="relative flex h-full w-[460px] animate-fade-up flex-col border-l border-line bg-card px-4 py-3 shadow-pop">
            <NoteEditor note={editorNote} highlight={highlight} onClose={() => setEditorOpen(false)} />
            <div className="mt-2 flex shrink-0 items-center gap-2 border-t border-line pt-2">
              {noteOpen.aiActions.map((a) => (
                <Btn key={a} variant="line" size="xs" icon={<SparkIcon size={11} />}>{a}</Btn>
              ))}
              <Link to="/deck" className="ml-auto flex items-center gap-1 text-[11px] text-ink2 hover:text-ink">
                生成卡片
                <ArrowRightIcon size={11} />
              </Link>
            </div>
          </aside>
        </div>
      ) : null}

      <Card pad={false} className="min-[1440px]:hidden">
        <div className="flex items-center gap-2 px-4 py-2.5">
          <ChevronDownIcon size={13} className="shrink-0 text-ink3" />
          <p className="min-w-0 flex-1 truncate text-[11px] text-ink3">
            窗口宽度 ≥ 1440px 时笔记编辑器与文件夹、列表并排显示；当前宽度下编辑器以抽屉形式打开。
          </p>
        </div>
      </Card>

      <AiTidyDrawer open={aiTidyOpen} onClose={() => setAiTidyOpen(false)} />
    </div>
  );
}
