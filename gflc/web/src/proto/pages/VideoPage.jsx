import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Badge, Btn, Card, Divider, Progress, SectionTitle, cx } from '../ui.jsx';
import {
  ArrowRightIcon,
  ChevronDownIcon,
  NotesIcon,
  PlayIcon,
  SparkIcon,
  UploadIcon,
  VideoIcon,
} from '../NavIcons.jsx';
import {
  videoFigures,
  videoList,
  videoMeta,
  videoNotes,
  videoOutline,
  videoQA,
  videoSources,
  videoSummary,
  videoTabs,
  videoTimeline,
  videoTranscript,
} from '../mock/index.js';

const STATUS_TONE = {
  已完成: 'ok',
  解析中: 'brand',
  待解析: 'neutral',
  解析失败: 'bad',
};

export default function VideoPage() {
  const navigate = useNavigate();
  const [active, setActive] = useState('v1');
  const [tab, setTab] = useState('summary');
  const [outlineId, setOutlineId] = useState('o3');

  const gotoNotes = () => navigate('/notes');

  return (
    <div className="flex h-[calc(100vh-96px)] min-h-[620px] animate-fade-up items-stretch gap-2.5">
      {/* 左：视频列表 */}
      <div className="flex w-[238px] shrink-0 flex-col gap-2.5">
        <Card pad={false} className="flex flex-none flex-col overflow-hidden">
          <div className="px-3 pt-3">
            <SectionTitle
              title="视频库"
              sub={`${videoList.length} 个视频 · 1 个解析中`}
              action={
                <Btn variant="solid" size="xs" icon={<UploadIcon size={11} />}>
                  批量导入
                </Btn>
              }
            />
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-2 pb-2">
            {videoList.map((v) => {
              const on = v.id === active;
              return (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => setActive(v.id)}
                  className={cx(
                    'flex flex-col items-start gap-1 rounded-[10px] px-2 py-1.5 text-left transition-colors duration-150 ease-apple',
                    on ? 'bg-sel' : 'hover:bg-sel/60',
                  )}
                >
                  <span className="flex w-full items-center gap-1.5">
                    <span className={cx('shrink-0', on ? 'text-brand' : 'text-ink3')}>
                      <VideoIcon size={11} />
                    </span>
                    <span
                      className={cx(
                        'min-w-0 flex-1 truncate text-[12px] leading-[17px]',
                        on ? 'text-ink' : 'text-ink2',
                      )}
                    >
                      {v.title}
                    </span>
                  </span>
                  <span className="flex w-full items-center gap-1.5">
                    <Badge tone={STATUS_TONE[v.status]} dot>
                      {v.status}
                    </Badge>
                    <span className="gf-num shrink-0 text-[10px] leading-[14px] text-ink3">{v.duration}</span>
                    <span className="ml-auto shrink-0 text-[10px] leading-[14px] text-ink3">{v.progress}%</span>
                  </span>
                </button>
              );
            })}
          </div>
        </Card>

        <Card>
          <SectionTitle title="解析概览" sub="最近 7 个视频" />
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="min-w-0 flex-1 truncate text-[11px] leading-[16px] text-ink2">已完成解析</span>
              <span className="gf-num shrink-0 text-[11px] leading-[16px] text-ink">4</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="min-w-0 flex-1 truncate text-[11px] leading-[16px] text-ink2">解析中</span>
              <span className="gf-num shrink-0 text-[11px] leading-[16px] text-ink">1</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="min-w-0 flex-1 truncate text-[11px] leading-[16px] text-ink2">待解析 / 失败</span>
              <span className="gf-num shrink-0 text-[11px] leading-[16px] text-ink">1 / 1</span>
            </div>
          </div>
          <Divider className="my-2" />
          <p className="text-[10px] leading-[15px] text-ink3">
            批量导入支持 mp4 / mkv，单文件 ≤ 4 GB；解析完成后自动生成摘要、大纲、转写与配图。
          </p>
        </Card>
      </div>

      {/* 中：播放器 + 时间轴配图带 */}
      <div className="flex min-w-0 flex-1 flex-col gap-2.5">
        <Card pad={false} className="flex-none overflow-hidden">
          <div className="relative flex h-[312px] flex-col justify-between bg-ink px-4 py-3">
            <div className="flex items-start gap-2">
              <span className="min-w-0 flex-1 truncate text-[12px] leading-[17px] text-white/85">
                {videoMeta.title}
              </span>
              <span className="shrink-0 rounded-full bg-white/10 px-2 py-0.5 text-[10px] leading-[14px] text-white/70">
                {videoMeta.resolution}
              </span>
            </div>
            <div className="flex flex-1 flex-col items-center justify-center gap-2">
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-white">
                <PlayIcon size={18} />
              </span>
              <span className="text-[12px] leading-[17px] text-white/75">播放器占位 · 点击开始播放</span>
              <span className="text-[10px] leading-[14px] text-white/45">
                本地播放 · 不发起外部请求
              </span>
            </div>
            <div className="flex items-center gap-2 text-[10px] leading-[14px] text-white/55">
              <span className="shrink-0">{videoMeta.chapter}</span>
              <span className="shrink-0">·</span>
              <span className="truncate">{videoMeta.source}</span>
              <span className="ml-auto shrink-0">{videoMeta.subtitle}</span>
            </div>
          </div>

          <div className="px-4 py-2.5">
            <Progress value={videoMeta.progress} height="h-1" />
            <div className="mt-2 flex items-center gap-2">
              <span className="gf-num shrink-0 text-[11px] leading-[16px] text-ink">{videoMeta.watched}</span>
              <span className="shrink-0 text-[10px] leading-[14px] text-ink3">/</span>
              <span className="gf-num shrink-0 text-[10px] leading-[14px] text-ink3">{videoMeta.duration}</span>
              <span className="ml-2 shrink-0 text-[10px] leading-[14px] text-ink3">已看 {videoMeta.progress}%</span>
              <div className="ml-auto flex shrink-0 items-center gap-1.5">
                <Badge tone="neutral">0.5x</Badge>
                <Badge tone="brand">1.0x</Badge>
                <Badge tone="neutral">1.5x</Badge>
                <Badge tone="neutral">字幕 中文自动</Badge>
                <Btn variant="ghost" size="xs" icon={<ChevronDownIcon size={11} />}>
                  更多
                </Btn>
              </div>
            </div>
          </div>
        </Card>

        <Card pad={false} className="flex flex-none flex-col overflow-hidden">
          <div className="px-4 pt-3">
            <SectionTitle
              title="时间轴配图带"
              sub="标记为解析出的配图，点击跳转到对应笔记"
              action={<Badge tone="brand">{videoFigures.length} 张配图</Badge>}
            />
          </div>
          <div className="flex items-end gap-1 px-4">
            {videoTimeline.map((t, i) => {
              const show = i % 3 === 0 || i === videoTimeline.length - 1;
              return (
                <div key={`${t}-${i}`} className="flex min-w-0 flex-1 flex-col items-start">
                  <span className={cx('h-2 w-px', show ? 'bg-ink3' : 'bg-line2')} />
                  <span
                    className={cx(
                      'gf-num mt-0.5 w-full truncate text-[10px] leading-[13px]',
                      show ? 'text-ink3' : 'text-transparent',
                    )}
                  >
                    {i === videoTimeline.length - 1 ? '01:48' : t}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex gap-1.5 px-4 pb-2 pt-1.5">
            {videoFigures.map((f, i) => (
              <button
                key={f.id}
                type="button"
                onClick={gotoNotes}
                title={`${f.t} ${f.note} · 点击打开笔记`}
                className="group flex h-[104px] min-w-0 flex-1 flex-col justify-between rounded-[10px] border border-line bg-brandSoft px-1.5 py-1.5 text-left transition-colors duration-150 ease-apple hover:border-brand"
              >
                <span className="flex w-full items-center gap-1">
                  <span className="shrink-0 text-brand">
                    <NotesIcon size={10} />
                  </span>
                  <span className="gf-num shrink-0 text-[10px] leading-[13px] text-brand">图{i + 1}</span>
                </span>
                <span className="flex w-full flex-col">
                  <span className="w-full text-[10px] leading-[14px] font-medium text-ink">{f.title}</span>
                  <span className="gf-num mt-0.5 w-full truncate text-[10px] leading-[13px] text-ink3">{f.t}</span>
                </span>
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 border-t border-line px-4 py-2">
            <span className="min-w-0 flex-1 truncate text-[10px] leading-[14px] text-ink3">
              配图由转写内容自动对齐时间戳生成，点击任一配图可打开笔记页查看图文对照。
            </span>
            <Btn variant="line" size="xs" icon={<ArrowRightIcon size={11} />} onClick={gotoNotes}>
              全部配图笔记
            </Btn>
          </div>
        </Card>

        <Card className="flex-none">
          <SectionTitle title="继续学习" sub="由本节内容自动关联" />
          <div className="flex flex-col gap-1">
            {[
              { k: '资料', v: '《数据结构》第7章 图.pdf', to: '/docs' },
              { k: '卡包', v: '图论 · 最短路径 12 张', to: '/deck' },
              { k: '复习', v: '最短路径专项 8 题', to: '/review' },
            ].map((r) => (
              <button
                key={r.k}
                type="button"
                onClick={() => navigate(r.to)}
                className="flex items-center gap-2 rounded-[10px] px-2 py-1 text-left transition-colors duration-150 ease-apple hover:bg-sel/60"
              >
                <span className="w-[26px] shrink-0 text-[10px] leading-[14px] text-ink3">{r.k}</span>
                <span className="min-w-0 flex-1 truncate text-[11px] leading-[16px] text-ink2">{r.v}</span>
                <span className="shrink-0 text-ink3">
                  <ArrowRightIcon size={11} />
                </span>
              </button>
            ))}
          </div>
        </Card>
      </div>

      {/* 右：Tab */}
      <Card pad={false} className="flex w-[352px] shrink-0 flex-col overflow-hidden">
        <div className="grid grid-cols-4 gap-1 px-3 pt-3">
          {videoTabs.map((t) => {
            const on = t.id === tab;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={cx(
                  'rounded-[10px] border px-1 py-1.5 text-center text-[11px] leading-[16px] transition-colors duration-150 ease-apple',
                  on
                    ? 'border-brand bg-brandSoft font-medium text-brand'
                    : 'border-line bg-card text-ink2 hover:bg-sel/60',
                )}
              >
                {t.label}
              </button>
            );
          })}
        </div>

        <div className="mt-2 flex min-h-0 flex-1 flex-col overflow-y-auto px-3 pb-3">
          {tab === 'summary' ? (
            <div className="flex flex-col gap-2">
              <p className="text-[12px] leading-[19px] text-ink2">{videoSummary.text}</p>
              <Divider />
              <div className="flex flex-col gap-1">
                <span className="text-[11px] leading-[16px] font-medium text-ink">要点</span>
                {videoSummary.points.map((p) => (
                  <div key={p} className="flex items-start gap-1.5">
                    <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-line2" />
                    <span className="min-w-0 text-[11px] leading-[16px] text-ink2">{p}</span>
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-1">
                {videoSummary.keywords.map((k) => (
                  <Badge key={k} tone="line">
                    {k}
                  </Badge>
                ))}
              </div>
              <Divider />
              <div className="flex items-center gap-2">
                {[
                  { k: '段落', v: videoOutline.length },
                  { k: '配图', v: videoFigures.length },
                  { k: '笔记', v: videoNotes.length },
                ].map((st) => (
                  <div key={st.k} className="flex min-w-0 flex-1 flex-col rounded-[10px] bg-page px-2 py-1.5">
                    <span className="gf-num text-[15px] leading-[20px] font-medium text-ink">{st.v}</span>
                    <span className="text-[10px] leading-[14px] text-ink3">{st.k}</span>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-1.5 text-[10px] leading-[14px] text-ink3">
                <SparkIcon size={10} />
                <span className="min-w-0 truncate">摘要由转写内容生成 · 可点击大纲逐段对照</span>
              </div>
            </div>
          ) : null}

          {tab === 'outline' ? (
            <div className="flex flex-col gap-0.5">
              {videoOutline.map((o) => {
                const on = o.id === outlineId;
                return (
                  <button
                    key={o.id}
                    type="button"
                    onClick={() => setOutlineId(o.id)}
                    className={cx(
                      'flex items-center gap-1.5 rounded-[10px] py-1.5 pr-2 text-left transition-colors duration-150 ease-apple',
                      o.level === 2 ? 'pl-4' : 'pl-2',
                      on ? 'bg-sel' : 'hover:bg-sel/60',
                    )}
                  >
                    <span className="gf-num w-[42px] shrink-0 text-[10px] leading-[14px] text-ink3">{o.t}</span>
                    <span
                      className={cx(
                        'min-w-0 flex-1 truncate text-[11px] leading-[16px]',
                        on ? 'text-ink' : 'text-ink2',
                      )}
                    >
                      {o.level === 2 ? '· ' : ''}
                      {o.title}
                    </span>
                    <span className="shrink-0 text-[10px] leading-[14px] text-ink3">{o.dur}</span>
                  </button>
                );
              })}
              <div className="mt-1.5 flex items-center gap-2 rounded-[10px] bg-page px-2 py-1.5">
                <span className="min-w-0 flex-1 truncate text-[10px] leading-[14px] text-ink2">
                  共 {videoOutline.length} 个段落 · 已生成笔记 {videoNotes.length} 条
                </span>
                <Btn variant="line" size="xs" onClick={gotoNotes}>
                  查看笔记
                </Btn>
              </div>
            </div>
          ) : null}

          {tab === 'qa' ? (
            <div className="flex flex-col gap-2">
              {videoQA.map((qa) => (
                <div key={qa.id} className="rounded-[10px] border border-line bg-card px-2 py-1.5">
                  <span className="flex items-start gap-1.5">
                    <span className="mt-[2px] shrink-0 text-[10px] leading-[14px] font-medium text-brand">Q</span>
                    <span className="min-w-0 text-[11px] leading-[16px] font-medium text-ink">{qa.q}</span>
                  </span>
                  <span className="mt-1 flex items-start gap-1.5">
                    <span className="mt-[2px] shrink-0 text-[10px] leading-[14px] font-medium text-ink3">A</span>
                    <span className="min-w-0 text-[11px] leading-[16px] text-ink2">{qa.a}</span>
                  </span>
                </div>
              ))}
              <Btn variant="line" size="xs" icon={<ArrowRightIcon size={11} />} onClick={() => navigate('/qa')}>
                继续在问答页追问
              </Btn>
            </div>
          ) : null}

          {tab === 'figures' || tab === 'pics' ? (
            <div className="flex flex-col gap-1.5">
              {videoFigures.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={gotoNotes}
                  className="flex items-start gap-2 rounded-[10px] border border-line bg-card px-2 py-1.5 text-left transition-colors duration-150 ease-apple hover:border-brand hover:bg-brandSoft/40"
                >
                  <span className="flex h-8 w-11 shrink-0 items-center justify-center rounded-[8px] bg-page text-ink3">
                    <NotesIcon size={12} />
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="w-full truncate text-[11px] leading-[16px] font-medium text-ink">{f.title}</span>
                    <span className="w-full truncate text-[10px] leading-[14px] text-ink3">
                      {f.t} · {f.note}
                    </span>
                  </span>
                  <span className="mt-0.5 shrink-0 text-ink3">
                    <ArrowRightIcon size={11} />
                  </span>
                </button>
              ))}
              <p className="text-[10px] leading-[14px] text-ink3">
                点击任一配图可跳转到笔记页，定位到对应时间戳的图文笔记。
              </p>
            </div>
          ) : null}

          {tab === 'source' ? (
            <div className="flex flex-col gap-1.5">
              {videoSources.map((s) => (
                <div key={s.id} className="flex items-center gap-2">
                  <span className="w-[64px] shrink-0 text-[10px] leading-[14px] text-ink3">{s.label}</span>
                  <span className="min-w-0 flex-1 truncate text-[11px] leading-[16px] text-ink2">{s.value}</span>
                </div>
              ))}
              <Divider />
              <div className="flex items-center gap-1.5">
                <Badge tone="ok" dot>
                  解析完成
                </Badge>
                <Badge tone="neutral">{videoMeta.size}</Badge>
                <Btn variant="line" size="xs" className="ml-auto">
                  重新解析
                </Btn>
              </div>
            </div>
          ) : null}

          {tab === 'transcript' ? (
            <div className="flex flex-col gap-1.5">
              {videoTranscript.map((r) => (
                <div key={r.id} className="flex items-start gap-1.5">
                  <span className="gf-num mt-[1px] w-[38px] shrink-0 text-[10px] leading-[15px] text-ink3">{r.t}</span>
                  <span className="min-w-0 text-[11px] leading-[16px] text-ink2">{r.text}</span>
                </div>
              ))}
            </div>
          ) : null}

          {tab === 'notes' ? (
            <div className="flex flex-col gap-1.5">
              {videoNotes.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  onClick={gotoNotes}
                  className="flex flex-col items-start gap-0.5 rounded-[10px] border border-line bg-card px-2 py-1.5 text-left transition-colors duration-150 ease-apple hover:border-brand hover:bg-brandSoft/40"
                >
                  <span className="flex w-full items-center gap-1.5">
                    <span className="gf-num shrink-0 text-[10px] leading-[14px] text-brand">{n.t}</span>
                    <span className="min-w-0 flex-1 truncate text-[11px] leading-[16px] font-medium text-ink">{n.title}</span>
                  </span>
                  <span className="w-full text-[11px] leading-[16px] text-ink2">{n.text}</span>
                </button>
              ))}
              <Btn variant="line" size="xs" onClick={gotoNotes}>
                打开笔记页
              </Btn>
            </div>
          ) : null}
        </div>
      </Card>
    </div>
  );
}
