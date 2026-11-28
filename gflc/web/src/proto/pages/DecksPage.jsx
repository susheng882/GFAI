import React, { useMemo, useState } from 'react';
import { Badge, Btn, Card, Divider, Progress, SectionTitle, cx } from '../ui.jsx';
import { CheckIcon, DeckIcon, PlusIcon, SearchIcon } from '../NavIcons.jsx';
import {
  deckCards as seedCards,
  deckChapters,
  deckEditor,
  deckProficiency,
  deckStats,
  deckSubjects,
} from '../mock/index.js';

const LEVEL_TONE = { 生疏: 'bad', 一般: 'warn', 熟练: 'brand', 已掌握: 'ok' };
const ROW_GRID = 'grid grid-cols-[20px_minmax(0,1fr)_136px_66px_58px_52px_56px] items-center gap-2';

function masteryTone(v) {
  if (v >= 75) return 'ok';
  if (v >= 60) return 'brand';
  return 'warn';
}

function Chip({ on, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        'h-6 shrink-0 rounded-[7px] px-2 text-[10px] transition-colors duration-200 ease-apple',
        on ? 'bg-ink text-white' : 'bg-page text-ink2 hover:text-ink',
      )}
    >
      {children}
    </button>
  );
}

function EditorModal({ title, draft, onClose }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-[#1D1D1F]/30 px-6">
      <Card className="w-[620px] max-w-full" role="dialog" aria-modal="true" aria-label="卡片编辑">
        <SectionTitle
          title={title}
          sub="正面写问题，背面写答案；标签用于复习筛选"
          action={<Btn variant="ghost" size="xs" onClick={onClose}>关闭</Btn>}
        />
        <div className="flex flex-col gap-2.5">
          <label className="block">
            <span className="text-[11px] leading-[16px] text-ink3">正面 · 问题</span>
            <input defaultValue={draft.front} className="gf-input mt-1 h-9 text-[12px]" />
          </label>
          <label className="block">
            <span className="text-[11px] leading-[16px] text-ink3">背面 · 答案</span>
            <textarea
              defaultValue={draft.back}
              rows={3}
              className="mt-1 w-full resize-none rounded-[10px] border border-line bg-card px-3 py-2 text-[12px] leading-[19px] text-ink focus:border-line2 focus:outline-none"
            />
          </label>
          <div className="grid grid-cols-2 gap-2.5">
            <label className="block">
              <span className="text-[11px] leading-[16px] text-ink3">所属章节</span>
              <select defaultValue={draft.chapter} className="gf-input mt-1 h-9 text-[12px]">
                {deckEditor.chapterOptions.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
            <div>
              <span className="text-[11px] leading-[16px] text-ink3">标签</span>
              <div className="mt-1 flex h-9 flex-wrap items-center gap-1 rounded-[10px] border border-line bg-card px-2">
                {deckEditor.tagOptions.slice(0, 4).map((t) => (
                  <Badge key={t} tone={draft.tags.includes(t) ? 'brand' : 'neutral'}>{t}</Badge>
                ))}
              </div>
            </div>
          </div>
        </div>
        <Divider className="my-3" />
        <div className="flex items-center justify-between">
          <p className="text-[11px] text-ink3">保存后立即加入「{draft.chapter}」卡包</p>
          <div className="flex items-center gap-1.5">
            <Btn variant="line" size="sm" onClick={onClose}>取消</Btn>
            <Btn variant="solid" size="sm" icon={<CheckIcon size={13} />} onClick={onClose}>保存卡片</Btn>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default function DecksPage() {
  const [subject, setSubject] = useState('全部');
  const [level, setLevel] = useState('全部');
  const [chapter, setChapter] = useState('全部');
  const [query, setQuery] = useState('');
  const [cards, setCards] = useState(seedCards);
  const [selected, setSelected] = useState(['dc2', 'dc5']);
  const [editor, setEditor] = useState(null);

  const packs = useMemo(
    () => deckChapters.filter((d) => subject === '全部' || d.subject === subject),
    [subject],
  );

  const list = useMemo(() => {
    const q = query.trim();
    return cards.filter((c) => {
      if (chapter !== '全部' && c.chapter !== chapter) return false;
      if (level !== '全部' && c.level !== level) return false;
      if (q && !(c.front.includes(q) || c.chapter.includes(q))) return false;
      return true;
    });
  }, [cards, chapter, level, query]);

  const allOn = list.length > 0 && list.every((c) => selected.includes(c.id));

  const toggle = (id) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const toggleAll = () =>
    setSelected(allOn ? [] : Array.from(new Set([...selected, ...list.map((c) => c.id)])));

  const markMastered = () =>
    setCards((prev) => prev.map((c) => (selected.includes(c.id) ? { ...c, level: '已掌握' } : c)));

  return (
    <div className="flex animate-fade-up flex-col gap-2.5">
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex h-8 w-[210px] shrink-0 items-center gap-1.5 rounded-[10px] border border-line bg-card px-2.5">
            <SearchIcon size={13} className="shrink-0 text-ink3" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索卡片正面 / 章节"
              className="h-full w-full min-w-0 bg-transparent text-[12px] text-ink placeholder:text-ink3 focus:outline-none"
            />
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {deckSubjects.map((s) => (
              <Chip key={s} on={subject === s} onClick={() => setSubject(s)}>{s}</Chip>
            ))}
          </div>
          <span className="ml-auto flex items-center gap-2.5 text-[11px] text-ink3">
            <span>卡包 <span className="gf-num text-ink">{deckStats.packs}</span></span>
            <span>卡片 <span className="gf-num text-ink">{deckStats.cards}</span></span>
            <span>今日到期 <span className="gf-num text-[#B26A00]">{deckStats.due}</span></span>
            <span>平均掌握 <span className="gf-num text-ink">{deckStats.mastery}%</span></span>
          </span>
          <Btn
            variant="solid"
            size="sm"
            icon={<PlusIcon size={13} />}
            onClick={() => setEditor({ title: deckEditor.newTitle, draft: deckEditor.draft })}
          >
            新建卡片
          </Btn>
        </div>
      </Card>

      <Card>
        <SectionTitle
          title="章节卡包"
          sub={`按大纲章节组织的背诵卡包 · 同步于 ${deckStats.syncAt}`}
          action={<Badge tone="line">{packs.length} 个卡包</Badge>}
        />
        <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
          {packs.map((d) => (
            <button
              key={d.id}
              type="button"
              onClick={() => setChapter(chapter === d.title ? '全部' : d.title)}
              className={cx(
                'flex flex-col gap-1 rounded-[12px] border p-2 text-left transition-colors duration-200 ease-apple',
                chapter === d.title ? 'border-line2 bg-page' : 'border-line bg-card hover:bg-page',
              )}
            >
              <div className="flex items-center gap-1.5">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-[6px] bg-page text-ink2">
                  <DeckIcon size={12} />
                </span>
                <span className="truncate text-[12px] leading-[17px] text-ink">{d.title}</span>
              </div>
              <p className="truncate text-[11px] leading-[15px] text-ink3">{d.front}</p>
              <div className="flex items-center gap-1.5">
                <Progress value={d.mastery} tone={masteryTone(d.mastery)} height="h-1" className="w-[52px]" />
                <span className="gf-num text-[10px] text-ink3">{d.mastery}%</span>
                <span className="gf-num ml-auto text-[10px] text-ink3">{d.cards} 张</span>
                {d.due ? <Badge tone="warn">{d.due} 到期</Badge> : null}
              </div>
            </button>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle
          title="卡片浏览器"
          sub={chapter === '全部' ? '全部章节 · 勾选可批量操作' : `已筛选：${chapter}`}
          action={
            <>
              <div className="flex items-center gap-1">
                {deckProficiency.map((p) => (
                  <Chip key={p} on={level === p} onClick={() => setLevel(p)}>{p}</Chip>
                ))}
              </div>
              <Badge tone="brand" dot>{list.length} 张</Badge>
            </>
          }
        />

        <div className="mb-2 flex flex-wrap items-center gap-1.5 rounded-[10px] bg-page px-2.5 py-1.5">
          <span className="text-[11px] text-ink2">
            已选 <span className="gf-num text-ink">{selected.length}</span> 张
          </span>
          <span className="text-[11px] text-ink3">批量操作仅影响当前筛选结果</span>
          <div className="ml-auto flex items-center gap-1.5">
            <Btn variant="line" size="xs" icon={<CheckIcon size={12} />} onClick={markMastered}>标记已掌握</Btn>
            <Btn variant="line" size="xs" onClick={() => setSelected([])}>移到明天</Btn>
            <Btn variant="line" size="xs" onClick={() => setCards((p) => p.filter((c) => !selected.includes(c.id)))}>
              删除所选
            </Btn>
            <Btn variant="ghost" size="xs" onClick={() => setSelected([])}>取消选择</Btn>
          </div>
        </div>

        <div className={cx(ROW_GRID, 'border-b border-line pb-1 text-[10px] text-ink3')}>
          <button type="button" onClick={toggleAll} aria-label="全选" className="flex items-center">
            <span
              className={cx(
                'flex h-3.5 w-3.5 items-center justify-center rounded-[4px] border',
                allOn ? 'border-brand bg-brand text-white' : 'border-line2 bg-card text-transparent',
              )}
            >
              <CheckIcon size={9} />
            </span>
          </button>
          <span>卡片正面</span>
          <span>所属章节</span>
          <span>熟练度</span>
          <span className="gf-num text-right">到期</span>
          <span className="gf-num text-right">复习</span>
          <span className="text-right">操作</span>
        </div>

        <ul>
          {list.map((c) => {
            const on = selected.includes(c.id);
            return (
              <li
                key={c.id}
                className={cx(ROW_GRID, 'h-[27px] border-b border-line last:border-b-0 hover:bg-page')}
              >
                <button type="button" onClick={() => toggle(c.id)} aria-label="选择卡片" className="flex items-center">
                  <span
                    className={cx(
                      'flex h-3.5 w-3.5 items-center justify-center rounded-[4px] border',
                      on ? 'border-brand bg-brand text-white' : 'border-line2 bg-card text-transparent',
                    )}
                  >
                    <CheckIcon size={9} />
                  </span>
                </button>
                <span className="truncate text-[12px] leading-[17px] text-ink">{c.front}</span>
                <span className="truncate text-[11px] text-ink3">{c.chapter}</span>
                <Badge tone={LEVEL_TONE[c.level] || 'neutral'}>{c.level}</Badge>
                <span className="gf-num text-right text-[10px] text-ink3">{c.due}</span>
                <span className="gf-num text-right text-[11px] text-ink2">{c.reviews}</span>
                <div className="flex items-center justify-end">
                  <button
                    type="button"
                    onClick={() => setEditor({ title: deckEditor.editTitle, draft: { ...deckEditor.draft, front: c.front, chapter: c.chapter, tags: c.tags } })}
                    className="text-[10px] text-ink2 hover:text-brand"
                  >
                    编辑
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
        {list.length === 0 ? (
          <p className="py-6 text-center text-[12px] text-ink3">没有匹配的卡片，试试换个熟练度或章节</p>
        ) : null}
      </Card>

      {editor ? <EditorModal title={editor.title} draft={editor.draft} onClose={() => setEditor(null)} /> : null}
    </div>
  );
}
