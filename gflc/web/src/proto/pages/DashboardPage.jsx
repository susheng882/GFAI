import React from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRightIcon,
  UploadIcon,
  SparkIcon,
  TargetIcon,
  FlameIcon,
  PlayIcon,
  NotesIcon,
  BanksIcon,
  VideoIcon,
} from '../NavIcons.jsx';
import { Badge, Btn, Card, Divider, Kpi, Progress, SectionTitle, cx } from '../ui.jsx';
import {
  aiUsage,
  dashboardKpis,
  deckDistribution,
  deckDistributionTotal,
  heatmap,
  heatmapSummary,
  profile,
  quickUploads,
  recentLearnings,
  studyEntries,
  systemInfo,
  weeklyGoal,
} from '../mock/index.js';

const KIND_TONE = { video: 'brand', note: 'neutral', bank: 'ok' };
const KIND_ICON = { video: VideoIcon, note: NotesIcon, bank: BanksIcon };

/** 热力格：level 0–4 → 单色蓝阶（无渐变、无发光） */
const HEAT_CLASS = ['bg-sel', 'bg-[#DCE9FB]', 'bg-[#BFD8F7]', 'bg-[#7FB1EE]', 'bg-brand'];

/** 柱高：固定 10 档，避免内联 style */
const BAR_H = [
  'h-[8px]',
  'h-[12px]',
  'h-[16px]',
  'h-[20px]',
  'h-[24px]',
  'h-[28px]',
  'h-[32px]',
  'h-[38px]',
  'h-[43px]',
  'h-[48px]',
];

const WEEK_DAYS = ['一', '二', '三', '四', '五', '六', '日'];

function DashboardPage() {
  const goalPct = Math.round((weeklyGoal.done / weeklyGoal.total) * 100);
  const avgMastery = Math.round(
    deckDistribution.reduce((s, d) => s + d.mastery * d.cards, 0) / deckDistributionTotal,
  );
  const aiMax = Math.max(...aiUsage.days.map((d) => d.value));

  return (
    <div className="flex animate-fade-up flex-col gap-2.5">
      {/* ① 指标带 + 周目标条 */}
      <Card>
        <div className="grid grid-cols-2 gap-y-3 sm:grid-cols-4">
          {dashboardKpis.map((k, idx) => (
            <div key={k.key} className={cx('min-w-0', idx > 0 && 'sm:border-l sm:border-line sm:pl-5')}>
              <Kpi label={k.label} value={k.value} unit={k.unit} hint={k.hint} tone={k.tone} />
            </div>
          ))}
        </div>
        <Divider className="my-1.5" />
        <div className="flex flex-wrap items-center gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="text-[12px] leading-[17px] text-ink2">
                {weeklyGoal.label}
                <span className="gf-num ml-1.5 text-[13px] font-medium text-ink">{weeklyGoal.done}</span>
                <span className="gf-num text-[11px] text-ink3">
                  {' '}
                  / {weeklyGoal.total} {weeklyGoal.unit}
                </span>
              </p>
              <p className="text-[11px] leading-[16px] text-ink3">
                {weeklyGoal.range} · 剩 {weeklyGoal.daysLeft} 天，日均还需 {weeklyGoal.perDayLeft}{' '}
                {weeklyGoal.unit}
              </p>
            </div>
            <Progress value={goalPct} className="mt-1" tone="brand" />
          </div>
          <Badge tone={goalPct >= 60 ? 'ok' : 'warn'} dot>
            {goalPct}% 达成
          </Badge>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-2.5 lg:grid-cols-12">
        {/* ② 最近学习 */}
        <Card className="lg:col-span-7">
          <SectionTitle
            title="最近学习"
            sub="视频 / 笔记 / 题库动态"
            action={
              <Link to="/plans" className="text-[11px] text-ink3 hover:text-ink">
                全部记录
              </Link>
            }
          />
          <ul className="flex flex-col">
            {recentLearnings.map((r, idx) => {
              const Icon = KIND_ICON[r.kind] || NotesIcon;
              return (
                <li key={r.id} className={cx('border-line', idx > 0 && 'border-t')}>
                  <Link
                    to={r.to}
                    className="flex h-[34px] items-center gap-3 rounded-[8px] px-1 transition-colors duration-200 ease-apple hover:bg-page"
                  >
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-[6px] bg-page text-ink2">
                      <Icon size={12} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[12px] leading-[16px] text-ink">{r.title}</p>
                      <p className="truncate text-[10px] leading-[13px] text-ink3">{r.meta}</p>
                    </div>
                    <Badge tone={KIND_TONE[r.kind] || 'neutral'}>{r.kindLabel}</Badge>
                    <div className="hidden w-[56px] shrink-0 sm:block">
                      <Progress
                        value={r.progress}
                        height="h-1"
                        tone={r.progress >= 100 ? 'ok' : r.progress === 0 ? 'ink' : 'brand'}
                      />
                    </div>
                    <span className="w-[58px] shrink-0 text-right text-[10px] leading-[13px] text-ink3">
                      {r.time}
                    </span>
                    <ArrowRightIcon size={12} className="shrink-0 text-ink3" />
                  </Link>
                </li>
              );
            })}
          </ul>
        </Card>

        {/* ③ 卡片分布 */}
        <Card className="lg:col-span-5">
          <SectionTitle
            title="卡片分布"
            sub={`共 ${deckDistributionTotal.toLocaleString('en-US')} 张 · 平均掌握 ${avgMastery}%`}
            action={
              <Link to="/deck" className="text-[11px] text-ink3 hover:text-ink">
                卡包
              </Link>
            }
          />
          <div className="flex flex-col gap-2">
            {deckDistribution.map((d) => (
              <div key={d.label} className="flex flex-col gap-1.5">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-[12px] leading-[17px] text-ink2">{d.label}</span>
                  <span className="gf-num shrink-0 text-[10px] leading-[13px] text-ink3">
                    {d.cards} 张 · {d.mastery}%
                  </span>
                </div>
                <Progress value={d.mastery} tone={d.tone} height="h-1" />
              </div>
            ))}
          </div>
        </Card>

        {/* ④ 学习热力图（含刷题 / 背诵入口） */}
        <Card className="lg:col-span-7">
          <SectionTitle
            title="学习热力图"
            sub={`近 ${heatmapSummary.weeks} 周 · 活跃 ${heatmapSummary.activeDays} 天 · 日均 ${heatmapSummary.avgPerDay} 分钟 · 累计 ${heatmapSummary.totalMinutes} 分钟`}
            action={<Badge tone="line" dot>12 周记录</Badge>}
          />
          <div className="flex flex-wrap items-start gap-4">
            <div className="min-w-0">
              <div className="flex gap-1.5">
                <div className="flex flex-col gap-1 pr-0.5">
                  {WEEK_DAYS.map((d, i) => (
                    <span
                      key={d}
                      className="flex h-[11px] items-center text-[10px] leading-[11px] text-ink3"
                    >
                      {i % 2 === 1 ? d : ''}
                    </span>
                  ))}
                </div>
                <div className="grid grid-flow-col grid-rows-7 gap-[3px]">
                  {heatmap.map((w) =>
                    w.cells.map((c) => (
                      <span
                        key={`${w.week}-${c.d}`}
                        title={`第 ${w.week + 1} 周 · 周${WEEK_DAYS[c.d]} · ${c.minutes} 分钟`}
                        className={cx(
                          'h-[11px] w-[11px] rounded-[3px] transition-colors duration-200 ease-apple',
                          HEAT_CLASS[c.level],
                        )}
                      />
                    )),
                  )}
                </div>
              </div>
              <div className="mt-1.5 flex items-center gap-1">
                <span className="text-[10px] leading-[13px] text-ink3">少</span>
                {HEAT_CLASS.map((cls, i) => (
                  <span
                    key={cls}
                    title={heatmapSummary.legend[i]}
                    className={cx('h-[9px] w-[9px] rounded-[2px]', cls)}
                  />
                ))}
                <span className="ml-0.5 text-[10px] leading-[13px] text-ink3">多</span>
              </div>
            </div>

            <div className="flex min-w-[210px] flex-1 flex-col gap-2">
              {studyEntries.map((s) => (
                <div
                  key={s.key}
                  className="flex items-center gap-2.5 rounded-[10px] border border-line bg-page px-2.5 py-1.5"
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[7px] bg-card text-ink2">
                    {s.key === 'quiz' ? <BanksIcon size={12} /> : <FlameIcon size={12} />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[12px] leading-[16px] text-ink">
                      {s.title}
                      <span className="gf-num ml-1 font-medium">{s.value}</span>
                      <span className="ml-0.5 text-[10px] text-ink3">{s.unit}</span>
                    </p>
                    <p className="truncate text-[10px] leading-[13px] text-ink3">{s.hint}</p>
                  </div>
                  <Link to={s.to} className="gf-btn gf-btn-line h-7 shrink-0 px-2.5 text-[11px]">
                    去{s.title}
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* ⑤ 快速上传 */}
        <Card className="lg:col-span-5">
          <SectionTitle
            title="快速上传"
            sub="今日已解析 3 份 · 队列剩 3 个任务"
            action={<Btn variant="ghost" size="xs" icon={<UploadIcon size={12} />}>上传</Btn>}
          />
          <div className="flex flex-col divide-y divide-line">
            {quickUploads.map((q) => (
              <button
                key={q.key}
                type="button"
                className="flex items-center gap-2.5 py-1.5 text-left transition-colors duration-200 ease-apple first:pt-0 last:pb-0 hover:bg-page"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[7px] bg-page text-ink2">
                  {q.key === 'video' ? <PlayIcon size={12} /> : <UploadIcon size={12} />}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[12px] leading-[16px] text-ink">{q.title}</p>
                  <p className="truncate text-[10px] leading-[13px] text-ink3">
                    {q.sub} · {q.hint}
                  </p>
                </div>
                <ArrowRightIcon size={12} className="shrink-0 text-ink3" />
              </button>
            ))}
          </div>
        </Card>

        {/* ⑥ 系统信息 */}
        <Card className="lg:col-span-6">
          <SectionTitle
            title="系统信息"
            sub={`${profile.exam} · 距考试 ${profile.daysLeft} 天 · ${systemInfo.updatedAt}`}
            action={
              <Badge tone={systemInfo.status.tone} dot>
                {systemInfo.status.text}
              </Badge>
            }
          />
          <dl className="flex flex-col">
            {systemInfo.rows.map((row, idx) => (
              <div
                key={row.label}
                className={cx(
                  'flex items-center justify-between gap-3 py-1.5',
                  idx > 0 && 'border-t border-line',
                )}
              >
                <dt className="text-[12px] leading-[17px] text-ink2">{row.label}</dt>
                <dd className="gf-num text-[12px] leading-[17px] text-ink">{row.value}</dd>
              </div>
            ))}
          </dl>
        </Card>

        {/* ⑦ AI 用量 */}
        <Card className="lg:col-span-6">
          <SectionTitle
            title="AI 用量"
            sub={`近 7 天 ${aiUsage.weekTotal} ${aiUsage.unit} · ${aiUsage.tokenLabel} · 解析/生成/问答合计`}
            action={
              <Badge tone="brand">
                今日 {aiUsage.today} {aiUsage.unit}
              </Badge>
            }
          />
          <div className="flex items-end gap-2.5">
            {aiUsage.days.map((d, idx) => {
              const hIdx = Math.round((d.value / aiMax) * (BAR_H.length - 1));
              const isToday = idx === aiUsage.days.length - 1;
              return (
                <div key={d.date} className="flex min-w-0 flex-1 flex-col items-center gap-1">
                  <span className="gf-num text-[10px] leading-[13px] text-ink3">{d.value}</span>
                  <div className="flex h-[48px] w-full items-end justify-center">
                    <span
                      className={cx(
                        'w-full rounded-[3px] transition-colors duration-200 ease-apple',
                        isToday ? 'bg-brand' : 'bg-[#BFD8F7]',
                        BAR_H[hIdx],
                      )}
                      title={`${d.date} · ${d.value} ${aiUsage.unit}`}
                    />
                  </div>
                  <span
                    className={cx('text-[10px] leading-[13px]', isToday ? 'text-ink' : 'text-ink3')}
                  >
                    {d.label}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="mt-2 flex items-center justify-between gap-2">
            <p className="flex items-center gap-1.5 text-[10px] leading-[13px] text-ink3">
              <SparkIcon size={11} className="shrink-0" />
              今日 {aiUsage.today} 次，接近本周日均
            </p>
            <Link to="/settings" className="text-[11px] text-ink3 hover:text-ink">
              用量设置
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}

export default DashboardPage;
