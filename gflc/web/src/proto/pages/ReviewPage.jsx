import React, { useState } from 'react';
import { Badge, Btn, Card, Divider, KeyCap, Progress, SectionTitle, cx } from '../ui.jsx';
import { CheckIcon, FlameIcon, PlusIcon, ReviewIcon, SparkIcon } from '../NavIcons.jsx';
import {
  reviewCard,
  reviewGrades,
  reviewQueue,
  reviewSnooze,
  reviewStats,
  reviewToday,
  upcomingReviews,
} from '../mock/index.js';

const GRADE_CLASS = {
  bad: 'text-[#C4322B] hover:bg-[#FDECEC]',
  warn: 'text-[#B26A00] hover:bg-[#FFF4E5]',
  brand: 'text-brand hover:bg-brandSoft',
  ok: 'text-[#248A3D] hover:bg-[#EAF8EE]',
};

const DOT_STATE = {
  done: 'bg-ok text-white',
  cur: 'bg-ink text-white',
  todo: 'bg-page text-ink3',
};

export default function ReviewPage() {
  const [flipped, setFlipped] = useState(false);
  const [graded, setGraded] = useState(null);
  const [snooze, setSnooze] = useState('tomorrow');
  const { items, done, total } = reviewQueue;
  const percent = Math.round((done / total) * 100);
  const maxUpcoming = Math.max(...upcomingReviews.days.map((d) => d.value));

  return (
    <div className="flex animate-fade-up flex-col gap-2.5">
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-brandSoft text-brand">
            <ReviewIcon size={15} />
          </div>
          <div className="min-w-0">
            <p className="text-[12px] leading-[17px] text-ink">
              今日复习 <span className="gf-num text-[13px] font-medium">{done} / {total}</span> 张
            </p>
            <p className="text-[11px] leading-[16px] text-ink3">按遗忘曲线排序 · 已用时 {reviewStats.minutes} 分钟</p>
          </div>
          <div className="flex w-[180px] shrink-0 items-center gap-2">
            <Progress value={percent} tone="brand" height="h-1.5" />
            <span className="gf-num text-[11px] text-ink3">{percent}%</span>
          </div>
          <span className="ml-auto flex items-center gap-2.5 text-[11px] text-ink3">
            <span>剩余 <span className="gf-num text-ink">{reviewStats.left}</span> 张</span>
            <span>记住率 <span className="gf-num text-ink">{reviewStats.recall}%</span></span>
            <span>连续 <span className="gf-num text-ink">{reviewStats.streak}</span> 天</span>
          </span>
          <div className="flex items-center gap-1.5">
            <Btn variant="line" size="sm" icon={<PlusIcon size={13} />}>加卡</Btn>
            <Btn variant="line" size="sm" icon={<CheckIcon size={13} />}>今日完成</Btn>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-12">
        <Card className="xl:col-span-8">
          <SectionTitle
            title={`第 ${done + 1} 张 · ${reviewCard.chapter}`}
            sub={`${reviewCard.interval} · 已复习 ${reviewCard.reviews} 次 · 遗忘 ${reviewCard.lapses} 次`}
            action={
              <>
                <Badge tone="brand" dot>{flipped ? '背面 · 答案' : '正面 · 问题'}</Badge>
                <Btn variant="line" size="xs">编辑</Btn>
                <Btn variant="line" size="xs">删除</Btn>
              </>
            }
          />

          <div className="rounded-[12px] border border-line bg-page px-3 py-2.5">
            <p className="text-[11px] leading-[16px] text-ink3">正面 · 问题</p>
            <p className="mt-1 text-[15px] font-medium leading-[23px] text-ink">{reviewCard.front}</p>
            <div className="mt-1.5 flex items-center gap-1">
              {reviewCard.tags.map((t) => (
                <Badge key={t} tone="neutral">{t}</Badge>
              ))}
              <span className="ml-auto text-[10px] text-ink3">{reviewCard.source}</span>
            </div>
          </div>

          {flipped ? (
            <div className="mt-2 rounded-[12px] border border-line bg-card px-3 py-2.5">
              <p className="text-[11px] leading-[16px] text-ink3">背面 · 整块知识点</p>
              <ul className="mt-1 flex flex-col gap-0.5">
                {reviewCard.back.map((line, i) => (
                  <li key={i} className="text-[11px] leading-[18px] text-ink">{line}</li>
                ))}
              </ul>
              <p className="mt-1.5 rounded-[8px] bg-[#FFF4E5] px-2 py-1 text-[10px] leading-[16px] text-[#B26A00]">
                {reviewCard.tip}
              </p>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setFlipped(true)}
              className="mt-2 flex h-[52px] w-full flex-col items-center justify-center gap-0.5 rounded-[12px] border border-dashed border-line2 bg-card text-ink2 transition-colors duration-200 ease-apple hover:bg-page"
            >
              <span className="flex items-center gap-1 text-[12px]">
                <SparkIcon size={13} /> 点击翻面查看整块知识点
              </span>
              <span className="text-[10px] text-ink3">先自述答案，再对照要点，最后评分</span>
            </button>
          )}

          <Divider className="my-2.5" />

          <div className="flex items-center gap-1.5">
            <span className="shrink-0 text-[11px] text-ink3">评分</span>
            {reviewGrades.map((g) => (
              <button
                key={g.key}
                type="button"
                onClick={() => setGraded(g.key)}
                className={cx(
                  'flex h-[38px] flex-1 flex-col items-center justify-center rounded-[10px] border transition-colors duration-200 ease-apple',
                  graded === g.key ? 'border-ink bg-sel' : 'border-line bg-card',
                  GRADE_CLASS[g.tone],
                )}
              >
                <span className="text-[12px] leading-[16px]">{g.label}</span>
                <span className="text-[10px] leading-[14px] text-ink3">{g.hint}</span>
              </button>
            ))}
          </div>

          <div className="mt-2 flex items-center gap-1.5">
            <span className="shrink-0 text-[11px] text-ink3">延后</span>
            {reviewSnooze.map((s) => (
              <button
                key={s.key}
                type="button"
                onClick={() => setSnooze(s.key)}
                className={cx(
                  'h-6 rounded-[7px] px-2 text-[10px] transition-colors duration-200 ease-apple',
                  snooze === s.key ? 'bg-ink text-white' : 'bg-page text-ink2 hover:text-ink',
                )}
              >
                {s.label}
              </button>
            ))}
            <span className="ml-auto text-[10px] text-ink3">
              {graded ? `已评分：${reviewGrades.find((g) => g.key === graded).label}` : '未评分'} · 快捷键
              <KeyCap className="ml-1">1</KeyCap>
              <KeyCap className="ml-1">2</KeyCap>
              <KeyCap className="ml-1">3</KeyCap>
              <KeyCap className="ml-1">4</KeyCap>
            </span>
          </div>
        </Card>

        <div className="flex flex-col gap-2.5 xl:col-span-4">
          <Card>
            <SectionTitle
              title="今日队列"
              sub="12 张 · 已完成 3 张"
              action={<Badge tone="ok" dot>进行中</Badge>}
            />
            <div className="grid grid-cols-6 gap-1.5">
              {items.map((it) => (
                <div
                  key={it.n}
                  className={cx(
                    'flex h-[26px] items-center justify-center rounded-[7px] text-[11px] tabular-nums',
                    DOT_STATE[it.state],
                  )}
                >
                  {it.n}
                </div>
              ))}
            </div>
            <div className="mt-2 flex items-center justify-between text-[10px] text-ink3">
              <span className="flex items-center gap-2">
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-[2px] bg-ok" />已完成</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-[2px] bg-ink" />当前</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-[2px] bg-sel" />待复习</span>
              </span>
              <span>预计 {reviewStats.left * 4} 分钟</span>
            </div>
          </Card>

          <Card>
            <SectionTitle title="今日统计" action={<Badge tone="line">实时</Badge>} />
            <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-ink3">今日到期</span>
                <span className="gf-num text-ink">{reviewStats.due}</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-ink3">已复习</span>
                <span className="gf-num text-ink">{reviewStats.done}</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-ink3">平均用时</span>
                <span className="text-ink">{reviewStats.avgPerCard}</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-ink3">记住率</span>
                <span className="gf-num text-[#248A3D]">{reviewStats.recall}%</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-ink3">明日到期</span>
                <span className="gf-num text-ink">{reviewStats.tomorrow}</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="flex items-center gap-1 text-ink3"><FlameIcon size={11} />连续</span>
                <span className="gf-num text-ink">{reviewStats.streak} 天</span>
              </div>
            </div>
          </Card>

          <Card>
            <SectionTitle title="今日已复习" sub="点击可回看" />
            <ul>
              <li className="grid grid-cols-[38px_minmax(0,1fr)_40px] items-center gap-1.5 border-b border-line pb-1 text-[10px] text-ink3">
                <span className="gf-num">时间</span>
                <span>卡片</span>
                <span className="text-right">评分</span>
              </li>
              {reviewToday.map((r) => (
                <li
                  key={r.id}
                  className="grid h-[26px] grid-cols-[38px_minmax(0,1fr)_40px] items-center gap-1.5 border-b border-line last:border-b-0 hover:bg-page"
                >
                  <span className="gf-num text-[10px] text-ink3">{r.time}</span>
                  <span className="truncate text-[11px] text-ink">{r.front}</span>
                  <span className="text-right text-[10px] text-ink3">{r.grade}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <SectionTitle
              title="记忆曲线预告"
              sub="未来 7 天到期"
              action={<Badge tone="line">按遗忘曲线排期</Badge>}
            />
            <div className="flex h-[96px] items-end gap-2">
              {upcomingReviews.days.map((d) => {
                const h = Math.round((d.value / maxUpcoming) * 72);
                return (
                  <div key={d.key} className="flex min-w-0 flex-1 flex-col items-center gap-1">
                    <span className="gf-num text-[10px] text-ink2">{d.value}</span>
                    <div
                      className={cx(
                        'w-full rounded-[6px] transition-colors duration-200 ease-apple',
                        d.key === 'd0' ? 'bg-brand' : 'bg-brand/35',
                      )}
                      style={{ height: `${h}px` }}
                    />
                    <span className="text-[10px] text-ink3">{d.label}</span>
                  </div>
                );
              })}
            </div>
            <div className="mt-2 flex items-center justify-between border-t border-line pt-2 text-[11px]">
              <span className="flex items-center gap-1.5 text-ink3">
                <span className="h-2 w-2 rounded-[3px] bg-brand" />今天
                <span className="h-2 w-2 rounded-[3px] bg-brand/35" />未来
              </span>
              <span className="text-ink3">
                未来 7 天到期 · 合计 <span className="gf-num text-ink">{upcomingReviews.total}</span> 张
              </span>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
