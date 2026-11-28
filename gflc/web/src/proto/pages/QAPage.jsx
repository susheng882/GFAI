import React, { useEffect, useRef, useState } from 'react';
import { Badge, Btn, Card, Divider, SectionTitle, cx } from '../ui.jsx';
import { ArrowRightIcon, PlusIcon, QaIcon, SparkIcon } from '../NavIcons.jsx';
import { qaAnswer, qaHints, qaSessions, qaStrategies, recommendedQuestions } from '../mock/index.js';

const FULL = qaAnswer.blocks.join('\n\n');

function AnswerBody({ text }) {
  const parts = text.split('\n\n').filter((p) => p.length > 0);
  return (
    <div className="flex flex-col gap-2">
      {parts.map((part, i) => {
        const lines = part.split('\n');
        if (lines.length > 1 && lines[0].startsWith('- ')) {
          return (
            <ul key={i} className="flex flex-col gap-1">
              {lines.map((line, j) => (
                <li key={j} className="flex items-start gap-1.5">
                  <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-line2" />
                  <span className="min-w-0 text-[12px] leading-[19px] text-ink2">
                    {line.replace(/^-\s*/, '')}
                  </span>
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={i} className="text-[12px] leading-[19px] text-ink2">
            {part}
          </p>
        );
      })}
    </div>
  );
}

export default function QAPage() {
  const [strategy, setStrategy] = useState('smart');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [ai, setAi] = useState(null);
  const [session, setSession] = useState('qs-1');
  const timerRef = useRef(null);
  const bodyRef = useRef(null);

  useEffect(
    () => () => {
      if (timerRef.current) clearInterval(timerRef.current);
    },
    [],
  );

  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [ai, messages]);

  const running = ai !== null && !ai.done;

  const send = (preset) => {
    const q = (typeof preset === 'string' ? preset : input).trim();
    if (!q || running) return;
    setMessages((prev) => [...prev, { id: `u-${prev.length}`, role: 'user', text: q }]);
    setInput('');
    setAi({ text: '', stageIdx: 0, done: false });
    const t0 = Date.now();
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      const el = Date.now() - t0;
      const stageIdx = el > 1600 ? 3 : el > 1000 ? 2 : el > 450 ? 1 : 0;
      const len = Math.max(0, Math.min(FULL.length, Math.floor((el - 1600) / 4)));
      if (len >= FULL.length) {
        clearInterval(timerRef.current);
        timerRef.current = null;
        setAi({ text: FULL, stageIdx: 3, done: true });
        return;
      }
      setAi({ text: FULL.slice(0, len), stageIdx, done: false });
    }, 50);
  };

  const activeStrategy = qaStrategies.find((s) => s.id === strategy) || qaStrategies[0];

  return (
    <div className="flex animate-fade-up items-start gap-2.5">
      <div className="flex min-w-0 flex-1 flex-col gap-2.5">
        <Card>
          <SectionTitle
            title="问答"
            sub="选择检索策略后提问 · 回答会标注资料与联网来源"
            action={<Badge tone={activeStrategy.isDefault ? 'brand' : 'neutral'}>{activeStrategy.hint}</Badge>}
          />
          <div className="grid grid-cols-5 gap-2">
            {qaStrategies.map((s) => {
              const on = s.id === strategy;
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setStrategy(s.id)}
                  className={cx(
                    'flex flex-col items-start gap-0.5 rounded-[10px] border px-2.5 py-2 text-left transition-colors duration-150 ease-apple',
                    on
                      ? 'border-brand bg-brandSoft'
                      : 'border-line bg-card hover:bg-sel/60',
                  )}
                >
                  <span
                    className={cx(
                      'text-[12px] leading-[17px] font-medium',
                      on ? 'text-brand' : 'text-ink',
                    )}
                  >
                    {s.label}
                  </span>
                  <span className="w-full truncate text-[10px] leading-[14px] text-ink3">
                    {s.desc}
                  </span>
                </button>
              );
            })}
          </div>
        </Card>

        <Card pad={false} className="flex min-h-[480px] flex-1 flex-col overflow-hidden">
          <div className="flex items-center gap-2 border-b border-line px-4 py-2.5">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[8px] bg-brandSoft text-brand">
              <QaIcon size={13} />
            </span>
            <span className="min-w-0 truncate text-[13px] leading-[18px] font-medium text-ink">
              死锁的四个必要条件与检测避免的区别
            </span>
            <Badge tone="neutral">{activeStrategy.label}</Badge>
            <span className="ml-auto shrink-0 text-[10px] leading-[14px] text-ink3">
              本轮 {messages.length + (ai ? 1 : 0)} 条 · 上下文 4 轮
            </span>
          </div>

          <div ref={bodyRef} className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
            {messages.length === 0 && !ai ? (
              <div className="flex h-full flex-col gap-4">
                <div className="flex flex-col items-center gap-1.5 pt-3 text-center">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brandSoft text-brand">
                    <SparkIcon size={16} />
                  </span>
                  <p className="text-[13px] leading-[18px] text-ink">问点什么，比如「死锁的四个必要条件」</p>
                  <p className="text-[11px] leading-[16px] text-ink3">
                    当前策略：{activeStrategy.label} · {activeStrategy.desc}
                  </p>
                </div>

                <div>
                  <p className="mb-2 text-[11px] font-medium text-ink3">推荐问题</p>
                  <div className="grid grid-cols-2 gap-1.5">
                    {recommendedQuestions.map((rq) => (
                      <button
                        key={rq.id}
                        type="button"
                        onClick={() => send(rq.text)}
                        className="flex flex-col items-start gap-1.5 rounded-[10px] border border-line bg-card px-2.5 py-2 text-left transition-colors duration-150 ease-apple hover:bg-page"
                      >
                        <Badge tone="neutral">{rq.topic}</Badge>
                        <span className="text-[12px] leading-[17px] text-ink2">{rq.text}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="min-h-0 flex-1">
                  <p className="mb-1.5 text-[11px] font-medium text-ink3">最近会话</p>
                  <ul className="flex flex-col gap-0.5">
                    {qaSessions.slice(0, 4).map((s) => (
                      <li key={s.id} className="flex items-center gap-2 rounded-[8px] px-2 py-1.5 hover:bg-page">
                        <span className="min-w-0 flex-1 truncate text-[12px] leading-[17px] text-ink2">{s.title}</span>
                        <span className="shrink-0 text-[10px] text-ink3">{s.strategy}</span>
                        <span className="shrink-0 text-[10px] text-ink3">{s.time}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}

            <div className="flex flex-col gap-3">
              {messages.map((m) => (
                <div key={m.id} className="flex justify-end">
                  <div className="max-w-[520px] rounded-[10px] bg-sel px-3 py-2">
                    <p className="text-[12px] leading-[19px] text-ink">{m.text}</p>
                  </div>
                </div>
              ))}

              {ai ? (
                <div className="flex gap-2">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brandSoft text-brand">
                    <SparkIcon size={13} />
                  </span>
                  <div className="min-w-0 flex-1 rounded-[10px] border border-line bg-card px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] leading-[16px] font-medium text-ink">GFLC 助手</span>
                      <Badge tone="brand">{activeStrategy.label}</Badge>
                      <span className="gf-num ml-auto shrink-0 text-[10px] leading-[14px] text-ink3">
                        {ai.done ? `耗时 ${qaAnswer.total}` : '生成中…'}
                      </span>
                    </div>

                    <div className="mt-2 flex flex-col gap-1 rounded-[8px] bg-page px-2 py-1.5">
                      {qaAnswer.stages.map((st, i) => {
                        const state = ai.stageIdx > i ? 'done' : ai.stageIdx === i ? 'doing' : 'wait';
                        return (
                          <div key={st.id} className="flex items-center gap-1.5">
                            <span
                              className={cx(
                                'flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[10px] leading-none',
                                state === 'done'
                                  ? 'border-ok bg-[#EAF8EE] text-[#248A3D]'
                                  : state === 'doing'
                                    ? 'border-brand bg-brandSoft text-brand'
                                    : 'border-line2 bg-card text-ink3',
                              )}
                            >
                              {state === 'done' ? '✓' : state === 'doing' ? '·' : i + 1}
                            </span>
                            <span
                              className={cx(
                                'shrink-0 text-[10px] leading-[14px]',
                                state === 'wait' ? 'text-ink3' : 'text-ink2',
                              )}
                            >
                              {st.label}
                            </span>
                            <span className="min-w-0 flex-1 truncate text-[10px] leading-[14px] text-ink3">
                              {state === 'wait' ? '等待中' : st.detail}
                            </span>
                            <span className="gf-num shrink-0 text-[10px] leading-[14px] text-ink3">
                              {(st.ms / 1000).toFixed(1)}s
                            </span>
                          </div>
                        );
                      })}
                    </div>

                    <div className="mt-2">
                      {ai.text ? (
                        <AnswerBody text={ai.text} />
                      ) : (
                        <p className="text-[12px] leading-[19px] text-ink3">正在检索资料并组织回答…</p>
                      )}
                    </div>

                    {ai.done ? (
                      <>
                        <Divider className="my-2" />
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-[10px] leading-[14px] text-ink3">来源</span>
                          {qaAnswer.sources.map((s) => (
                            <span
                              key={s.id}
                              title={s.meta}
                              className={cx(
                                'inline-flex max-w-[220px] items-center gap-1 rounded-full border px-2 py-0.5',
                                s.kind === 'web'
                                  ? 'border-line bg-page text-ink2'
                                  : 'border-line bg-card text-ink2',
                              )}
                            >
                              <span className="shrink-0 text-[10px] leading-none text-ink3">
                                {s.kind === 'web' ? '网' : '料'}
                              </span>
                              <span className="truncate text-[10px] leading-[14px]">{s.title}</span>
                            </span>
                          ))}
                        </div>

                        <div className="mt-2 flex flex-wrap items-center gap-1.5">
                          <span className="text-[10px] leading-[14px] text-ink3">追问</span>
                          {qaAnswer.followups.map((f) => (
                            <Btn
                              key={f}
                              variant="line"
                              size="xs"
                              onClick={() => setInput(f)}
                              icon={<ArrowRightIcon size={11} />}
                            >
                              {f}
                            </Btn>
                          ))}
                        </div>
                      </>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </div>
          </div>

          <div className="border-t border-line px-4 py-2.5">
            <div className="flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') send();
                }}
                placeholder="问点什么… 例如：死锁的四个必要条件是什么？检测和避免有什么区别？"
                className="gf-input h-9 flex-1 text-[12px]"
              />
              <Btn variant="solid" size="sm" onClick={send} disabled={running}>
                {running ? '生成中' : '发送'}
              </Btn>
            </div>
            <div className="mt-1.5 flex items-center gap-2 text-[10px] leading-[14px] text-ink3">
              <span className="truncate">
                策略：{activeStrategy.label} · 回答只用于复习参考，不作为考试结论
              </span>
              <span className="ml-auto shrink-0">Enter 发送 · Shift+Enter 换行</span>
            </div>
          </div>
        </Card>
      </div>

      <div className="flex w-[268px] shrink-0 flex-col gap-2.5">
        <Card>
          <SectionTitle
            title="历史会话"
            sub={`共 ${qaSessions.length} 个会话`}
            action={
              <Btn variant="ghost" size="xs" icon={<PlusIcon size={11} />}>
                新建
              </Btn>
            }
          />
          <div className="flex flex-col gap-0.5">
            {qaSessions.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => setSession(s.id)}
                className={cx(
                  'flex flex-col items-start gap-0.5 rounded-[10px] px-2 py-1.5 text-left transition-colors duration-150 ease-apple',
                  s.id === session ? 'bg-sel' : 'hover:bg-sel/60',
                )}
              >
                <span
                  className={cx(
                    'w-full truncate text-[12px] leading-[17px]',
                    s.id === session ? 'text-ink' : 'text-ink2',
                  )}
                >
                  {s.title}
                </span>
                <span className="flex w-full items-center gap-1.5 text-[10px] leading-[14px] text-ink3">
                  <span className="shrink-0">{s.strategy}</span>
                  <span className="shrink-0">·</span>
                  <span className="shrink-0">{s.turns} 轮</span>
                  <span className="ml-auto shrink-0">{s.time}</span>
                </span>
              </button>
            ))}
          </div>
        </Card>

        <Card>
          <SectionTitle title="使用提示" sub="策略与来源说明" />
          <div className="flex flex-col gap-1.5">
            {qaHints.map((h) => (
              <div key={h.id} className="flex items-start gap-1.5">
                <span className="mt-[3px] shrink-0 text-ink3">
                  <SparkIcon size={11} />
                </span>
                <span className="min-w-0 text-[11px] leading-[16px] text-ink2">{h.text}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
