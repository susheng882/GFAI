import React, { useMemo, useState } from 'react';
import { Badge, Btn, Card, Divider, Kpi, Progress, SectionTitle, cx } from '../ui.jsx';
import { CheckIcon, FlameIcon, TasksIcon } from '../NavIcons.jsx';
import { taskCleanup, taskRows, taskStats, taskSummary } from '../mock/index.js';

const STATUS = {
  running: { label: '进行中', tone: 'brand', prog: 'brand' },
  queued: { label: '排队中', tone: 'neutral', prog: 'ink' },
  success: { label: '成功', tone: 'ok', prog: 'ok' },
  failed: { label: '失败', tone: 'bad', prog: 'bad' },
  canceled: { label: '已放弃', tone: 'line', prog: 'ink' },
};

const COLS = 'grid-cols-[88px_minmax(0,1fr)_76px_132px_96px_196px_88px]';

const SUBJECT_TONE = {
  OS: 'bg-brandSoft text-brand',
  CN: 'bg-[#EEF3FF] text-[#2A5BD7]',
  CO: 'bg-[#F3EEFF] text-[#6B46C1]',
  DS: 'bg-[#EAF8EE] text-[#248A3D]',
  数学: 'bg-[#FFF4E5] text-[#B26A00]',
  英语: 'bg-[#FDECEC] text-[#C4322B]',
  政治: 'bg-sel text-ink2',
};

export default function TasksPage() {
  const [rows, setRows] = useState(() => taskRows.map((r) => ({ ...r })));
  const [cleaned, setCleaned] = useState(false);

  const counts = useMemo(() => {
    const base = { running: 0, queued: 0, success: 0, failed: 0, canceled: 0 };
    rows.forEach((r) => {
      base[r.status] = (base[r.status] || 0) + 1;
    });
    return base;
  }, [rows]);

  const liveValue = {
    running: counts.running,
    queued: counts.queued,
    done: taskSummary.todayDone + counts.success - taskRows.filter((r) => r.status === 'success').length,
    failed: counts.failed,
    avg: taskSummary.avgTime,
  };

  const cancel = (id) =>
    setRows((prev) =>
      prev.map((r) =>
        r.id === id && (r.status === 'running' || r.status === 'queued')
          ? { ...r, status: 'canceled', progress: r.progress, elapsed: '已手动放弃', note: '已从队列移除' }
          : r,
      ),
    );

  const retry = (id) =>
    setRows((prev) =>
      prev.map((r) =>
        r.id === id && (r.status === 'failed' || r.status === 'canceled')
          ? { ...r, status: 'queued', progress: 0, elapsed: '刚刚入队', error: '', note: '排队第 1 位' }
          : r,
      ),
    );

  return (
    <div className="flex animate-fade-up flex-col gap-2.5">
      <Card>
        <SectionTitle
          title="任务中心"
          sub={`后台解析与生成任务 · 并发 ${taskSummary.concurrency} · 队列 ${taskSummary.queue} · 保留期 ${taskSummary.retentionDays} 天`}
          action={
            <>
              <Badge tone="brand" dot>
                运行中 {counts.running}
              </Badge>
              <Badge tone="neutral">排队 {counts.queued}</Badge>
              <Btn variant="line" size="xs" icon={<TasksIcon size={12} />}>
                任务日志
              </Btn>
            </>
          }
        />
        <div className="grid grid-cols-5 gap-3">
          {taskStats.map((s) => (
            <Kpi
              key={s.id}
              label={s.label}
              value={liveValue[s.id] ?? s.value}
              unit={s.unit}
              hint={s.hint}
              tone={s.tone}
              className={cx('rounded-[10px] border border-line px-3 py-2')}
            />
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle
          title="后台任务"
          sub="最近 24 小时 · 共 9 条 · 点击「放弃」「重试」可直接调整队列"
          action={
            <>
              <Badge tone="ok">今日成功 {taskSummary.todayDone}</Badge>
              <Badge tone="bad">失败 {counts.failed}</Badge>
            </>
          }
        />
        <div className={cx('grid items-center gap-2 border-b border-line pb-1.5', COLS)}>
          <span className="text-[10px] leading-[14px] text-ink3">类型</span>
          <span className="text-[10px] leading-[14px] text-ink3">任务对象</span>
          <span className="text-[10px] leading-[14px] text-ink3">状态</span>
          <span className="text-[10px] leading-[14px] text-ink3">进度</span>
          <span className="text-[10px] leading-[14px] text-ink3">耗时</span>
          <span className="text-[10px] leading-[14px] text-ink3">错误（已脱敏）</span>
          <span className="text-right text-[10px] leading-[14px] text-ink3">操作</span>
        </div>

        <div className="flex flex-col">
          {rows.map((r, i) => {
            const meta = STATUS[r.status] || STATUS.queued;
            const busy = r.status === 'running' || r.status === 'queued';
            const retryable = r.status === 'failed' || r.status === 'canceled';
            return (
              <div
                key={r.id}
                className={cx('grid items-center gap-2 py-1', i > 0 && 'border-t border-line', COLS)}
              >
                <div className="flex min-w-0 items-center gap-1.5">
                  <span
                    className={cx(
                      'flex h-4 w-4 shrink-0 items-center justify-center rounded-[5px] text-[10px] font-medium leading-none',
                      SUBJECT_TONE[r.subject] || 'bg-sel text-ink2',
                    )}
                  >
                    {r.type === '资料解析' ? '析' : r.type === '生成卡片' ? '卡' : r.type === '模拟卷' ? '卷' : '视'}
                  </span>
                  <span className="truncate text-[11px] leading-[16px] text-ink2">{r.type}</span>
                </div>
                <span className="truncate text-[12px] leading-[17px] text-ink" title={r.target}>
                  {r.target}
                </span>
                <Badge tone={meta.tone} dot={r.status === 'running'}>
                  {meta.label}
                </Badge>
                <div className="flex items-center gap-2">
                  <Progress value={r.progress} tone={meta.prog} height="h-1" className="flex-1" />
                  <span className="gf-num w-[26px] shrink-0 text-right text-[10px] leading-[14px] text-ink3">
                    {r.progress}%
                  </span>
                </div>
                <span className="gf-num truncate text-[10px] leading-[14px] text-ink3">{r.elapsed}</span>
                <span
                  className={cx(
                    'truncate text-[10px] leading-[14px]',
                    r.error ? 'text-[#C4322B]' : 'text-ink3',
                  )}
                  title={r.error || r.note}
                >
                  {r.error || r.note}
                </span>
                <div className="flex items-center justify-end gap-1">
                  {busy ? (
                    <Btn variant="ghost" size="xs" onClick={() => cancel(r.id)}>
                      放弃
                    </Btn>
                  ) : null}
                  {retryable ? (
                    <Btn variant="ghost" size="xs" onClick={() => retry(r.id)}>
                      重试
                    </Btn>
                  ) : null}
                  {!busy && !retryable ? (
                    <span className="flex items-center gap-0.5 text-[10px] leading-[14px] text-ink3">
                      <CheckIcon size={11} />
                      完成
                    </span>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <SectionTitle
          title="清理与维护"
          sub={`保留期 ${taskSummary.retentionDays} 天 · 上次清理 ${taskSummary.lastCleanup}`}
          action={
            <>
              {cleaned ? <Badge tone="ok">已清理 {taskSummary.oldFailed} 条</Badge> : null}
              <Btn variant="solid" size="xs" onClick={() => setCleaned(true)}>
                清理旧失败
              </Btn>
            </>
          }
        />
        <div className="grid grid-cols-3 gap-2">
          {taskCleanup.map((c) => (
            <div key={c.id} className="rounded-[10px] border border-line px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-[12px] leading-[17px] text-ink">{c.label}</span>
                <span className="gf-num shrink-0 text-[11px] leading-[16px] text-ink2">
                  {cleaned && c.id !== 'cf-3' ? '0 条' : c.count}
                </span>
              </div>
              <p className="mt-1 truncate text-[10px] leading-[14px] text-ink3">{c.hint}</p>
            </div>
          ))}
        </div>
        <Divider className="my-2.5" />
        <div className="flex items-center gap-2 text-[11px] leading-[16px] text-ink3">
          <FlameIcon size={12} />
          <span className="truncate">
            清理只删除任务记录与日志，不影响已生成的资料笔记、卡片与题目；失败任务重试仍可在 7 天内进行。
          </span>
        </div>
      </Card>
    </div>
  );
}
