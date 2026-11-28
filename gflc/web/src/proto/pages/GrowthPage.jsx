import React from 'react';
import { Badge, Btn, Card, Divider, Kpi, Progress, SectionTitle, cx } from '../ui.jsx';
import { ArrowRightIcon, FlameIcon, GrowthIcon, TargetIcon } from '../NavIcons.jsx';
import {
  growthDims,
  growthLevel,
  growthMilestones,
  growthStats,
  growthTimeline,
} from '../mock/index.js';

const TONE_PROGRESS = { brand: 'brand', ok: 'ok', warn: 'warn', ink: 'ink' };

const STATE_BADGE = {
  done: { text: '已获得', tone: 'ok' },
  doing: { text: '进行中', tone: 'warn' },
  locked: { text: '未解锁', tone: 'neutral' },
};

const STATE_GLYPH = {
  done: 'bg-brandSoft text-brand',
  doing: 'bg-[#FFF4E5] text-[#B26A00]',
  locked: 'bg-sel text-ink3',
};

export default function GrowthPage() {
  const percent = Math.round((growthLevel.exp / growthLevel.nextExp) * 100);
  const diff = growthLevel.nextExp - growthLevel.exp;

  return (
    <div className="flex animate-fade-up flex-col gap-2.5">
      <div className="grid grid-cols-1 gap-2.5 xl:grid-cols-12">
        <Card className="xl:col-span-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[14px] bg-brandSoft text-brand">
              <GrowthIcon size={19} />
            </div>
            <div className="min-w-0">
              <p className="truncate text-[16px] leading-[22px] font-medium text-ink">
                Lv.{growthLevel.level} · {growthLevel.name}
              </p>
              <p className="truncate text-[11px] leading-[16px] text-ink3">
                距离「{growthLevel.next}」还差 {diff} exp
              </p>
            </div>
            <Badge tone="brand" className="ml-auto shrink-0">
              {growthLevel.rank}
            </Badge>
          </div>

          <div className="mt-3">
            <div className="flex items-baseline justify-between">
              <span className="gf-num text-[11px] leading-[16px] text-ink3">
                {growthLevel.exp} / {growthLevel.nextExp} exp
              </span>
              <span className="gf-num text-[11px] leading-[16px] text-ink3">{percent}%</span>
            </div>
            <Progress value={percent} tone="brand" height="h-1.5" className="mt-1.5" />
          </div>

          <Divider className="my-3" />

          <div className="grid grid-cols-3 gap-2">
            <Kpi label="学习天数" value={growthLevel.days} unit="天" />
            <Kpi label="连续打卡" value={growthLevel.streak} unit="天" tone="ok" />
            <Kpi label="今日获得" value={`+${growthLevel.todayExp}`} unit="exp" tone="brand" />
          </div>

          <Divider className="my-3" />

          <div className="flex items-center gap-2 text-[11px] leading-[16px] text-ink3">
            <FlameIcon size={12} />
            <span>
              累计学习 <span className="gf-num text-ink">{growthStats.totalHours}</span> 小时 · 本周{' '}
              <span className="gf-num text-ink">{growthStats.hours}</span> 小时
            </span>
            <Btn variant="ghost" size="xs" className="ml-auto" icon={<TargetIcon size={12} />}>
              设定目标
            </Btn>
          </div>
        </Card>

        <Card className="xl:col-span-7">
          <SectionTitle
            title="五维能力"
            sub="记忆 / 理解 / 输出 / 速度 / 稳定 · 每周一更新"
            action={<Badge tone="ok" dot>较上周 +6</Badge>}
          />
          <div className="flex flex-col gap-2">
            {growthDims.map((d) => (
              <div key={d.id} className="flex items-center gap-2.5">
                <span className="w-[28px] shrink-0 text-[12px] leading-[17px] text-ink2">
                  {d.label}
                </span>
                <Progress
                  value={d.value}
                  tone={TONE_PROGRESS[d.tone] || 'brand'}
                  height="h-2"
                  className="flex-1"
                />
                <span className="gf-num w-[26px] shrink-0 text-right text-[12px] leading-[17px] text-ink">
                  {d.value}
                </span>
                <span className="hidden w-[186px] shrink-0 truncate text-right text-[10px] leading-[14px] text-ink3 xl:block">
                  {d.hint}
                </span>
              </div>
            ))}
          </div>
          <Divider className="my-2.5" />
          <div className="flex items-center justify-between text-[11px] leading-[16px] text-ink3">
            <span>短板：稳定 61 · 建议保持每日固定时段复习</span>
            <Btn variant="line" size="xs" icon={<ArrowRightIcon size={12} />}>
              能力详情
            </Btn>
          </div>
        </Card>
      </div>

      <Card>
        <SectionTitle
          title="里程碑徽章"
          sub={`已获得 ${growthStats.badgesDone} / ${growthStats.badgesTotal} 枚 · 连续解锁可触发经验加成`}
          action={
            <>
              <Badge tone="neutral">已获得 {growthStats.badgesDone}</Badge>
              <Badge tone="warn">进行中 2</Badge>
              <Badge tone="line">未解锁 3</Badge>
            </>
          }
        />
        <div className="grid grid-cols-4 gap-2 md:grid-cols-7">
          {growthMilestones.map((m) => {
            const meta = STATE_BADGE[m.state] || STATE_BADGE.locked;
            return (
              <div
                key={m.id}
                className={cx(
                  'flex min-w-0 flex-col items-center gap-1 rounded-[10px] border px-1.5 py-2 text-center',
                  m.state === 'locked' ? 'border-line bg-page' : 'border-line bg-card',
                )}
              >
                <span
                  className={cx(
                    'flex h-9 w-9 items-center justify-center rounded-full text-[13px] font-medium',
                    STATE_GLYPH[m.state] || STATE_GLYPH.locked,
                  )}
                >
                  {m.glyph}
                </span>
                <span
                  className={cx(
                    'w-full truncate text-[11px] leading-[15px]',
                    m.state === 'locked' ? 'text-ink3' : 'text-ink',
                  )}
                >
                  {m.name}
                </span>
                <span className="w-full truncate text-[10px] leading-[14px] text-ink3">{m.note}</span>
                <Badge tone={meta.tone}>{meta.text}</Badge>
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <SectionTitle
          title="成长动态"
          sub="最近 5 条经验记录"
          action={
            <Btn variant="line" size="xs">
              全部记录
            </Btn>
          }
        />
        <div className="flex flex-col">
          {growthTimeline.map((t, i) => (
            <div
              key={t.id}
              className={cx('flex items-center gap-3 py-1', i > 0 && 'border-t border-line')}
            >
              <span className="gf-num w-[40px] shrink-0 text-[11px] leading-[16px] text-ink3">
                {t.date}
              </span>
              <span className="min-w-0 flex-1 truncate text-[12px] leading-[17px] text-ink2">
                {t.text}
              </span>
              <span className="gf-num shrink-0 text-[11px] leading-[16px] font-medium text-[#248A3D]">
                {t.delta} exp
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
