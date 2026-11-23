import React, { useCallback, useEffect, useRef, useState } from 'react';
import { App as AntdApp, Button, Input, InputNumber, Progress, Segmented, Select, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import { api, runTask } from '../api.js';
import { esc, pct } from '../utils.js';
import { isTypingTarget, useTodayQueue } from '../hooks.js';
import EmptyState from '../components/EmptyState.jsx';
import Markdown from '../components/Markdown.jsx';

const TEST_TYPES = [
  { value: 'all', label: '全部题型' },
  { value: 'single', label: '单选题' },
  { value: 'multiple', label: '多选题' },
  { value: 'fill', label: '填空题' },
];

/* 今日队列条（B5）：复习 + 新学 = 今日，数字等宽，荧光笔只标「今日」一个数字。 */
function QueueBar() {
  const q = useTodayQueue();
  return (
    <div className="queue-bar" style={{ marginBottom: 12 }}>
      <div className="queue-bar-b">
        <span>复习 <span className="mono">{q.review}</span></span>
        <span className="queue-op">+</span>
        <span>新学 <span className="mono">{q.fresh}</span></span>
        <span className="queue-op">=</span>
        <span>今日 <b className="hl mono">{q.total}</b> 项</span>
      </div>
      {!q.total && !q.loading && <div className="queue-zero">今日暂无队列，挑一个卡包开始背诵</div>}
    </div>
  );
}

/* 学习页：刷题（推荐/随机/错题/章节）、背诵卡片、测试、错题本、题库导入。 */
export default function StudyPage() {
  const { message } = AntdApp.useApp();
  const navigate = useNavigate();
  const [mode, setMode] = useState('quiz');
  const [overview, setOverview] = useState(null);
  const [recommend, setRecommend] = useState(null);
  const [chapters, setChapters] = useState([]);
  const [wrong, setWrong] = useState([]);
  const [quiz, setQuiz] = useState(null);
  const [idx, setIdx] = useState(0);
  const [answer, setAnswer] = useState(null);
  const [selected, setSelected] = useState(null);
  const [reciteCards, setReciteCards] = useState([]);
  const [reciteIdx, setReciteIdx] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [count, setCount] = useState(5);
  const [decks, setDecks] = useState([]);
  const [stage, setStage] = useState('');
  const [testType, setTestType] = useState('all');
  const [test, setTest] = useState(null);
  const [testBusy, setTestBusy] = useState(false);
  const [testScore, setTestScore] = useState({ correct: 0, total: 0 });
  const qbRef = useRef(null);

  const load = useCallback(async () => {
    const [o, r, c, w, d] = await Promise.allSettled([
      api('/quiz/overview'), api('/quiz/recommend'), api('/quiz/chapters'),
      api('/quiz/wrong'), api('/decks'),
    ]);
    if (o.status === 'fulfilled') setOverview(o.value);
    if (r.status === 'fulfilled') setRecommend(r.value);
    if (c.status === 'fulfilled') setChapters(c.value || []);
    if (w.status === 'fulfilled') setWrong(w.value || []);
    if (d.status === 'fulfilled') setDecks(d.value || []);
  }, []);
  useEffect(() => { load(); }, [load]);

  const bankEmpty = overview != null && +overview.total === 0 && !chapters.length;
  const goImport = () => navigate('/docs');

  const startQuiz = async (payload) => {
    if (bankEmpty) { message.info('请先导入题库，再去资料页上传题目'); goImport(); return; }
    try {
      const qs = await api('/quiz/generate', { method: 'POST', body: JSON.stringify({ count, ...payload }) });
      if (!qs?.length) { message.info('没有符合条件的题目'); return; }
      setQuiz(qs); setIdx(0); setAnswer(null); setSelected(null); setMode('quiz');
    } catch (e) {
      message.info(e.message || '暂时无法出题，请先确认题库已导入');
    }
  };

  const submit = async () => {
    const q = quiz[idx];
    const ans = selected != null ? q.options[selected] : document.getElementById('fillAns')?.value;
    if (!ans) { message.warning('请选择或输入答案'); return; }
    try {
      const r = await api('/quiz/submit', { method: 'POST', body: JSON.stringify({ question_id: q.id, user_answer: ans }) });
      setAnswer(r);
    } catch (e) { message.info(e.message || '提交失败，请重试'); }
  };

  const openDeck = async (id) => {
    try {
      const cards = await api(`/decks/${id}/cards`) || [];
      if (!cards.length) { message.info('这个卡包还没有卡片'); return; }
      setReciteCards(cards); setReciteIdx(0); setRevealed(false); setMode('recite');
    } catch (e) { message.info(e.message || '暂时无法读取卡包'); }
  };

  /* B6：背诵态翻面后二元评分，背诵卡同为 Card，复用 POST /review/{id}；失败轻提示不红字。 */
  const reciteRate = (rating) => {
    const card = reciteCards[reciteIdx];
    if (!card) return;
    api(`/review/${card.id}`, { method: 'POST', body: JSON.stringify({ rating }) })
      .then(() => message.success(rating === 3 ? '已记住' : '已记录，稍后再练'))
      .catch(() => message.info('评分暂未保存，可继续学习'));
    if (reciteIdx >= reciteCards.length - 1) message.info('这一组已背完');
    else { setReciteIdx((i) => i + 1); setRevealed(false); }
  };

  /* B11 测试模式：题量/题型设定 → /quiz/generate；交卷逐题 /quiz/submit → 逐题回顾。
     题型由后端按 qtype 过滤，前端不再二次筛选；qtype 为空（全部题型）时不传该字段。 */
  const startTest = async () => {
    if (bankEmpty) { message.info('请先导入题库'); goImport(); return; }
    setTestBusy(true);
    try {
      const body = { count: Math.min(50, count), mode: 'new' };
      if (testType !== 'all') body.qtype = testType;
      const raw = await api('/quiz/generate', { method: 'POST', body: JSON.stringify(body) });
      const picked = (Array.isArray(raw) ? raw : []).slice(0, count);
      if (!picked.length) { message.info('没有符合条件的题目'); return; }
      setQuiz(null);
      setTest({ phase: 'paper', qs: picked, idx: 0, answers: {}, results: [] });
      setTestScore({ correct: 0, total: picked.length });
      setMode('test');
    } catch (e) { message.info(e.message || '暂时无法出题'); }
    finally { setTestBusy(false); }
  };

  const submitTest = async () => {
    setTestBusy(true);
    const results = [];
    let correct = 0;
    for (const q of test.qs) {
      const user = test.answers[q.id] || '';
      try {
        const r = await api('/quiz/submit', {
          method: 'POST', body: JSON.stringify({ question_id: q.id, user_answer: user }),
        });
        results.push({ q, user, ...r });
        if (r?.correct) correct++;
      } catch (e) { results.push({ q, user, error: e.message || '判分失败' }); }
    }
    setTestBusy(false);
    setTest({ ...test, phase: 'review', results, idx: 0 });
    setTestScore({ correct, total: test.qs.length });
    message.success('已交卷');
  };

  const uploadBank = async (file) => {
    if (!file) return;
    setStage('上传中…');
    try {
      const fd = new FormData(); fd.append('file', file);
      const r = await api('/questions/upload', { method: 'POST', body: fd });
      setStage('生成题库中…');
      const res = await runTask(`/questions/${r.document_id}/generate`, { method: 'POST' }, '生成题库');
      setStage(`已生成 ${res.questions || 0} 道题`);
      message.success('题库已生成'); await load();
    } catch (e) { setStage(e.message); message.info(e.message || '导入失败'); }
  };

  /* B9 背诵态快捷键：Space 翻面/下一张，← → 切卡，翻面后 1=再练一次 2=记住了；输入框聚焦不触发。 */
  useEffect(() => {
    if (mode !== 'recite' || !reciteCards.length) return undefined;
    const onKey = (e) => {
      if (isTypingTarget(e.target)) return;
      if (e.key === ' ') {
        e.preventDefault();
        if (!revealed) setRevealed(true);
        else if (reciteIdx < reciteCards.length - 1) { setReciteIdx((i) => i + 1); setRevealed(false); }
        return;
      }
      if (e.key === 'ArrowRight' && reciteIdx < reciteCards.length - 1) {
        e.preventDefault(); setReciteIdx((i) => i + 1); setRevealed(false); return;
      }
      if (e.key === 'ArrowLeft' && reciteIdx > 0) {
        e.preventDefault(); setReciteIdx((i) => i - 1); setRevealed(false); return;
      }
      if (revealed && e.key === '1') { e.preventDefault(); reciteRate(1); return; }
      if (revealed && e.key === '2') { e.preventDefault(); reciteRate(3); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mode, reciteCards, revealed, reciteIdx]);

  if (quiz) {
    if (idx >= quiz.length) {
      return (
        <div>
          <div className="v3-card" style={{ textAlign: 'center', padding: 36 }}>
            <div style={{ fontSize: 16, fontWeight: 500 }}>这一轮完成</div>
            <div className="muted" style={{ marginTop: 6 }}>共 {quiz.length} 题，去错题本回看答错的题。</div>
            <Button style={{ marginTop: 14 }} onClick={() => { setQuiz(null); load(); }}>再来一套</Button>
          </div>
          <h2 style={{ fontSize: 13, fontWeight: 500, margin: '20px 0 10px' }}>错题本</h2>
          <WrongList wrong={wrong} />
        </div>
      );
    }
    const q = quiz[idx];
    return (
      <div style={{ maxWidth: 760, margin: '0 auto' }}>
        <div className="row between" style={{ marginBottom: 12 }}>
          <span className="muted">第 {idx + 1} / {quiz.length} 题</span>
          <Button size="small" type="text" onClick={() => setQuiz(null)}>结束练习</Button>
        </div>
        <div className="v3-card">
          <div style={{ fontSize: 15, fontWeight: 500, lineHeight: 1.7, marginBottom: 14 }}>{esc(q.stem)}</div>
          {(q.options || []).map((o, i) => (
            <div key={i} onClick={() => !answer && setSelected(i)}
              style={{
                border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '9px 12px',
                marginBottom: 8, cursor: answer ? 'default' : 'pointer',
                background: answer && o === rAnswer(answer) ? 'var(--success-soft)'
                  : answer && i === selected ? 'var(--danger-soft)' : selected === i ? 'var(--accent)' : 'transparent',
              }}>
              <Tag>{String.fromCharCode(65 + i)}</Tag>{esc(o)}
            </div>
          ))}
          {!(q.options || []).length && <Input id="fillAns" placeholder="输入答案" disabled={!!answer} />}
          {!answer ? <div className="row" style={{ justifyContent: 'flex-end', marginTop: 14 }}>
            <Button type="primary" onClick={submit}>提交</Button>
          </div> : (
            <div style={{ marginTop: 14 }}>
              <div className="divider" />
              <div className="row" style={{ gap: 8 }}>
                <Tag color={answer.correct ? 'success' : 'error'}>{answer.correct ? '回答正确' : '回答错误'}</Tag>
                <span className="muted">正确答案：{esc(answer.answer)}</span>
              </div>
              {answer.analysis && (
                <div style={{ fontSize: 13, lineHeight: 1.8, marginTop: 10 }}>
                  <div><b>考点：</b>{esc(answer.analysis.point || '-')}</div>
                  <div><b>思路：</b>{esc(answer.analysis.approach || '-')}</div>
                  <div><b>步骤：</b>{(answer.analysis.steps || []).map(esc).join(' → ') || '-'}</div>
                  <div><b>易错点：</b>{(answer.analysis.pitfalls || []).map(esc).join('；') || '-'}</div>
                </div>
              )}
              <div className="row" style={{ justifyContent: 'flex-end', marginTop: 14 }}>
                <Button type="primary" onClick={() => { setIdx(idx + 1); setAnswer(null); setSelected(null); }}>下一题</Button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  /* ---------- B11 测试模式：交卷前不判分，交卷后统一评分 + 逐题回顾 ---------- */
  if (test) {
    if (test.phase === 'review') {
      const r = test.results[test.idx] || {};
      return (
        <div style={{ maxWidth: 760, margin: '0 auto' }}>
          <div className="v3-card test-score">
            <div className="lab">本次得分</div>
            <div className="big"><span className="hl mono">{testScore.correct}</span><small> / {testScore.total} 题</small></div>
            <div className="row" style={{ gap: 8, marginTop: 12 }}>
              <Button type="primary" onClick={startTest}>再测一套</Button>
              <Button onClick={() => setTest(null)}>返回学习</Button>
            </div>
          </div>
          <div className="v3-card" style={{ marginTop: 12 }}>
            <div className="v3-sh">逐题回顾<span className="meta mono">{test.idx + 1} / {test.results.length}</span></div>
            <div className="test-q">{esc(r.q?.stem)}</div>
            <div className="test-answers">
              <div>你的答案 <span className="mono">{esc(r.user || '未作答')}</span></div>
              <div>正确答案 <span className="mono">{esc(r.answer || '—')}</span></div>
              {r.correct != null && <Tag color={r.correct ? 'success' : 'error'}>{r.correct ? '正确' : '错误'}</Tag>}
            </div>
            {r.error && <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>{esc(r.error)}</div>}
            {r.analysis && (
              <div className="test-analysis">
                <div><b>考点：</b>{esc(r.analysis.point || '-')}</div>
                <div><b>思路：</b>{esc(r.analysis.approach || '-')}</div>
                <div><b>步骤：</b>{(r.analysis.steps || []).map(esc).join(' → ') || '-'}</div>
                <div><b>易错点：</b>{(r.analysis.pitfalls || []).map(esc).join('；') || '-'}</div>
              </div>
            )}
            <div className="row between" style={{ marginTop: 16 }}>
              <Button disabled={test.idx <= 0} onClick={() => setTest({ ...test, idx: test.idx - 1 })}>上一题</Button>
              <Button disabled={test.idx >= test.results.length - 1}
                onClick={() => setTest({ ...test, idx: test.idx + 1 })}>下一题</Button>
            </div>
          </div>
        </div>
      );
    }
    const q = test.qs[test.idx];
    const ans = test.answers[q.id] || '';
    const isMulti = q.qtype === 'multiple';
    const setAns = (v) => setTest({ ...test, answers: { ...test.answers, [q.id]: v } });
    return (
      <div style={{ maxWidth: 760, margin: '0 auto' }}>
        <div className="row between" style={{ marginBottom: 12 }}>
          <span className="muted mono">第 {test.idx + 1} / {test.qs.length} 题</span>
          <Button size="small" type="text" onClick={() => setTest(null)}>退出测试</Button>
        </div>
        <div className="v3-card">
          <div className="test-q">{esc(q.stem)}</div>
          {(q.options || []).map((o, i) => {
            const letter = String.fromCharCode(65 + i);
            const checked = isMulti ? ans.split('').includes(letter) : ans === letter;
            return (
              <div key={i} className={'test-opt' + (checked ? ' on' : '')} onClick={() => {
                if (isMulti) {
                  const letters = ans.split('').filter(Boolean);
                  setAns((checked ? letters.filter((x) => x !== letter) : [...letters, letter].sort()).join(''));
                } else setAns(letter);
              }}>
                <Tag>{letter}</Tag>{esc(o)}
              </div>
            );
          })}
          {!(q.options || []).length && (
            <Input.TextArea rows={3} placeholder="输入答案" value={ans} onChange={(e) => setAns(e.target.value)} />
          )}
          <div className="row between" style={{ marginTop: 16 }}>
            <Button disabled={test.idx <= 0} onClick={() => setTest({ ...test, idx: test.idx - 1 })}>上一题</Button>
            <span className="muted" style={{ fontSize: 11.5 }}>交卷前可返回修改</span>
            {test.idx < test.qs.length - 1 ? (
              <Button type="primary" onClick={() => setTest({ ...test, idx: test.idx + 1 })}>下一题</Button>
            ) : (
              <Button type="primary" loading={testBusy} onClick={submitTest}>交卷评分</Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="row between" style={{ marginBottom: 14 }}>
        <Segmented value={mode} onChange={setMode}
          options={[
            { label: '刷题', value: 'quiz' }, { label: '背诵', value: 'recite' },
            { label: '测试', value: 'test' }, { label: '错题本', value: 'wrong' },
          ]} />
        <div className="row">
          <span className="muted" style={{ fontSize: 12 }}>题量</span>
          <InputNumber size="small" min={1} max={50} value={count} onChange={(v) => setCount(v || 5)} style={{ width: 70 }} />
          <Button size="small" icon={<span>＋</span>} onClick={() => bankEmpty ? goImport() : qbRef.current?.click()}>导入题库</Button>
          <input ref={qbRef} type="file" accept="application/pdf" hidden onChange={(e) => { uploadBank(e.target.files[0]); e.target.value = ''; }} />
        </div>
      </div>
      {stage && <div className="muted" style={{ fontSize: 12, marginBottom: 10 }}>{stage}</div>}

      {mode === 'quiz' && bankEmpty && (
        <div className="v3-card">
          <EmptyState title="题库还没有题目" desc="去资料页上传题目文件，导入后就能按章节刷题。"
            action="导入题库" onAction={goImport} />
        </div>
      )}

      {mode === 'quiz' && !bankEmpty && (
        <div className="grid g2">
          <div>
            {recommend && (
              <div className="v3-card" style={{ marginBottom: 16 }}>
                <div className="v3-sh">今日推荐<span className="meta">{recommend.chapter || ''}</span></div>
                <div className="muted" style={{ fontSize: 12.5 }}>{esc(recommend.reason || '导入题库后，系统会按章节正确率推荐今天该练什么')}</div>
                {recommend.total ? <Progress percent={pct(recommend.progress)} size="small" /> : null}
                <Button style={{ marginTop: 10 }} type="primary" onClick={() => startQuiz({ mode: 'recommend' })}>开始这一章</Button>
              </div>
            )}
            <div className="v3-card">
              <div className="v3-sh">章节掌握度<span className="meta">{chapters.length} 章</span></div>
              {chapters.length ? chapters.map((c) => (
                <div className="row between" key={c.chapter} style={{ padding: '9px 0', borderBottom: '1px solid var(--border)' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 500 }}>{esc(c.chapter || '未分章')}</div>
                    <div className="row" style={{ gap: 6, marginTop: 4 }}>
                      <Progress percent={pct(c.progress)} size="small" style={{ width: 120 }} />
                      <span className="muted" style={{ fontSize: 11.5 }}>{c.done}/{c.total} · {pct(c.correct_rate)}%</span>
                    </div>
                  </div>
                  <Button size="small" type="text" onClick={() => startQuiz({ chapter: c.chapter })}>练这章</Button>
                </div>
              )) : <EmptyState title="还没有题目" desc="导入题库后按章节练习。" />}
            </div>
          </div>
          <div>
            <div className="grid g2" style={{ marginBottom: 16 }}>
              <Stat k="总题数" v={overview?.total || 0} />
              <Stat k="已练" v={overview?.done || 0} />
              <Stat k="正确率" v={pct(overview?.correct_rate) + '%'} />
              <Stat k="错题" v={overview?.wrong_open || 0} />
            </div>
            <div className="row" style={{ marginBottom: 12 }}>
              <Button onClick={() => startQuiz({ mode: 'new' })}>随机新题</Button>
              <Button danger onClick={() => startQuiz({ mode: 'wrong' })}>只练错题</Button>
            </div>
            <h2 style={{ fontSize: 13, fontWeight: 500, margin: '8px 0' }}>错题本</h2>
            <WrongList wrong={wrong} />
          </div>
        </div>
      )}

      {mode === 'recite' && (
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <QueueBar />
          {reciteCards.length ? (
            <>
              <div className="row between" style={{ marginBottom: 10 }}>
                <span className="muted">第 {reciteIdx + 1} / {reciteCards.length} 张 · 点击卡片翻面</span>
                <Button size="small" onClick={() => setRevealed(!revealed)}>翻面</Button>
              </div>
              <div className="v3-card flash" onClick={() => setRevealed(!revealed)} style={{ cursor: 'pointer', minHeight: 220 }}>
                <div className="q">{esc(reciteCards[reciteIdx].question)}</div>
                {revealed && <div className="a"><Markdown text={reciteCards[reciteIdx].answer} /></div>}
              </div>
              {revealed && (
                <div className="recite-rate">
                  <Button type="primary" onClick={() => reciteRate(3)}>记住了</Button>
                  <Button onClick={() => reciteRate(1)}>再练一次</Button>
                </div>
              )}
              <div className="rate">
                <Button disabled={reciteIdx <= 0}
                  onClick={() => { setReciteIdx(reciteIdx - 1); setRevealed(false); }}>上一张</Button>
                {!revealed && (
                  <Button type="primary" disabled={reciteIdx >= reciteCards.length - 1}
                    onClick={() => { setReciteIdx(reciteIdx + 1); setRevealed(false); }}>下一张</Button>
                )}
              </div>
            </>
          ) : (
            <>
              <EmptyState title="选择卡包开始背诵" desc="点击下面的卡包，逐张翻面记忆。" />
              <div className="row" style={{ justifyContent: 'center' }}>
                {decks.flatMap((r) => (r.children || []).map((c) => (
                  <Button key={c.id} onClick={() => openDeck(c.id)}>{esc(r.name)} / {esc(c.name)} · {c.total}</Button>
                )))}
              </div>
            </>
          )}
        </div>
      )}

      {mode === 'test' && (
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          {bankEmpty ? (
            <div className="v3-card">
              <EmptyState title="题库还没有题目" desc="去资料页上传题目文件，导入后就能开始测试。"
                action="导入题库" onAction={goImport} />
            </div>
          ) : (
            <div className="v3-card test-setup">
              <div className="v3-sh">开始一套测试</div>
              <div className="row" style={{ gap: 12, marginBottom: 16 }}>
                <span className="muted">题量</span>
                <InputNumber min={1} max={50} value={count} onChange={(v) => setCount(v || 5)} style={{ width: 80 }} />
                <span className="muted">题型</span>
                <Select value={testType} onChange={setTestType} options={TEST_TYPES} style={{ width: 140 }} />
              </div>
              <Button type="primary" loading={testBusy} onClick={startTest}>开始测试</Button>
            </div>
          )}
        </div>
      )}

      {mode === 'wrong' && <div className="v3-card"><WrongList wrong={wrong} /></div>}
    </div>
  );
}

function Stat({ k, v }) {
  return <div className="stat-box"><div className="k">{k}</div><div className="v">{v}</div></div>;
}
function rAnswer(r) { return r?.answer; }
function WrongList({ wrong }) {
  if (!wrong?.length) return <div className="muted" style={{ fontSize: 12.5, padding: 20 }}>暂无错题，继续保持。</div>;
  return <div>{wrong.slice(0, 8).map((q, i) => (
    <div key={i} style={{ padding: '9px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ fontSize: 12.5, lineHeight: 1.6 }}>{esc(q.stem || '')}</div>
      <div className="row" style={{ gap: 6, marginTop: 5 }}>
        <Tag color="error">你：{esc((q.last_answer || '-').slice(0, 12))}</Tag>
        <Tag color="success">答案：{esc((q.answer || '-').slice(0, 12))}</Tag>
      </div>
    </div>
  ))}</div>;
}
