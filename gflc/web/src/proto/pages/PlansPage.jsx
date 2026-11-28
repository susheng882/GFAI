import React, { useMemo, useState } from 'react';
import { Badge, Btn, Card, Divider, Progress, SectionTitle, cx } from '../ui.jsx';
import {
  ArrowRightIcon,
  CheckIcon,
  FlameIcon,
  PlansIcon,
  PlusIcon,
  TargetIcon,
} from '../NavIcons.jsx';
import {
  planDay,
  planGoalBars,
  planHeader,
  planMonth,
  planStats,
  planTemplates,
  planTodayTasks,
  planWeek,
} from '../mock/index.js';

const VIEWS = [
  { key: 'month', label: '月' },
  { key: 'week', label: '周' },
  { key: 'day', label: '日' },
];

const TONE_TEXT = {
  brand: 'text-brand',
  ok: 'text-[#248A3D]',
  warn: 'text-[#B26A00]',
  neutral: 'text-ink2',
  ink: 'text-ink',
};

const TONE_BAR = {
  brand: 'border-l-brand',
  ok: 'border-l-ok',
  warn: 'border-l-warn',
  neutral: 'border-l-line2',
  ink: 'border-l-ink',
};

const TONE_PROGRESS = {
  brand: 'brand',
  ok: 'ok',
  warn: 'warn',
  ink: 'ink',
  neutral: 'brand',
};

function MonthCell({ cell }) {
  const load = Math.min(3, cell.tasks);
  return (
    <div
      className={cx(
        'flex h-[46px] flex-col justify-between rounded-[8px] border px-1.5 py-1',
        cell.today
          ? 'border-brand bg-brandSoft'
          : cell.out
            ? 'border-line bg-page'
            : 'border-line bg-card',
      )}
    >
      <div className="flex items-baseline justify-between gap-1">
        <span
          className={cx(
            'gf-num text-[11px] leading-[15px]',
            cell.out ? 'text-ink3' : cell.today ? 'font-medium text-brand' : 'text-ink',
          )}
        >
          {cell.d}
        </span>
        <span className="truncate text-[10px] leading-[14px] text-ink3">
          {cell.out ? '—' : cell.tasks === 0 ? '休息' : `${cell.tasks} 项`}
        </span>
      </div>
      <div className="flex items-end gap-0.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className={cx(
              'h-[6px] w-[3px] rounded-full',
              i < load ? 'bg-brand' : cell.out ? 'bg-line' : 'bg-sel',
            )}
          />
        ))}
      </div>
    </div>
  );
}

function MonthView() {
  return (
    <div className="flex flex-col gap-1">
      <div className="grid grid-cols-7 gap-1">
        {planMonth.weekdays.map((w) => (
          <div key={w} className="text-center text-[10px] leading-[14px] text-ink3">
            {w}
          </div>
        ))}
      </div>
      {planMonth.weeks.map((wk) => (
        <div key={wk.key} className="grid grid-cols-7 gap-1">
          {wk.days.map((cell) => (
            <MonthCell key={`${wk.key}-${cell.m}-${cell.d}`} cell={cell} />
          ))}
        </div>
      ))}
    </div>
  );
}

function WeekView() {
  return (
    <div className="grid grid-cols-7 gap-1">
      {planWeek.days.map((day) => (
        <div key={day.key} className="flex min-w-0 flex-col gap-1">
          <div
            className={cx(
              'rounded-[8px] px-1 py-1 text-center',
              day.today ? 'bg-brandSoft text-brand' : 'bg-page text-ink2',
            )}
          >
            <p className="text-[11px] leading-[15px]">{day.label}</p>
            <p className="gf-num text-[10px] leading-[14px] opacity-80">{day.date}</p>
          </div>
          {day.blocks.map((b) => (
            <div
              key={b.id}
              className={cx(
                'rounded-[8px] border border-l-2 border-line bg-card px-1.5 py-1',
                TONE_BAR[b.tone] || TONE_BAR.neutral,
              )}
            >
              <p className="gf-num truncate text-[10px] leading-[14px] text-ink3">{b.time}</p>
              <p className="truncate text-[11px] leading-[15px] text-ink">{b.title}</p>
              <p
                className={cx(
                  'truncate text-[10px] leading-[14px]',
                  TONE_TEXT[b.tone] || TONE_TEXT.neutral,
                )}
              >
                {b.subject}
              </p>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function DayView() {
  return (
    <div className="flex flex-col gap-1">
      {planDay.blocks.map((b) => (
        <div
          key={b.id}
          className={cx(
            'flex items-center gap-2.5 rounded-[8px] border border-l-2 border-line bg-card px-2.5 py-1',
            TONE_BAR[b.tone] || TONE_BAR.neutral,
          )}
        >
          <div className="w-[76px] shrink-0">
            <p className="gf-num text-[11px] leading-[15px] text-ink">
              {b.start} - {b.end}
            </p>
            <p className={cx('truncate text-[10px] leading-[14px]', TONE_TEXT[b.tone] || TONE_TEXT.neutral)}>
              {b.subject}
            </p>
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[12px] leading-[17px] text-ink">{b.title}</p>
            <p className="truncate text-[10px] leading-[14px] text-ink3">{b.book}</p>
          </div>
          <Badge tone={b.done ? 'ok' : 'line'}>{b.done ? '已完成' : '待开始'}</Badge>
        </div>
      ))}
    </div>
  );
}

export default function PlansPage() {
  const [view, setView] = useState('month');
  const [doneMap, setDoneMap] = useState(() =>
    planTodayTasks.reduce((acc, t) => ({ ...acc, [t.id]: t.done }), {}),
  );

  const doneCount = useMemo(
    () => Object.values(doneMap).filter(Boolean).length,
    [doneMap],
  );

  const toggle = (id) => setDoneMap((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <div className="flex animate-fade-up flex-col gap-2.5">
      <Card>
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-brandSoft text-brand">
            <PlansIcon size={15} />
          </div>
          <div className="min-w-0">
            <p className="truncate text-[13px] leading-[18px] text-ink">{planHeader.week}</p>
            <p className="truncate text-[11px] leading-[16px] text-ink3">{planHeader.focus}</p>
          </div>
          <div className="flex w-[196px] shrink-0 items-center gap-2">
            <Progress value={planHeader.percent} tone="brand" height="h-1.5" />
            <span className="gf-num shrink-0 text-[11px] text-ink3">{planHeader.percent}%</span>
          </div>
          <span className="flex items-center gap-2.5 text-[11px] text-ink3">
            <span>
              已完成 <span className="gf-num text-ink">{planHeader.done}</span> / {planHeader.total}
            </span>
            <span>
              剩余 <span className="gf-num text-ink">{planHeader.daysLeft}</span> 天
            </span>
            <span className="flex items-center gap-1">
              <FlameIcon size={12} />
              连续 <span className="gf-num text-ink">{planStats.streak}</span> 天
            </span>
          </span>
          <div className="ml-auto flex shrink-0 items-center gap-1.5">
            <Btn variant="line" size="sm" icon={<TargetIcon size={13} />}>
              调整目标
            </Btn>
            <Btn variant="solid" size="sm" icon={<PlusIcon size={13} />}>
              新建计划
            </Btn>
          </div>
        </div>

        <Divider className="my-2.5" />

        <div className="grid grid-cols-2 gap-2.5 xl:grid-cols-4">
          {planGoalBars.map((g) => {
            const pct = Math.round((g.value / g.total) * 100);
            return (
              <div key={g.id} className="min-w-0 rounded-[10px] border border-line bg-card px-2.5 py-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-[12px] leading-[17px] text-ink">{g.label}</span>
                  <span className="gf-num shrink-0 text-[11px] text-ink3">
                    {g.value}/{g.total}
                  </span>
                </div>
                <Progress
                  value={pct}
                  tone={TONE_PROGRESS[g.tone] || 'brand'}
                  height="h-1"
                  className="mt-1.5"
                />
                <p className="mt-1 truncate text-[10px] leading-[14px] text-ink3">{g.detail}</p>
              </div>
            );
          })}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-12">
        <Card className="xl:col-span-8">
          <SectionTitle
            title="学习日历"
            sub={
              view === 'month'
                ? `${planMonth.label} · 本月完成 ${planStats.monthDone} / ${planStats.monthTotal} 个任务`
                : view === 'week'
                  ? `${planWeek.label} · 本周 7 天共 20 个任务块`
                  : `${planDay.label} · ${planDay.summary}`
            }
            action={
              <div className="flex items-center gap-1 rounded-[10px] bg-page p-0.5">
                {VIEWS.map((v) => (
                  <button
                    key={v.key}
                    type="button"
                    onClick={() => setView(v.key)}
                    aria-pressed={view === v.key}
                    className={cx(
                      'h-7 w-9 rounded-[8px] text-[11px] transition-colors duration-150 ease-apple',
                      view === v.key
                        ? 'bg-card font-medium text-ink'
                        : 'text-ink3 hover:text-ink',
                    )}
                  >
                    {v.label}
                  </button>
                ))}
              </div>
            }
          />
          <div className="min-h-[318px]">
            {view === 'month' ? <MonthView /> : null}
            {view === 'week' ? <WeekView /> : null}
            {view === 'day' ? <DayView /> : null}
          </div>
        </Card>

        <Card className="xl:col-span-4">
          <SectionTitle
            title="今日任务"
            sub={`${planStats.doneTasks} 个任务 · 已完成 ${doneCount} 个`}
            action={<Badge tone="brand" dot>打卡中</Badge>}
          />
          <div className="flex flex-col gap-1.5">
            {planTodayTasks.map((t) => {
              const done = Boolean(doneMap[t.id]);
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => toggle(t.id)}
                  className="flex w-full items-center gap-2 rounded-[10px] border border-line bg-card px-2 py-1.5 text-left transition-colors duration-150 ease-apple hover:bg-page"
                >
                  <span
                    className={cx(
                      'flex h-4 w-4 shrink-0 items-center justify-center rounded-[5px] border',
                      done ? 'border-ok bg-ok text-white' : 'border-line2 bg-card',
                    )}
                  >
                    {done ? <CheckIcon size={11} /> : null}
                  </span>
                  <span className="gf-num w-[34px] shrink-0 text-[11px] text-ink3">{t.time}</span>
                  <span
                    className={cx(
                      'min-w-0 flex-1 truncate text-[12px] leading-[17px]',
                      done ? 'text-ink3 line-through' : 'text-ink',
                    )}
                  >
                    {t.title}
                  </span>
                  <Badge tone="line">{t.subject}</Badge>
                  <span className="gf-num w-[34px] shrink-0 text-right text-[10px] text-ink3">
                    {t.minutes} 分
                  </span>
                </button>
              );
            })}
          </div>
          <Divider className="my-2.5" />
          <div className="flex items-center justify-between text-[11px] text-ink3">
            <span>
              今日专注 <span className="gf-num text-ink">{planStats.focusHours}</span> 小时
            </span>
            <Btn variant="ghost" size="xs" icon={<ArrowRightIcon size={12} />}>
              查看全部任务
            </Btn>
          </div>
        </Card>
      </div>

      <Card>
        <SectionTitle
          title="计划模板"
          sub="按目标一键生成每日任务，可再逐条调整"
          action={
            <Btn variant="line" size="xs">
              全部模板
            </Btn>
          }
        />
        <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2 xl:grid-cols-4">
          {planTemplates.map((t) => (
            <div key={t.id} className="rounded-[10px] border border-line bg-card px-3 py-2.5">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-[12px] leading-[17px] font-medium text-ink">
                  {t.name}
                </span>
                <Badge tone={t.tone === 'ink' ? 'neutral' : t.tone}>{t.tag}</Badge>
              </div>
              <p className="mt-1 truncate text-[10px] leading-[14px] text-ink3">{t.detail}</p>
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="gf-num truncate text-[10px] text-ink3">
                  {t.days} 天 · {t.tasks} 个任务
                </span>
                <Btn variant="line" size="xs">
                  套用
                </Btn>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
