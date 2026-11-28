import React, { useState } from 'react';
import { Badge, Btn, Card, Divider, Empty, Kpi, MeterRow, Progress, SectionTitle, cx } from '../ui.jsx';
import {
  ArrowRightIcon,
  CheckIcon,
  CloseIcon,
  FlameIcon,
  PlayIcon,
  SparkIcon,
  TargetIcon,
} from '../NavIcons.jsx';
import {
  examHistory,
  examPaper,
  quizSession,
  reciteCards,
  reciteGroups,
  studyModes,
  wrongList,
  wrongStats,
} from '../mock/index.js';

const CARD_TONE = {
  right: 'bg-[#EAF8EE] text-[#248A3D]',
  wrong: 'bg-[#FDECEC] text-[#C4322B]',
  cur: 'bg-ink text-white',
  todo: 'bg-page text-ink3',
};

const LEVEL_TONE = { 生疏: 'bad', 一般: 'warn', 熟练: 'brand', 已掌握: 'ok' };

/* ---------------- 刷题 ---------------- */

function QuizPanel() {
  const [picked, setPicked] = useState(quizSession.picked);
  const [submitted, setSubmitted] = useState(false);
  const right = picked === quizSession.answer;

  return (
    <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-12">
      <Card className="xl:col-span-8">
        <SectionTitle
          title={quizSession.bank}
          sub={`第 ${quizSession.index} / ${quizSession.total} 题 · ${quizSession.difficulty} · 已用 ${quizSession.spent}`}
          action={
            <>
              <Badge tone="line">{quizSession.kind}</Badge>
              {submitted ? (
                <Badge tone={right ? 'ok' : 'bad'} dot>{right ? '回答正确' : `答错 · 正确 ${quizSession.answer}`}</Badge>
              ) : (
                <Badge tone="brand" dot>作答中</Badge>
              )}
            </>
          }
        />

        <p className="rounded-[10px] bg-page px-3 py-2.5 text-[13px] leading-[21px] text-ink">
          {quizSession.stem}
        </p>

        <div className="mt-2 flex flex-col gap-1.5">
          {quizSession.options.map((o) => {
            const on = picked === o.key;
            const isRight = o.key === quizSession.answer;
            return (
              <button
                key={o.key}
                type="button"
                onClick={() => setPicked(o.key)}
                className={cx(
                  'flex h-[34px] items-center gap-2 rounded-[10px] border px-2.5 text-left text-[12px] transition-colors duration-200 ease-apple',
                  on ? 'border-brand bg-brandSoft text-ink' : 'border-line bg-card text-ink2 hover:bg-page',
                  submitted && isRight ? 'border-ok bg-[#EAF8EE] text-ink' : '',
                )}
              >
                <span
                  className={cx(
                    'flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[10px]',
                    on ? 'border-brand bg-brand text-white' : 'border-line2 bg-card text-ink3',
                  )}
                >
                  {o.key}
                </span>
                <span className="truncate">{o.text}</span>
              </button>
            );
          })}
        </div>

        <div className="mt-2 rounded-[10px] bg-page px-3 py-2">
          <div className="flex items-center gap-1.5">
            <SparkIcon size={12} className="text-ink3" />
            <span className="text-[11px] font-medium text-ink">参考答案 {quizSession.answer} · 解析</span>
            <div className="ml-auto flex items-center gap-1">
              {quizSession.tags.map((t) => (
                <Badge key={t} tone="neutral">{t}</Badge>
              ))}
            </div>
          </div>
          {quizSession.explain.map((line, i) => (
            <p key={i} className={cx('text-[11px] leading-[17px] text-ink2', i === 0 ? 'mt-1' : '')}>
              {line}
            </p>
          ))}
        </div>

        <div className="mt-2 flex items-center gap-1.5">
          <span className="text-[11px] text-ink3">已答 {quizSession.stats.done} 题 · 正确 {quizSession.stats.right} · 错误 {quizSession.stats.wrong}</span>
          <div className="ml-auto flex items-center gap-1.5">
            <Btn variant="line" size="sm">上一题</Btn>
            <Btn variant="line" size="sm">下一题</Btn>
            <Btn variant="solid" size="sm" icon={<CheckIcon size={13} />} onClick={() => setSubmitted(true)}>
              {submitted ? '重新作答' : '提交答案'}
            </Btn>
          </div>
        </div>
      </Card>

      <div className="flex flex-col gap-2.5 xl:col-span-4">
        <Card>
          <SectionTitle title="答题卡" sub="点击题号可跳题" action={<Badge tone="line">{quizSession.total} 题</Badge>} />
          <div className="mb-2 flex items-center gap-2.5 text-[10px] text-ink3">
            <span>已答 <span className="gf-num text-ink">{quizSession.stats.done}</span></span>
            <span>正确 <span className="gf-num text-[#248A3D]">{quizSession.stats.right}</span></span>
            <span>错误 <span className="gf-num text-[#C4322B]">{quizSession.stats.wrong}</span></span>
            <span>未做 <span className="gf-num text-ink">{quizSession.stats.left}</span></span>
          </div>
          <div className="grid grid-cols-5 gap-1.5">
            {quizSession.card.map((state, i) => (
              <div
                key={i}
                className={cx(
                  'flex h-[26px] items-center justify-center rounded-[7px] text-[11px] tabular-nums',
                  CARD_TONE[state],
                )}
              >
                {i + 1}
              </div>
            ))}
          </div>
          <div className="mt-2 flex items-center gap-2 text-[10px] text-ink3">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-[2px] bg-[#EAF8EE]" />正确</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-[2px] bg-[#FDECEC]" />错误</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-[2px] bg-ink" />当前</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-[2px] bg-sel" />未做</span>
          </div>
        </Card>

        <Card>
          <SectionTitle title="本轮设置" sub="按模式自动套用" />
          <div className="flex flex-col gap-1.5">
            {quizSession.settings.map((s) => (
              <div key={s.label} className="flex items-center justify-between text-[11px]">
                <span className="text-ink2">{s.label}</span>
                <span className="text-ink3">{s.value}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

/* ---------------- 背诵 ---------------- */

function ReciteModal({ index, onClose, onStep }) {
  const [flipped, setFlipped] = useState(false);
  const card = reciteCards[index];
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-[#1D1D1F]/30 px-6">
      <Card className="w-[720px] max-w-full" role="dialog" aria-modal="true" aria-label="背诵卡片预览">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <Badge tone="brand">{card.chapter}</Badge>
              {card.tags.map((t) => (
                <Badge key={t} tone="neutral">{t}</Badge>
              ))}
              <Badge tone={LEVEL_TONE[card.level] || 'neutral'}>{card.level}</Badge>
            </div>
            <p className="mt-1.5 text-[11px] leading-[16px] text-ink3">
              第 <span className="gf-num text-ink">{index + 1}</span> / {reciteCards.length} 张 · 已复习 {card.reviews} 次 ·
              {flipped ? ' 当前为背面' : ' 当前为正面'}
            </p>
          </div>
          <Btn variant="ghost" size="xs" icon={<CloseIcon size={13} />} onClick={onClose}>关闭</Btn>
        </div>

        <div className="mt-2 min-h-[248px] rounded-[12px] border border-line bg-page px-3.5 py-3">
          {flipped ? (
            <div>
              <p className="text-[11px] leading-[16px] text-ink3">整块知识点 · {card.chapter}</p>
              <ul className="mt-1.5 flex flex-col gap-1">
                {card.point.map((line, i) => (
                  <li key={i} className="text-[12px] leading-[19px] text-ink">{line}</li>
                ))}
              </ul>
              <p className="mt-2 rounded-[8px] bg-[#FFF4E5] px-2 py-1.5 text-[11px] leading-[17px] text-[#B26A00]">
                {card.tip}
              </p>
            </div>
          ) : (
            <div>
              <p className="text-[11px] leading-[16px] text-ink3">正面 · 问题</p>
              <p className="mt-1.5 text-[16px] font-medium leading-[24px] text-ink">{card.front}</p>
              <Divider className="my-2.5" />
              <p className="text-[11px] leading-[16px] text-ink3">
                这张卡片背后是一整块知识点，共 {card.point.length} 个要点，点击「翻面」查看完整内容。
              </p>
              <p className="mt-1.5 text-[12px] leading-[19px] text-ink2">{card.point[0]}</p>
            </div>
          )}
        </div>

        <div className="mt-2.5 flex items-center gap-1.5">
          <Btn variant="line" size="sm" onClick={() => onStep(-1)}>上一张</Btn>
          <Btn variant="line" size="sm" onClick={() => onStep(1)}>下一张</Btn>
          <span className="text-[11px] text-ink3">翻面后可标记熟练度，进入复习队列</span>
          <div className="ml-auto flex items-center gap-1.5">
            <Btn variant="solid" size="sm" icon={<PlayIcon size={13} />} onClick={() => setFlipped((v) => !v)}>
              {flipped ? '看正面' : '翻面'}
            </Btn>
          </div>
        </div>
      </Card>
    </div>
  );
}

function RecitePanel() {
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [group, setGroup] = useState('全部');

  const step = (delta) =>
    setIndex((prev) => (prev + delta + reciteCards.length) % reciteCards.length);

  return (
    <>
      <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-12">
        <Card className="xl:col-span-3">
          <SectionTitle title="卡包分组" sub={`${reciteGroups.length} 个卡包 · 今日到期 52 张`} />
          <ul className="flex flex-col gap-1">
            <li>
              <button
                type="button"
                onClick={() => setGroup('全部')}
                className={cx(
                  'flex w-full items-center justify-between rounded-[8px] px-2 py-1.5 text-left text-[12px] transition-colors duration-200 ease-apple',
                  group === '全部' ? 'bg-sel text-ink' : 'text-ink2 hover:bg-page hover:text-ink',
                )}
              >
                <span>全部卡片</span>
                <span className="gf-num text-[10px] text-ink3">{reciteCards.length}</span>
              </button>
            </li>
            {reciteGroups.map((g) => (
              <li key={g.id}>
                <button
                  type="button"
                  onClick={() => setGroup(g.label)}
                  className={cx(
                    'flex w-full flex-col gap-1 rounded-[8px] px-2 py-1.5 text-left transition-colors duration-200 ease-apple',
                    group === g.label ? 'bg-sel' : 'hover:bg-page',
                  )}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-[11px] leading-[16px] text-ink">{g.label}</span>
                    <span className="gf-num shrink-0 text-[10px] text-ink3">{g.cards}</span>
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Progress value={g.mastery} tone="brand" height="h-1" className="w-[64px]" />
                    <span className="gf-num text-[10px] text-ink3">{g.mastery}%</span>
                    <Badge tone="warn">{g.due} 到期</Badge>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="xl:col-span-9">
          <SectionTitle
            title="卡片墙"
            sub="每张卡片是一整块知识点 · 点开可预览、翻面与顺序浏览"
            action={
              <>
                <Badge tone="line">{group}</Badge>
                <Btn variant="solid" size="sm" icon={<PlayIcon size={13} />} onClick={() => { setIndex(0); setOpen(true); }}>
                  开始背诵
                </Btn>
              </>
            }
          />
          <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
            {reciteCards.map((c, i) => (
              <button
                key={c.id}
                type="button"
                onClick={() => { setIndex(i); setOpen(true); }}
                className="flex h-[84px] flex-col gap-1 rounded-[12px] border border-line bg-card p-2.5 text-left transition-colors duration-200 ease-apple hover:bg-page"
              >
                <span className="flex items-center gap-1">
                  <Badge tone="brand">{c.chapter}</Badge>
                  <span className="gf-num ml-auto text-[10px] text-ink3">{c.point.length} 要点</span>
                </span>
                <span className="line-clamp-2 text-[12px] leading-[17px] text-ink">{c.front}</span>
                <span className="mt-auto flex items-center justify-between">
                  <span className="text-[10px] text-ink3">复习 {c.reviews} 次</span>
                  <Badge tone={LEVEL_TONE[c.level] || 'neutral'}>{c.level}</Badge>
                </span>
              </button>
            ))}
          </div>
        </Card>
      </div>
      {open ? (
        <ReciteModal index={index} onClose={() => setOpen(false)} onStep={step} />
      ) : null}
    </>
  );
}

/* ---------------- 模考 ---------------- */

function ExamPanel() {
  return (
    <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-12">
      <Card className="xl:col-span-8">
        <SectionTitle
          title={examPaper.title}
          sub={`${examPaper.subject} · 开卷时间 ${examPaper.openedAt} · 截止 ${examPaper.deadline}`}
          action={<Badge tone="warn" dot>{examPaper.status}</Badge>}
        />
        <div className="grid grid-cols-4 gap-3">
          <Kpi label="题量" value={examPaper.questions} unit="题" />
          <Kpi label="时长" value={examPaper.minutes} unit="分钟" />
          <Kpi label="满分" value={examPaper.full} unit="分" />
          <Kpi label="当前均分" value={examHistory[1].score} unit="分" tone="brand" />
        </div>
        <Divider className="my-2.5" />
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
          <div className="flex flex-col gap-1">
            <p className="text-[11px] leading-[16px] text-ink3">题型分布</p>
            {examPaper.types.map((t) => (
              <div key={t.label} className="flex items-center justify-between text-[11px]">
                <span className="text-ink2">{t.label}</span>
                <span className="gf-num text-ink3">{t.count} 题 · {t.score} 分</span>
              </div>
            ))}
          </div>
          <div className="flex flex-col gap-1">
            <p className="text-[11px] leading-[16px] text-ink3">科目分布</p>
            {examPaper.subjects.map((s) => (
              <MeterRow key={s.label} label={s.label} value={s.count} total={examPaper.questions} tone="brand" suffix={`${s.score} 分`} />
            ))}
          </div>
        </div>
        <Divider className="my-2.5" />
        <ul className="flex flex-col gap-1">
          {examPaper.rules.map((r) => (
            <li key={r} className="flex items-start gap-1.5 text-[11px] leading-[16px] text-ink3">
              <span className="mt-[6px] h-1 w-1 shrink-0 rounded-full bg-line2" />
              <span>{r}</span>
            </li>
          ))}
        </ul>
        <div className="mt-2.5 flex items-center gap-1.5">
          <span className="flex items-center gap-1 text-[11px] text-ink3">
            <FlameIcon size={12} /> 连续模考 3 周，平均提升 6 分
          </span>
          <div className="ml-auto flex items-center gap-1.5">
            <Btn variant="line" size="sm">查看解析</Btn>
            <Btn variant="solid" size="sm" icon={<PlayIcon size={13} />}>开始模考</Btn>
          </div>
        </div>
      </Card>

      <Card className="xl:col-span-4">
        <SectionTitle title="历史成绩" sub="最近 7 次模考记录" action={<Badge tone="brand">{examHistory.length} 次</Badge>} />
        {examHistory.length === 0 ? <Empty text="暂无模考记录" /> : null}
        <ul>
          <li className="grid grid-cols-[minmax(0,1fr)_46px_44px_40px] items-center gap-1.5 border-b border-line pb-1 text-[10px] text-ink3">
            <span>试卷</span>
            <span className="gf-num text-right">得分</span>
            <span className="gf-num text-right">用时</span>
            <span className="text-right">日期</span>
          </li>
          {examHistory.map((h) => (
            <li
              key={h.id}
              className="grid h-[28px] grid-cols-[minmax(0,1fr)_46px_44px_40px] items-center gap-1.5 border-b border-line last:border-b-0 hover:bg-page"
            >
              <span className="truncate text-[11px] text-ink">{h.name}</span>
              <span className="gf-num text-right text-[11px] text-ink">{h.score}<span className="text-[10px] text-ink3">/{h.full}</span></span>
              <span className="gf-num text-right text-[10px] text-ink3">{h.minutes}′</span>
              <span className="gf-num text-right text-[10px] text-ink3">{h.date}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

/* ---------------- 错题 ---------------- */

const WRONG_GRID = 'grid grid-cols-[minmax(0,1fr)_118px_76px_40px_78px_40px] items-center gap-2';

function WrongPanel() {
  return (
    <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-12">
      <Card className="xl:col-span-8">
        <SectionTitle
          title="错题本"
          sub={`共 ${wrongStats.total} 道本期错题 · 本周新增 ${wrongStats.weekNew} 道`}
          action={
            <>
              <Badge tone="bad">连续错 3 次以上 {wrongList.filter((w) => w.times >= 3).length} 道</Badge>
              <Btn variant="line" size="xs">只看生疏</Btn>
            </>
          }
        />
        <div className={cx(WRONG_GRID, 'border-b border-line pb-1 text-[10px] text-ink3')}>
          <span>题干</span>
          <span>来源</span>
          <span>章节</span>
          <span className="gf-num text-right">错次</span>
          <span className="gf-num text-right">最近一次</span>
          <span className="text-right">操作</span>
        </div>
        <ul>
          {wrongList.map((w) => (
            <li key={w.id} className={cx(WRONG_GRID, 'h-[32px] border-b border-line last:border-b-0 hover:bg-page')}>
              <span className="truncate text-[12px] leading-[17px] text-ink">{w.stem}</span>
              <span className="truncate text-[11px] text-ink3">{w.from}</span>
              <span className="truncate text-[11px] text-ink2">{w.chapter}</span>
              <span className="gf-num text-right text-[11px] text-[#C4322B]">{w.times}</span>
              <span className="gf-num text-right text-[10px] text-ink3">{w.last}</span>
              <div className="flex justify-end">
                <button type="button" className="text-[10px] text-ink2 hover:text-brand">重做</button>
              </div>
            </li>
          ))}
        </ul>
      </Card>

      <div className="flex flex-col gap-2.5 xl:col-span-4">
        <Card>
          <SectionTitle title="错题分布" sub="按章节统计近 30 天错题" action={<Badge tone="line">{wrongStats.redo} 待重做</Badge>} />
          <div className="flex flex-col gap-1.5">
            {wrongStats.dist.map((d) => (
              <MeterRow key={d.label} label={d.label} value={d.value} total={wrongStats.total} tone={d.tone} suffix={`${d.value} 道`} />
            ))}
          </div>
        </Card>
        <Card>
          <SectionTitle title="重做设置" sub="按遗忘曲线自动排序" />
          <div className="flex items-center gap-1">
            {['10 道', '20 道', '全部', '仅生疏'].map((t, i) => (
              <span
                key={t}
                className={cx(
                  'rounded-[7px] px-2 py-1 text-[10px]',
                  i === 1 ? 'bg-ink text-white' : 'bg-page text-ink2',
                )}
              >
                {t}
              </span>
            ))}
          </div>
          <div className="mt-2 flex items-center justify-between">
            <span className="flex items-center gap-1 text-[11px] text-ink3">
              <TargetIcon size={12} /> 目标正确率 80%
            </span>
            <Btn variant="solid" size="sm" icon={<ArrowRightIcon size={13} />}>开始重做</Btn>
          </div>
        </Card>
      </div>
    </div>
  );
}

/* ---------------- 页面 ---------------- */

export default function StudyPage() {
  const [mode, setMode] = useState('quiz');
  const current = studyModes.find((m) => m.key === mode) || studyModes[0];

  return (
    <div className="flex animate-fade-up flex-col gap-2.5">
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex h-8 shrink-0 items-center gap-0.5 rounded-[10px] bg-page p-0.5">
            {studyModes.map((m) => (
              <button
                key={m.key}
                type="button"
                onClick={() => setMode(m.key)}
                className={cx(
                  'flex h-7 items-center gap-1 rounded-[8px] px-2.5 text-[12px] transition-colors duration-200 ease-apple',
                  mode === m.key ? 'bg-card text-ink' : 'text-ink2 hover:text-ink',
                )}
              >
                {m.label}
                <span className="gf-num text-[10px] text-ink3">{m.count}</span>
              </button>
            ))}
          </div>
          <span className="text-[11px] text-ink3">{current.hint}</span>
          <div className="ml-auto flex items-center gap-2 text-[11px] text-ink3">
            <span>今日学习 <span className="gf-num text-ink">3 小时 12 分</span></span>
            <span>连续 <span className="gf-num text-ink">23</span> 天</span>
          </div>
        </div>
      </Card>

      {mode === 'quiz' ? <QuizPanel /> : null}
      {mode === 'recite' ? <RecitePanel /> : null}
      {mode === 'exam' ? <ExamPanel /> : null}
      {mode === 'wrong' ? <WrongPanel /> : null}
    </div>
  );
}
