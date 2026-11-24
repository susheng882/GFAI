import React, { useCallback, useEffect, useRef, useState } from 'react';
import { App as AntdApp, Button, Input, InputNumber, Progress, Segmented, Select, Tag, Tooltip } from 'antd';
import { FileAddOutlined, FlagOutlined, PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { api, runTask } from '../api.js';
import { esc, fmtTs, pct } from '../utils.js';
import { isTypingTarget, useTodayQueue } from '../hooks.js';
import EmptyState from '../components/EmptyState.jsx';
import Markdown from '../components/Markdown.jsx';
import { AiExplainButton } from '../components/AiExplainDrawer.jsx';
import QuizAnswerSheet from '../components/QuizAnswerSheet.jsx';
import QuizResult from '../components/QuizResult.jsx';
import WrongBook, { WrongPreview } from '../components/WrongBook.jsx';

const TEST_TYPES = [
  { value: 'all', label: '全部题型' },
  { value: 'single', label: '单选题' },
  { value: 'multiple', label: '多选题' },
  { value: 'fill', label: '填空题' },
];

const MODE_DESC = {
  quiz: '刷题 · 逐题判分，随时结束看解析',
  recite: '背诵 · 翻卡自评，按记忆强度排下一次',
  test: '模考 · 计时作答，交卷后统一判分',
  wrong: '错题 · 按错次排序，答对自动移出',
};

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

/* 挖空：把答案里的「重点词」转成可点击的填空。
   识别三类重点：① **加粗** ② （括号）内术语 ③ $公式$（数学式）。
   返回片段数组，每段 { t: 'text'|'blank', v, key }，blank 点击揭示。 */
function clozeAnswer(answer, shown) {
  const src = String(answer || '');
  const parts = [];
  const re = /(\*\*[^*]+\*\*|（[^）]*）|\([^)]*\)|\$[^$]+\$)/g;
  let last = 0, m, k = 0;
  while ((m = re.exec(src)) !== null) {
    if (m.index > last) parts.push({ t: 'text', v: src.slice(last, m.index), key: k++ });
    const raw = m[0];
    const inner = raw.replace(/^\*\*/, '').replace(/\*\*$/, '');
    const isMath = raw.startsWith('$');
    parts.push({ t: 'blank', v: inner, key: k++, isMath });
    last = m.index + raw.length;
  }
  if (last < src.length) parts.push({ t: 'text', v: src.slice(last), key: k++ });
  if (!parts.some((p) => p.t === 'blank')) {
    // 没有可挖空的重点，整段原样显示
    return [{ t: 'text', v: src, key: 0 }];
  }
  return parts;
}


/* 题库为空：160px 主空态 + 三步说明，动作只在空态内（C-1 / C-2）。 */
function EmptyBank({ title, onImport }) {
  return (
    <div className="v3-card">
      <div className="study-empty">
        <span className="se-ic"><FileAddOutlined /></span>
        <div className="se-t">{title}</div>
        <div className="se-d">把题目文件解析成可练的题库</div>
        <Button type="primary" onClick={onImport}>导入题库</Button>
      </div>
      <ol className="se-steps">
        <li><b>1</b>导入题库 · 题库页上传试卷 PDF</li>
        <li><b>2</b>选题量 · 每轮 1 到 50 题</li>
        <li><b>3</b>开始 · 刷题逐题判分，模考统一交卷</li>
      </ol>
    </div>
  );
}

/* 学习页：刷题（推荐/随机/错题/章节）、背诵卡片、模考、错题本、题库导入。 */
export default function StudyPage() {
  const { message, modal } = AntdApp.useApp();
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
  const [fill, setFill] = useState('');
  const [reciteCards, setReciteCards] = useState([]);
  const [reciteIdx, setReciteIdx] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [reciteGroups, setReciteGroups] = useState([]);  // 分组背诵：{ name, cards }[]
  const [blanksShown, setBlanksShown] = useState({});     // 挖空显隐：{ cardId: true/false }
  const [count, setCount] = useState(5);
  const [decks, setDecks] = useState([]);
  const [stage, setStage] = useState('');
  const [testType, setTestType] = useState('all');
  const [test, setTest] = useState(null);
  const [testBusy, setTestBusy] = useState(false);
  const [testScore, setTestScore] = useState({ correct: 0, total: 0 });
  const [sheetOpen, setSheetOpen] = useState(false);
  const [timerStart, setTimerStart] = useState(0);
  const [elapsed, setElapsed] = useState(0);
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

  /* 计时：test 与 quiz 共用；timerStart 为 0 表示停表，卸载/停表都清掉 interval。 */
  useEffect(() => {
    if (!timerStart) return undefined;
    const tick = () => setElapsed(Math.floor((Date.now() - timerStart) / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [timerStart]);

  const bankEmpty = overview != null && +overview.total === 0 && !chapters.length;
  const goImport = () => navigate('/banks');

  const startQuiz = async (payload) => {
    if (bankEmpty) { message.info('请先导入题库，再去题库页上传试卷'); goImport(); return; }
    try {
      const qs = await api('/quiz/generate', { method: 'POST', body: JSON.stringify({ count, ...payload }) });
      if (!qs?.length) { message.info('没有符合条件的题目'); return; }
      setTest(null); setQuiz(qs); setIdx(0); setAnswer(null); setSelected(null); setFill('');
      setMode('quiz'); setElapsed(0); setTimerStart(Date.now());
    } catch (e) {
      message.info(e.message || '暂时无法出题，请先确认题库已导入');
    }
  };

  const exitQuiz = () => { setQuiz(null); setTimerStart(0); setElapsed(0); load(); };

  /* S3 针对薄弱点：后端按掌握度 / 错次用 SQL 挑题（不调模型），题目自带 reason。 */
  const startWeak = async () => {
    if (bankEmpty) { message.info('请先导入题库，再去题库页上传试卷'); goImport(); return; }
    try {
      const qs = await api('/ai/weak-quiz', {
        method: 'POST', body: JSON.stringify({ count: Math.min(count, 20) }),
      });
      if (!qs?.length) { message.info('当前没有明显薄弱的题目，先去刷一轮'); return; }
      setTest(null); setQuiz(qs); setIdx(0); setAnswer(null); setSelected(null); setFill('');
      setMode('quiz'); setElapsed(0); setTimerStart(Date.now());
    } catch (e) {
      message.info(e.message || '暂时无法生成薄弱练习');
    }
  };

  const submit = async () => {
    const q = quiz[idx];
    const ans = selected != null ? (q.options || [])[selected] : fill;
    if (!ans) { message.warning('请选择或输入答案'); return; }
    try {
      const r = await api('/quiz/submit', { method: 'POST', body: JSON.stringify({ question_id: q.id, user_answer: ans }) });
      setAnswer(r);
    } catch (e) { message.info(e.message || '提交失败，请重试'); }
  };

  const nextPractice = () => {
    setIdx(idx + 1); setAnswer(null); setSelected(null); setFill('');
    if (idx + 1 >= quiz.length) { setTimerStart(0); load(); }
  };

  const openDeck = async (id) => {
    try {
      const cards = await api(`/decks/${id}/cards`) || [];
      if (!cards.length) { message.info('这个卡包还没有卡片'); return; }
      setReciteCards(cards); setReciteIdx(0); setRevealed(false); setMode('recite');
    } catch (e) { message.info(e.message || '暂时无法读取卡包'); }
  };

  /* 分组背诵：点根卡包 → 拉取它下面所有章节卡包 → 按章节分组一屏展示 */
  const openDeckGroup = async (root) => {
    try {
      const kids = (root.children || []).filter((c) => +c.total > 0);
      if (!kids.length) { message.info('这个卡包下还没有章节卡片'); return; }
      const all = [];
      for (const k of kids) {
        const cards = await api(`/decks/${k.id}/cards`) || [];
        if (cards.length) all.push({ name: k.name, cards });
      }
      if (!all.length) { message.info('没有可背诵的卡片'); return; }
      setReciteGroups(all);
      setBlanksShown({});
      setMode('recite');
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

  /* 模考：题量/题型 → /quiz/generate；交卷逐题 /quiz/submit → 练习报告。 */
  const startTest = async (size) => {
    if (bankEmpty) { message.info('请先导入题库'); goImport(); return; }
    setTestBusy(true);
    try {
      const n = Math.min(50, size || count);
      const body = { count: n, mode: 'new' };
      if (testType !== 'all') body.qtype = testType;
      const raw = await api('/quiz/generate', { method: 'POST', body: JSON.stringify(body) });
      const picked = (Array.isArray(raw) ? raw : []).slice(0, n);
      if (!picked.length) { message.info('没有符合条件的题目'); return; }
      setQuiz(null);
      setTest({ phase: 'paper', qs: picked, idx: 0, answers: {}, results: [], flagged: {} });
      setTestScore({ correct: 0, total: picked.length });
      setSheetOpen(false); setElapsed(0); setTimerStart(Date.now()); setMode('test');
    } catch (e) { message.info(e.message || '暂时无法出题'); }
    finally { setTestBusy(false); }
  };

  const doSubmit = async (t) => {
    if (!t) return;
    const used = timerStart ? Math.floor((Date.now() - timerStart) / 1000) : elapsed;
    setSheetOpen(false); setTestBusy(true); setTimerStart(0);
    const results = [];
    let correct = 0;
    for (const q of t.qs) {
      const user = (t.answers[q.id] || '').trim();
      try {
        const r = await api('/quiz/submit', {
          method: 'POST', body: JSON.stringify({ question_id: q.id, user_answer: user }),
        });
        results.push({ q, user, ...r });
        if (r?.correct) correct++;
      } catch (e) { results.push({ q, user, error: e.message || '判分失败' }); }
    }
    setTestBusy(false);
    setTest({ ...t, phase: 'review', results, idx: 0, elapsed: used });
    setTestScore({ correct, total: t.qs.length });
    setElapsed(used);
    if (t.redo) {
      const r0 = results[0];
      if (r0?.correct) { message.success('已移出错题本'); load(); }
      else if (r0?.error) message.info(r0.error);
      else message.info('仍在错题本，错次 +1');
    } else {
      message.success('已交卷');
      load();
    }
  };

  const confirmSubmit = () => {
    if (!test) return;
    const left = test.qs.filter((q) => !(test.answers[q.id] || '').trim()).length;
    modal.confirm({
      title: left ? `还有 ${left} 题未作答` : '确认交卷',
      content: left ? '未作答的题按错误计分，交卷后不能修改答案' : '交卷后不能修改答案',
      okText: '交卷',
      cancelText: '继续作答',
      onOk: () => doSubmit(test),
    });
  };

  const exitTest = () => {
    if (!test) return;
    const n = Object.values(test.answers || {}).filter((v) => (v || '').trim()).length;
    if (!n) { setTest(null); setTimerStart(0); setElapsed(0); return; }
    modal.confirm({
      title: '退出本次模考',
      content: `已作答 ${n} 题，退出后不保存`,
      okText: '退出',
      okButtonProps: { danger: true },
      cancelText: '继续作答',
      onOk: () => { setTest(null); setTimerStart(0); setElapsed(0); },
    });
  };

  const backToStudy = () => { setTest(null); setTimerStart(0); setElapsed(0); load(); };

  /* 单题重做：直接用错题本里的题（含 options），答对后 /quiz/wrong 自动移出。 */
  const redoOne = (q) => {
    setSheetOpen(false); setQuiz(null); setMode('test');
    setTest({
      phase: 'paper', idx: 0, answers: {}, results: [], flagged: {}, redo: true,
      qs: [{ id: q.id, stem: q.stem, options: q.options, qtype: q.qtype, chapter: q.chapter }],
    });
    setTestScore({ correct: 0, total: 1 });
    setElapsed(0); setTimerStart(Date.now());
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
          <div className="v3-card" style={{ textAlign: 'center', padding: 32 }}>
            <div style={{ fontSize: 16, fontWeight: 500 }}>这一轮完成</div>
            <div className="muted" style={{ marginTop: 6 }}>
              共 {quiz.length} 题 · 用时 <span className="mono">{fmtTs(elapsed)}</span>
            </div>
            <Button style={{ marginTop: 14 }} onClick={() => { setQuiz(null); load(); }}>再来一套</Button>
          </div>
          <div className="v3-card" style={{ marginTop: 12 }}>
            <div className="v3-sh">错题本<span className="meta">{wrong.length} 题</span></div>
            <WrongPreview wrong={wrong} onMore={() => { setQuiz(null); setMode('wrong'); }} />
          </div>
        </div>
      );
    }
    const q = quiz[idx];
    return (
      <div style={{ maxWidth: 760, margin: '0 auto' }}>
        <div className="test-top">
          <div className="test-top-l">
            <span>第 <b className="mono">{idx + 1}</b> / <span className="mono">{quiz.length}</span> 题</span>
            <span>用时 <span className="test-clock">{fmtTs(elapsed)}</span></span>
          </div>
          <Button size="small" type="text" onClick={exitQuiz}>结束练习</Button>
        </div>
        <div className="v3-card">
          <div style={{ fontSize: 15, fontWeight: 500, lineHeight: 1.7, marginBottom: 8 }}>{esc(q.stem)}</div>
          {q.reason && (
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 12 }}>{esc(q.reason)}</div>
          )}
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
          {!(q.options || []).length && (
            <Input placeholder="输入答案" disabled={!!answer} value={fill} onChange={(e) => setFill(e.target.value)} />
          )}
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
              <div className="row" style={{ justifyContent: 'flex-end', marginTop: 14, gap: 8 }}>
                <AiExplainButton questionId={q.id} label="AI 讲解" />
                <Button type="primary" onClick={nextPractice}>下一题</Button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  /* ---------- 模考：交卷前不判分，交卷后统一评分 + 知识点分布 + 逐题回顾 ---------- */
  if (test) {
    if (test.phase === 'review') {
      return (
        <QuizResult
          test={test}
          score={testScore}
          elapsed={test.elapsed ?? elapsed}
          onJump={(i) => setTest((t) => ({ ...t, idx: i }))}
          onRetest={() => startTest(test.qs.length)}
          onBack={backToStudy}
        />
      );
    }
    const q = test.qs[test.idx];
    const ans = test.answers[q.id] || '';
    const isMulti = q.qtype === 'multiple';
    const flagged = !!test.flagged?.[q.id];
    const answeredCount = test.qs.filter((x) => (test.answers[x.id] || '').trim()).length;
    const setAns = (v) => setTest((t) => ({ ...t, answers: { ...t.answers, [q.id]: v } }));
    const last = test.idx >= test.qs.length - 1;
    return (
      <div style={{ maxWidth: 760, margin: '0 auto' }}>
        <div className="test-top">
          <div className="test-top-l">
            <span>第 <b className="mono">{test.idx + 1}</b> / <span className="mono">{test.qs.length}</span> 题</span>
            <span>用时 <span className="test-clock">{fmtTs(elapsed)}</span></span>
          </div>
          <div className="test-top-r">
            <Button size="small" type="text" className={'test-flag' + (flagged ? ' on' : '')}
              icon={<FlagOutlined />} onClick={() => setTest((t) => ({
                ...t, flagged: { ...t.flagged, [q.id]: !t.flagged?.[q.id] },
              }))}>
              {flagged ? '已标记' : '标记疑题'}
            </Button>
            <Button size="small" onClick={() => setSheetOpen(true)}>答题卡 {answeredCount}/{test.qs.length}</Button>
            <Button size="small" type="text" onClick={exitTest}>退出</Button>
          </div>
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
          <div className="test-nav">
            <Button disabled={test.idx <= 0} onClick={() => setTest((t) => ({ ...t, idx: t.idx - 1 }))}>上一题</Button>
            {last ? (
              <Button type="primary" loading={testBusy} onClick={confirmSubmit}>交卷评分</Button>
            ) : (
              <>
                <Button onClick={confirmSubmit}>交卷</Button>
                <Button type="primary" onClick={() => setTest((t) => ({ ...t, idx: t.idx + 1 }))}>下一题</Button>
              </>
            )}
          </div>
        </div>
        <QuizAnswerSheet
          open={sheetOpen}
          questions={test.qs}
          answers={test.answers}
          flagged={test.flagged}
          idx={test.idx}
          busy={testBusy}
          onJump={(i) => { setTest((t) => ({ ...t, idx: i })); setSheetOpen(false); }}
          onClose={() => setSheetOpen(false)}
          onSubmit={confirmSubmit}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="row between" style={{ marginBottom: 8 }}>
        <Tooltip title={bankEmpty ? '导入题库后可切换其他模式' : ''}>
          <Segmented value={mode} onChange={setMode}
            options={[
              { label: '刷题', value: 'quiz' },
              { label: '背诵', value: 'recite', disabled: bankEmpty },
              { label: '模考', value: 'test', disabled: bankEmpty },
              { label: '错题', value: 'wrong', disabled: bankEmpty },
            ]} />
        </Tooltip>
        {!bankEmpty && (
          <Button size="small" icon={<PlusOutlined />} onClick={() => qbRef.current?.click()}>导入题库</Button>
        )}
      </div>
      <div className="study-mode-desc">{MODE_DESC[mode]}</div>
      <input ref={qbRef} type="file" accept="application/pdf" hidden onChange={(e) => { uploadBank(e.target.files[0]); e.target.value = ''; }} />
      {stage && <div className="muted" style={{ fontSize: 12, marginBottom: 10 }}>{stage}</div>}

      {mode === 'quiz' && bankEmpty && <EmptyBank title="题库还没有题目" onImport={goImport} />}

      {mode === 'quiz' && !bankEmpty && (
        <div className="grid g2">
          <div>
            {recommend && (
              <div className="v3-card" style={{ marginBottom: 16 }}>
                <div className="v3-sh">今日推荐<span className="meta">{recommend.chapter || ''}</span></div>
                <div className="muted" style={{ fontSize: 12.5 }}>{esc(recommend.reason || '导入题库后，系统会按章节正确率推荐今天该练什么')}</div>
                {recommend.total ? <Progress percent={pct(recommend.progress)} size="small" /> : null}
                <div className="row" style={{ marginTop: 10, gap: 8, flexWrap: 'wrap' }}>
                  <Button type="primary" onClick={() => startQuiz({ mode: 'recommend' })}>开始这一章</Button>
                  <Button onClick={startWeak}>针对薄弱点</Button>
                </div>
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
            <div className="v3-card v3-strip" style={{ marginBottom: 12 }}>
              <div className="m"><div className="k">总题数</div><div className="v mono">{overview?.total || 0}</div></div>
              <div className="m"><div className="k">已练</div><div className="v mono">{overview?.done || 0}</div></div>
              <div className="m"><div className="k">正确率</div><div className="v mono">{pct(overview?.correct_rate)}%</div></div>
              <div className="m"><div className="k">错题</div><div className="v mono">{overview?.wrong_open || 0}</div></div>
            </div>
            <div className="row" style={{ marginBottom: 12 }}>
              <span className="muted" style={{ fontSize: 11.5 }}>题量</span>
              <InputNumber size="small" min={1} max={50} value={count} onChange={(v) => setCount(v || 5)} style={{ width: 64 }} />
              <Button onClick={() => startQuiz({ mode: 'new' })}>随机新题</Button>
              <Button danger onClick={() => startQuiz({ mode: 'wrong' })}>只练错题</Button>
            </div>
            <div className="v3-card">
              <div className="v3-sh">错题<span className="meta">{wrong.length} 题</span></div>
              <WrongPreview wrong={wrong} onMore={() => setMode('wrong')} />
            </div>
          </div>
        </div>
      )}

      {mode === 'recite' && (
        <div style={{ maxWidth: 860, margin: '0 auto' }}>
          <QueueBar />
          {reciteGroups.length ? (
            <GroupRecite groups={reciteGroups} blanksShown={blanksShown}
              onToggleBlank={(id) => setBlanksShown((s) => ({ ...s, [id]: !s[id] }))}
              onRate={(id, rating) => api(`/review/${id}`, { method: 'POST', body: JSON.stringify({ rating }) })
                .then(() => message.success(rating === 3 ? '已记住' : '已记录'))
                .catch(() => message.info('评分暂未保存'))}
              onExit={() => { setReciteGroups([]); setMode('quiz'); }} />
          ) : reciteCards.length ? (
            <>
              <div className="row between" style={{ marginBottom: 10 }}>
                <span className="muted">第 {reciteIdx + 1} / {reciteCards.length} 张</span>
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
              <EmptyState title="选择卡包开始背诵" desc="点一个卡包，按章节分组背诵；重点词默认挖空，点击查看。" />
              <div className="row" style={{ justifyContent: 'center', flexWrap: 'wrap' }}>
                {decks.map((r) => (
                  <Button key={r.id} type={(r.children || []).some((c) => +c.total > 0) ? 'default' : 'default'}
                    onClick={() => openDeckGroup(r)}
                    style={{ margin: 4 }}>
                    {esc(r.name)} · {r.total} 张
                  </Button>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {mode === 'test' && (
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          {bankEmpty ? (
            <EmptyBank title="题库还没有题目" onImport={goImport} />
          ) : (
            <div className="v3-card test-setup">
              <div className="v3-sh">开始一套模考</div>
              <div className="test-setup-row">
                <span className="muted">题量</span>
                <InputNumber min={1} max={50} value={count} onChange={(v) => setCount(v || 5)} style={{ width: 80 }} />
                <span className="muted">题型</span>
                <Select value={testType} onChange={setTestType} options={TEST_TYPES} style={{ width: 140 }} />
                <Button type="primary" loading={testBusy} onClick={() => startTest()}>开始模考</Button>
              </div>
            </div>
          )}
        </div>
      )}

      {mode === 'wrong' && (
        <div className="v3-card">
          <WrongBook wrong={wrong} onRedo={redoOne} onRetryChapter={(c) => startQuiz({ mode: 'wrong', chapter: c })} />
        </div>
      )}
    </div>
  );
}

function rAnswer(r) { return r?.answer; }


/* 分组背诵：同一章节/知识点的卡片一屏展示，重点词挖空可点。
   摆脱「一句话翻一张卡」的反人类设计，改为「背一节知识点」。 */
function GroupRecite({ groups, blanksShown, onToggleBlank, onRate, onExit }) {
  return (
    <div>
      <div className="row between" style={{ marginBottom: 12 }}>
        <span className="muted">共 {groups.length} 个章节 · {groups.reduce((n, g) => n + g.cards.length, 0)} 张卡</span>
        <Button size="small" onClick={onExit}>退出背诵</Button>
      </div>
      {groups.map((g, gi) => (
        <div key={gi} className="v3-card" style={{ padding: 16, marginBottom: 14 }}>
          <div className="v3-sh" style={{ marginBottom: 10 }}>{esc(g.name)}<span className="meta">{g.cards.length} 个知识点</span></div>
          {g.cards.map((c) => {
            const shown = !!blanksShown[c.id];
            const parts = clozeAnswer(c.answer, shown);
            const hasBlank = parts.some((p) => p.t === 'blank');
            return (
              <div key={c.id} className="grec" style={{ padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                <div className="q" style={{ fontWeight: 500, marginBottom: 6 }}>{esc(c.question)}</div>
                <div className="a" style={{ lineHeight: 1.8 }}>
                  {parts.map((p) => p.t === 'text' ? (
                    <span key={p.key}>{esc(p.v)}</span>
                  ) : shown ? (
                    <span key={p.key} className="gblank gblank-on">{esc(p.v)}</span>
                  ) : (
                    <span key={p.key} className="gblank" onClick={() => onToggleBlank(c.id)}
                      title="点击查看">▢▢▢</span>
                  ))}
                </div>
                <div className="row" style={{ gap: 6, marginTop: 8 }}>
                  {hasBlank && (
                    <Button size="small" type="link" onClick={() => onToggleBlank(c.id)}>
                      {shown ? '隐藏重点' : '显示全部重点'}
                    </Button>
                  )}
                  <Button size="small" onClick={() => onRate(c.id, 3)}>记住了</Button>
                  <Button size="small" type="text" onClick={() => onRate(c.id, 1)}>再练一次</Button>
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
