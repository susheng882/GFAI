import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { App as AntdApp, Button, Checkbox, Empty, Input, Modal, Progress, Tag, Upload } from 'antd';
import { InboxOutlined, MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import { api, downloadText, runTask, shortErr } from '../api.js';
import { esc, fmtTs, noteKindCn } from '../utils.js';
import { useCollapsible } from '../hooks.js';
import Markdown from '../components/Markdown.jsx';
import MindMap from '../components/MindMap.jsx';

const TPL = [
  { key: 'summary', label: '摘要' }, { key: 'outline', label: '大纲' },
  { key: 'qa', label: '问答' }, { key: 'frames', label: '图文' },
];

/* 批量导入：单批上限 50，与后端视频池（默认 5 并发）分两层限流。
   前端只负责「一条一条提交任务」，排队与转写交给后端，避免一次打满连接。 */
const BATCH_MAX = 50;
const VIDEO_EXT = /\.(mp4|mkv|mov|webm|m4a|mp3|wav|flac|aac|m4v)$/i;
const BATCH_CN = { queued: '排队', submitting: '提交中', accepted: '转写中', done: '已完成', failed: '失败' };
const BATCH_TONE = {
  queued: 'var(--muted-foreground)', submitting: 'var(--primary)', accepted: 'var(--primary)',
  done: 'var(--success)', failed: 'var(--destructive)',
};

/* 逐行解析链接：只保留 http(s) 且域名含点的地址，重复项按规范化 URL 去重。
   非法行单独返回，由界面提示「已跳过」，不弹红色报错。 */
function parseVideoUrls(text) {
  const ok = [];
  const bad = [];
  const seen = new Set();
  for (const raw of String(text || '').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    // 只写域名时补 https://，其余仍要求完整 http(s) 地址
    const full = /^(b23\.tv|bilibili\.com|www\.bilibili\.com)\//i.test(line) ? `https://${line}` : line;
    if (!/^https?:\/\//i.test(full)) { bad.push(line); continue; }
    try {
      const u = new URL(full);
      if (!u.hostname || !u.hostname.includes('.')) { bad.push(line); continue; }
      if (seen.has(u.href)) continue;
      seen.add(u.href);
      ok.push({ key: u.href, url: full });
    } catch { bad.push(line); }
  }
  return { ok, bad };
}

/* 文稿命中的片段用 `**` 标出关键词，这里按标记切成普通/加粗两段渲染 */
function hitParts(text) {
  return String(text || '').split('**').map((seg, i) => (i % 2
    ? <b key={i} style={{ fontWeight: 500, color: 'var(--primary)' }}>{seg}</b>
    : <React.Fragment key={i}>{seg}</React.Fragment>));
}

/* 视频模块 · 三段式（对标 BiliNote）：
   左：上传/链接 + 历史 ｜ 中：播放器 + 关键点时间轴 ｜ 右：笔记（单篇 Markdown / 三模板 / 思维导图）
   关键帧与笔记里的图都能点，直接 seek 到对应秒数。 */
export default function VideoPage() {
  const { message, modal } = AntdApp.useApp();
  const [params, setParams] = useSearchParams();
  const videoRef = useRef(null);
  const [list, setList] = useState([]);
  const [notes, setNotes] = useState([]);
  const [transcript, setTranscript] = useState([]);
  const [frames, setFrames] = useState([]);
  const [docId, setDocId] = useState(null);
  const [title, setTitle] = useState('');
  const [active, setActive] = useState('markdown');
  const [tpls, setTpls] = useState(['summary', 'outline', 'qa']);
  const [url, setUrl] = useState('');
  const [stage, setStage] = useState('');
  const [busy, setBusy] = useState(false);
  // 文稿检索：hits=null 表示未检索（不显示结果区），[] 表示检索过但没有命中
  const [q, setQ] = useState('');
  const [hits, setHits] = useState(null);
  const [hitTotal, setHitTotal] = useState(0);
  const [searching, setSearching] = useState(false);
  const [exporting, setExporting] = useState(false);
  // 批量导入：清单存在页面状态里，刷新即回到 /videos 历史视图（不承诺断点续传）
  const [batchOpen, setBatchOpen] = useState(false);
  const [batchText, setBatchText] = useState('');
  const [batchQueue, setBatchQueue] = useState([]);
  const [batchRun, setBatchRun] = useState(false);
  const batchIdRef = useRef(0);
  const batchFileRef = useRef(null);
  const batchRunRef = useRef(false);
  // 正在跑的时间里有新条目改回 queued（重试）：让当前循环再取一轮，而不是另起一个并行循环
  const batchResumeRef = useRef(false);
  const batchQueueRef = useRef(batchQueue);
  batchQueueRef.current = batchQueue;
  // 视频左右栏折叠：状态记忆到 localStorage，刷新后保持
  const [leftCollapsed, toggleLeft] = useCollapsible('gflc_video_left', false);
  const [rightCollapsed, toggleRight] = useCollapsible('gflc_video_right', false);
  const pendingSeek = useRef(Number(params.get('ts')) || 0);

  const loadList = useCallback(async () => {
    try { setList(await api('/videos') || []); } catch { setList([]); }
  }, []);
  useEffect(() => { loadList(); }, [loadList]);

  const openVideo = useCallback(async (id) => {
    try {
      const d = await api(`/videos/${id}/notes`);
      setDocId(Number(id)); setTitle(d.title || '');
      setNotes(d.notes || []);
      setTranscript(d.transcript || []);
      // 换视频后旧检索结果失效，清空但保留输入框内容
      setHits(null); setHitTotal(0);
      setFrames((d.frames || []).map((f) => ({ ...f, name: String(f.name || f.path || '').split(/[\\/]/).pop() })));
      const hasMd = (d.notes || []).some((n) => n.kind === 'markdown');
      setActive(hasMd ? 'markdown' : ((d.notes || [])[0]?.kind || 'summary'));
    } catch (e) { message.error(e.message); }
  }, [message]);

  useEffect(() => {
    const id = params.get('doc');
    pendingSeek.current = Number(params.get('ts')) || 0;
    if (id) openVideo(id);
  }, [params, openVideo]);

  const seek = useCallback((sec) => {
    const v = videoRef.current;
    const t = Math.max(0, Number(sec) || 0);
    if (!v) { pendingSeek.current = t; return; }
    try {
      v.currentTime = Number.isFinite(v.duration) && v.duration > 0 ? Math.min(t, Math.max(0, v.duration - 0.15)) : t;
      v.play().catch(() => {});
    } catch { /* 未就绪时忽略，时间已记在 pendingSeek */ }
  }, []);
  const onLoadedMetadata = () => {
    if (pendingSeek.current > 0) { seek(pendingSeek.current); pendingSeek.current = 0; }
  };

  const applyResult = async (r) => {
    if (r?.document_id) await openVideo(r.document_id);
    await loadList();
  };
  const doTask = async (fn, label) => {
    setBusy(true);
    try { const r = await fn(); await applyResult(r); message.success(`${label}完成`); }
    catch (e) { message.error(e.message); } finally { setBusy(false); setStage(''); }
  };

  const uploadFile = (file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file); fd.append('templates', tpls.join(','));
    setStage('上传中，排队转写…');
    doTask(() => runTask('/videos/upload', { method: 'POST', body: fd }, '视频转写'), '视频笔记');
  };
  const uploadUrl = () => {
    if (!url.trim()) { message.warning('请粘贴链接'); return; }
    setStage('已提交（下载 → 转写 → 生成）…');
    doTask(() => runTask('/videos/url', {
      method: 'POST', body: JSON.stringify({ url: url.trim(), templates: tpls }),
    }, '链接视频'), '链接视频笔记');
  };
  const del = (id) => modal.confirm({
    title: '删除该视频及其笔记？', okText: '删除', okButtonProps: { danger: true }, cancelText: '取消',
    onOk: async () => {
      try {
        await api(`/videos/${id}`, { method: 'DELETE' });
        if (docId === Number(id)) { setDocId(null); setNotes([]); setTranscript([]); setFrames([]); }
        await loadList(); message.success('已删除');
      } catch (e) { message.error(e.message); }
    },
  });
  const toggleTpl = (k) => setTpls((cur) => {
    const next = cur.includes(k) ? cur.filter((x) => x !== k) : [...cur, k];
    return next.length ? next : ['summary'];
  });

  /* 导出整段视频的 Markdown（标题 + 摘要/大纲/问答/图文）。接口返回附件流，这里取文本再落盘。 */
  const exportMd = async () => {
    if (!docId) { message.info('先选择一个视频'); return; }
    setExporting(true);
    try {
      const res = await fetch(`/api/videos/${docId}/export`, { credentials: 'include' });
      if (!res.ok) {
        let msg = `导出失败（${res.status}）`;
        try { const j = await res.json(); msg = j?.error?.message || j?.detail || msg; } catch { /* 非 JSON 错误体 */ }
        throw new Error(msg);
      }
      const name = String(title || '视频笔记').replace(/[\\/:*?"<>|\r\n]+/g, '_').trim().slice(0, 60) || '视频笔记';
      downloadText(`${name}.md`, await res.text());
      message.success('已导出 Markdown');
    } catch (e) { message.error(e.message || '导出失败'); } finally { setExporting(false); }
  };

  /* 文稿检索：回车触发，结果命中后端 LIKE 过滤后的片段（含起点秒数） */
  const runSearch = async (value) => {
    const term = String(value ?? q).trim();
    if (!docId) { message.info('先选择一个视频'); return; }
    if (!term) { setHits(null); setHitTotal(0); return; }
    setSearching(true);
    try {
      const r = await api(`/videos/${docId}/search?q=${encodeURIComponent(term)}&limit=20`);
      setHits(r?.hits || []); setHitTotal(r?.total || 0);
    } catch (e) {
      setHits(null); setHitTotal(0); message.error(e.message);
    } finally { setSearching(false); }
  };
  const onSearchChange = (e) => {
    const v = e.target.value;
    setQ(v);
    if (!v.trim()) { setHits(null); setHitTotal(0); }
  };

  /* ---------- 批量导入：清单 → 串行提交 → 轮询进度 ---------- */
  const patchBatch = (id, patch) => setBatchQueue((q) => q.map((x) => (x.id === id ? { ...x, ...patch } : x)));

  const addBatchUrls = () => {
    if (!batchText.trim()) { message.info('先粘贴链接，每行一个'); return; }
    const { ok, bad } = parseVideoUrls(batchText);
    if (!ok.length) {
      message.warning(bad.length ? `没有可用链接：${bad.length} 行不是 http(s) 链接` : '没有识别到链接');
      return;
    }
    const exist = new Set(batchQueueRef.current.filter((x) => x.kind === 'url').map((x) => x.key));
    const fresh = ok.filter((x) => !exist.has(x.key));
    const dup = ok.length - fresh.length;
    if (!fresh.length) { message.info('这些链接已在清单中'); return; }
    if (batchQueueRef.current.length + fresh.length > BATCH_MAX) {
      message.warning(`单批最多 ${BATCH_MAX} 条，清单已有 ${batchQueueRef.current.length} 条，本次 ${fresh.length} 条未加入`);
      return;
    }
    const items = fresh.map((x) => ({
      id: ++batchIdRef.current, kind: 'url', key: x.key, name: x.url, value: x.url,
      selected: true, status: 'queued', taskId: null, error: '', progress: 0,
    }));
    setBatchQueue((q) => [...q, ...items]);
    setBatchText('');
    const tail = [bad.length ? `${bad.length} 行格式不正确已跳过` : '', dup ? `${dup} 条重复已跳过` : '']
      .filter(Boolean).join('，');
    message.success(`已加入 ${fresh.length} 条${tail ? `，${tail}` : ''}`);
  };

  const addBatchFiles = (files) => {
    const arr = Array.from(files || []);
    if (!arr.length) return;
    const good = arr.filter((f) => VIDEO_EXT.test(f.name || ''));
    const bad = arr.length - good.length;
    if (!good.length) {
      message.warning(`没有可用的视频/音频文件${bad ? `（${bad} 个格式不支持）` : ''}`);
      return;
    }
    const exist = new Set(batchQueueRef.current.filter((x) => x.kind === 'file').map((x) => x.key));
    const fresh = good.filter((f) => !exist.has(`${f.name}:${f.size}:${f.lastModified}`));
    if (!fresh.length) { message.info('这些文件已在清单中'); return; }
    if (batchQueueRef.current.length + fresh.length > BATCH_MAX) {
      message.warning(`单批最多 ${BATCH_MAX} 条，清单已有 ${batchQueueRef.current.length} 个，本次 ${fresh.length} 个未加入`);
      return;
    }
    const items = fresh.map((f) => ({
      id: ++batchIdRef.current, kind: 'file', key: `${f.name}:${f.size}:${f.lastModified}`,
      name: f.name, value: f, selected: true, status: 'queued', taskId: null, error: '', progress: 0,
    }));
    setBatchQueue((q) => [...q, ...items]);
    message.success(`已加入 ${fresh.length} 个文件${bad ? `，${bad} 个格式不支持已跳过` : ''}`);
  };

  /* 单条提交：链接走 /videos/url，文件走 /videos/upload；拿到 task_id 交给下面的轮询。 */
  const submitOne = async (it) => {
    patchBatch(it.id, { status: 'submitting', error: '' });
    try {
      let r;
      if (it.kind === 'url') {
        r = await api('/videos/url', { method: 'POST', body: JSON.stringify({ url: it.value, templates: tpls }) });
      } else {
        const fd = new FormData();
        fd.append('file', it.value);
        fd.append('templates', tpls.join(','));
        r = await api('/videos/upload', { method: 'POST', body: fd });
      }
      if (!r || !r.task_id) throw new Error('服务未返回任务号');
      patchBatch(it.id, { status: 'accepted', taskId: r.task_id, progress: 0 });
    } catch (e) {
      patchBatch(it.id, { status: 'failed', error: shortErr(e.message) || '提交失败' });
    }
  };

  /* 串行抽干队列：每轮取「第一个勾选且排队中」的条目提交，直到没有。
     限流口径不变 —— 一次只发一个请求，转写并发仍由后端视频池控制；
     重试把条目改回 queued 后自然排到当前轮次后面（resume 标记让正在跑的循环再取一轮）。 */
  const drainBatch = async () => {
    if (batchRunRef.current) { batchResumeRef.current = true; return; }
    batchRunRef.current = true;
    setBatchRun(true);
    try {
      for (;;) {
        const next = batchQueueRef.current.find((x) => x.selected && x.status === 'queued');
        if (!next) {
          if (batchResumeRef.current) { batchResumeRef.current = false; continue; }
          break;
        }
        batchResumeRef.current = false;
        await submitOne(next);
      }
    } finally {
      batchResumeRef.current = false;
      batchRunRef.current = false;
      setBatchRun(false);
      await loadList();
    }
  };

  const runBatch = () => {
    if (batchRunRef.current) return;
    const pending = batchQueueRef.current.filter((x) => x.selected && x.status === 'queued');
    if (!pending.length) { message.info('清单里没有待提交的条目'); return; }
    drainBatch();
  };

  /* 重试：把失败条目改回 queued 并追加到清单末尾（不插队、不抢占仍在排队的条目），
     再走同一条串行队列。并发策略不变：仍是一条一条提交，转写并发仍归后端视频池。 */
  const requeue = (ids, notice) => {
    const set = new Set(ids);
    setBatchQueue((q) => {
      const kept = q.filter((x) => !set.has(x.id));
      const moved = q.filter((x) => set.has(x.id)).map((x) => ({
        ...x, status: 'queued', error: '', progress: 0, taskId: null, selected: true,
      }));
      return [...kept, ...moved];
    });
    if (notice) message.info(notice);
    // 状态落地后再抽干，避免读到上一帧的 failed 状态
    setTimeout(drainBatch, 0);
  };
  const retryOne = (id) => requeue([id], '已重新排队，按顺序提交');
  const retryAllFailed = () => {
    const ids = batchQueueRef.current.filter((x) => x.status === 'failed').map((x) => x.id);
    if (!ids.length) { message.info('没有失败的条目'); return; }
    requeue(ids, `已把 ${ids.length} 条失败任务重新排队`);
  };

  const batchStat = useMemo(() => {
    const sel = batchQueue.filter((x) => x.selected);
    const n = { queued: 0, submitting: 0, accepted: 0, done: 0, failed: 0 };
    sel.forEach((x) => { n[x.status] = (n[x.status] || 0) + 1; });
    return { ...n, total: sel.length };
  }, [batchQueue]);
  // 失败条数按整张清单算（不受取消勾选影响），决定「重试全部失败」是否出现
  const failedCount = batchQueue.filter((x) => x.status === 'failed').length;

  /* 已受理的任务逐个查 /tasks/{id}：顺序轮询，避免 50 条同时打接口。
     完成或失败后该 id 退出轮询集合，effect 依赖自动收窄。 */
  const acceptedKey = batchQueue.filter((x) => x.status === 'accepted').map((x) => x.id).join(',');
  useEffect(() => {
    if (!acceptedKey) return undefined;
    const ids = acceptedKey.split(',').map(Number);
    let stop = false;
    let timer = null;
    const tick = async () => {
      for (const id of ids) {
        if (stop) return;
        const it = batchQueueRef.current.find((x) => x.id === id);
        if (!it || it.status !== 'accepted') continue;
        try {
          const t = await api('/tasks/' + it.taskId);
          if (t.status === 'ready') { patchBatch(id, { status: 'done', progress: 100 }); loadList(); }
          else if (t.status === 'failed') patchBatch(id, { status: 'failed', error: shortErr(t.error_message || '任务失败') });
          else if ((t.progress || 0) !== it.progress) patchBatch(id, { progress: t.progress || 0 });
        } catch { /* 单次轮询失败不判负，下一轮再试 */ }
      }
      if (!stop) timer = setTimeout(tick, 2400);
    };
    timer = setTimeout(tick, 1200);
    return () => { stop = true; clearTimeout(timer); };
  }, [acceptedKey, loadList]);

  const mdNote = notes.find((n) => n.kind === 'markdown');
  const outlineNote = notes.find((n) => n.kind === 'outline');
  const summaryNote = notes.find((n) => n.kind === 'summary');
  const qaNote = notes.find((n) => n.kind === 'qa');

  /* 时间轴只列章节级关键点（后端从 Markdown 的 ## 标题抽），不摊上千段转写 */
  const keypoints = useMemo(() => (mdNote?.points?.length ? mdNote.points : []), [mdNote]);

  const steps = [
    { k: 'source', label: '视频源', done: !!docId },
    { k: 'asr', label: '转写', done: transcript.length > 0 },
    { k: 'note', label: '笔记', done: notes.length > 0 },
    { k: 'visual', label: '配图', done: frames.length > 0 || (mdNote?.content || '').includes('/api/videos/frames') },
  ];

  const tabs = [
    { key: 'markdown', label: '笔记', has: !!mdNote },
    { key: 'summary', label: '摘要', has: !!summaryNote },
    { key: 'outline', label: '大纲', has: !!outlineNote },
    { key: 'qa', label: '问答', has: !!qaNote },
    { key: 'frames', label: '图文', has: frames.length > 0 },
    { key: 'transcript', label: '文稿', has: transcript.length > 0 },
  ];

  /* 笔记里的图片（alt=mm:ss）与 [mm:ss] 链接都拦截成 seek，不跳新页 */
  const onNoteClick = (e) => {
    const img = e.target.closest('img');
    if (img) {
      const m = (img.getAttribute('alt') || '').match(/^(\d{1,2}):(\d{2})$/);
      if (m) { e.preventDefault(); seek(Number(m[1]) * 60 + Number(m[2])); }
      return;
    }
    const a = e.target.closest('a');
    if (a) {
      const mm = (a.getAttribute('href') || '').match(/[?&]t=(\d+)/);
      if (mm) { e.preventDefault(); seek(Number(mm[1])); }
    }
  };

  const FrameStrip = ({ big }) => (
    <div className="fstrip">
      {frames.map((f, i) => (
        <div className={'fthumb' + (big ? ' lg' : '')} key={i} title={(f.text || '').slice(0, 160)}
          onClick={() => seek(Number(f.ts) || 0)}>
          <img src={`/api/videos/frames/${encodeURIComponent(f.name || '')}`} loading="lazy" alt={`帧 ${i + 1}`} />
          <span className="fts">{f.ts_label || fmtTs(f.ts)}</span>
        </div>
      ))}
    </div>
  );

  return (
    <div className="vpage">
      <div className="vsteps" style={{ flexWrap: 'wrap' }}>
        {steps.map((s, i) => (
          <div key={s.k} className={'vstep' + (s.done ? ' on' : '')}>
            <span className="vstep-dot">{s.done ? '✓' : i + 1}</span><span>{s.label}</span>
          </div>
        ))}
        {busy && <Progress percent={99} size="small" showInfo={false} status="active" style={{ width: 120, marginLeft: 'auto' }} />}
        <span className="row" style={{ gap: 4, marginLeft: 'auto' }}>
          <Button size="small" type="default" loading={exporting} disabled={!docId || exporting}
            onClick={exportMd}>导出 Markdown</Button>
          <Button size="small" type="text" icon={leftCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={toggleLeft} title={leftCollapsed ? '展开左侧列表' : '收起左侧列表'} />
          <Button size="small" type="text" icon={rightCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={toggleRight} title={rightCollapsed ? '展开右侧笔记' : '收起右侧笔记'} />
        </span>
      </div>

      <div className={'vgrid' + (leftCollapsed ? ' no-left' : '') + (rightCollapsed ? ' no-right' : '')}>
        {!leftCollapsed && <aside className="vcol-left">
          <div className="v3-card vpad">
            <Upload.Dragger multiple={false} showUploadList={false} disabled={busy}
              accept="video/*,audio/*" beforeUpload={(f) => { uploadFile(f); return false; }}>
              <p style={{ margin: 0 }}><InboxOutlined style={{ fontSize: 22, color: 'var(--primary)' }} /></p>
              <p className="vmuted">拖视频/音频到这里</p>
              <p className="vmuted2">MP4 / MKV / MP3 / WAV</p>
            </Upload.Dragger>
            <div className="vlink">
              <Input size="small" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="粘贴 B站 / YouTube 链接" />
              <Button size="small" type="primary" loading={busy} onClick={uploadUrl}>解析</Button>
            </div>
            <div className="vchips">
              {TPL.map((t) => (
                <Tag.CheckableTag key={t.key} checked={tpls.includes(t.key)} onChange={() => toggleTpl(t.key)}>{t.label}</Tag.CheckableTag>
              ))}
            </div>
            <div className="row between" style={{ marginTop: 8, gap: 4 }}>
              <span className="vmuted2">单批最多 {BATCH_MAX} 条</span>
              <Button size="small" type="link" style={{ padding: 0, height: 'auto' }}
                onClick={() => setBatchOpen(true)}>批量导入</Button>
            </div>
            {batchQueue.length > 0 && (
              <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border)' }}>
                <div className="row between" style={{ gap: 4 }}>
                  <span className="vmuted2" style={{ fontVariantNumeric: 'tabular-nums', lineHeight: 1.8 }}>
                    排队 {batchStat.queued} · 提交中 {batchStat.submitting} · 转写中 {batchStat.accepted}
                    {' · '}已完成 {batchStat.done} · 失败 {batchStat.failed}
                  </span>
                  <Button size="small" type="link" style={{ padding: 0, height: 'auto' }}
                    onClick={() => setBatchOpen(true)}>查看</Button>
                </div>
              </div>
            )}
            {stage && <div className="vmuted2" style={{ marginTop: 6 }}>{stage}</div>}
          </div>

          <div className="v3-card vpad vlist">
            <div className="v3-sh">历史视频<span className="meta">{list.length}</span></div>
            {list.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有视频" />}
            {list.map((x) => (
              <div key={x.document_id} className={'vitem' + (Number(x.document_id) === docId ? ' on' : '')}
                onClick={() => openVideo(x.document_id)}>
                <div className="vitem-t">{esc(x.title || '未命名')}</div>
                <div className="vitem-m">
                  {(x.notes || []).filter((n) => n.kind !== 'transcript').slice(0, 4)
                    .map((n) => <span key={n.kind} className="vkind">{noteKindCn(n.kind)}</span>)}
                  <span className="vdel" onClick={(e) => { e.stopPropagation(); del(x.document_id); }}>删除</span>
                </div>
              </div>
            ))}
          </div>
        </aside>}

        <section className="vcol-mid">
          <div className="vplayer">
            {docId ? (
              <video ref={videoRef} controls preload="metadata" src={`/api/videos/${docId}/stream`}
                onLoadedMetadata={onLoadedMetadata}
                onError={() => message.warning('该来源无法直接播放，可用关键点定位')} />
            ) : <div className="vph">选择或解析一个视频</div>}
          </div>

          <div className="v3-card vpad">
            <div className="v3-sh">关键点<span className="meta">{keypoints.length} 个</span></div>
            {keypoints.length ? (
              <div className="vkps">
                {keypoints.map((k, i) => (
                  <div className="vkp" key={i} onClick={() => seek(k.ts)}>
                    <span className="vt">{fmtTs(k.ts)}</span>
                    <span className="vkp-l">{esc(k.label)}</span>
                  </div>
                ))}
              </div>
            ) : <div className="vmuted2">生成「笔记」后这里会列章节级关键点</div>}
          </div>

          {frames.length > 0 && (
            <div className="v3-card vpad">
              <div className="v3-sh">关键帧<span className="meta">{frames.length} 张</span></div>
              <FrameStrip />
            </div>
          )}
        </section>

        {!rightCollapsed && <section className="vcol-right v3-card">
          {/* v7l 队列概览：提交中/转写中/排队/完成/失败 五态 */}
          <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--line-soft)' }}>
            <div className="row between" style={{ marginBottom: 6 }}>
              <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--muted-foreground)' }}>队列概览</span>
            </div>
            <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
              {[
                { k: '提交中', v: batchStat.submitting, c: 'var(--primary)' },
                { k: '转写中', v: batchStat.accepted, c: 'var(--warning)' },
                { k: '排队', v: batchStat.queued, c: 'var(--muted-foreground)' },
                { k: '完成', v: batchStat.done, c: 'var(--success)' },
                { k: '失败', v: batchStat.failed, c: 'var(--danger)' },
              ].map((s) => (
                <span key={s.k} style={{
                  fontSize: 10.5, padding: '2px 8px', borderRadius: 99,
                  background: 'var(--secondary)', color: s.c,
                }}>{s.k} <b className="num">{s.v}</b></span>
              ))}
            </div>
          </div>
          <div className="vtabs">
            {tabs.map((t) => (
              <button key={t.key} type="button" disabled={!t.has}
                className={'vtab' + (active === t.key ? ' on' : '')}
                onClick={() => setActive(t.key)}>{t.label}</button>
            ))}
            <span className="vtitle">{esc(title)}</span>
          </div>

          <div className="vbody" onClick={onNoteClick}>
            {active === 'markdown' && (mdNote ? <Markdown text={mdNote.content} className="vnote" /> : <Empty description="没有 Markdown 笔记" />)}
            {active === 'summary' && (summaryNote ? <Markdown text={summaryNote.content} className="vnote" /> : <Empty description="没有摘要" />)}
            {active === 'outline' && (outlineNote
              ? <MindMap markdown={outlineNote.content} />
              : <Empty description="没有大纲" />)}
            {active === 'qa' && (qaNote ? <Markdown text={qaNote.content} className="vnote" /> : <Empty description="没有问答" />)}
            {active === 'frames' && (frames.length ? <FrameStrip big /> : <Empty description="没有关键帧（音频源或已关闭网格 OCR）" />)}
            {active === 'transcript' && (
              <div>
                <Input.Search size="small" allowClear value={q} loading={searching}
                  placeholder="在文稿里找一句话" onChange={onSearchChange}
                  onSearch={runSearch} style={{ marginBottom: 8 }} />
                {hits?.length ? (
                  <>
                    <div className="vmuted2" style={{ marginBottom: 4, fontVariantNumeric: 'tabular-nums' }}>
                      命中 {hitTotal} 处{hitTotal > hits.length ? `，显示前 ${hits.length} 条` : ''}
                    </div>
                    <div className="vtl">
                      {hits.map((h) => (
                        <div className="vseg" key={h.chunk_index} onClick={() => seek(Number(h.start_sec) || 0)}>
                          <span className="vt">{h.start_sec == null ? '—' : fmtTs(h.start_sec)}</span>
                          <span>{hitParts(h.snippet)}</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : hits ? (
                  <div className="vmuted2">没有找到匹配内容</div>
                ) : (
                  <div className="vtl">
                    {transcript.map((x, i) => (
                      <div className="vseg" key={i} onClick={() => seek(Number(x.start) || 0)}>
                        <span className="vt">{fmtTs(x.start)}</span><span>{esc(x.text)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>}
      </div>

      <Modal open={batchOpen} title="批量导入视频" width="min(680px, calc(100vw - 24px))"
        onCancel={() => setBatchOpen(false)}
        footer={[
          <Button key="close" onClick={() => setBatchOpen(false)}>关闭</Button>,
          <Button key="run" type="primary" loading={batchRun} disabled={!batchStat.queued} onClick={runBatch}>
            {batchRun ? '提交中…' : `开始提交${batchStat.queued ? `（${batchStat.queued}）` : ''}`}
          </Button>,
        ]}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="vmuted2" style={{ lineHeight: 1.8 }}>
            每行一个视频链接，或一次选择多个本地文件。提交按顺序进行，转写由服务端并发处理。
          </div>
          <Input.TextArea value={batchText} rows={4} onChange={(e) => setBatchText(e.target.value)}
            placeholder={'https://www.bilibili.com/video/BV...\nhttps://b23.tv/...'} />
          <div className="row" style={{ gap: 8 }}>
            <Button size="small" onClick={addBatchUrls}>加入链接</Button>
            <Button size="small" onClick={() => batchFileRef.current?.click()}>选择文件</Button>
            {batchQueue.length > 0 && (
              <Button size="small" type="text" disabled={batchRun} onClick={() => setBatchQueue([])}>清空清单</Button>
            )}
            {failedCount > 0 && (
              <Button size="small" type="text" onClick={retryAllFailed}>重试全部失败</Button>
            )}
            <span className="vmuted2" style={{ marginLeft: 'auto', fontVariantNumeric: 'tabular-nums' }}>
              {batchQueue.length} / {BATCH_MAX}
            </span>
            <input ref={batchFileRef} type="file" hidden multiple accept="video/*,audio/*"
              onChange={(e) => { addBatchFiles(e.target.files); e.target.value = ''; }} />
          </div>

          {batchQueue.length === 0 ? (
            <div className="vmuted2" style={{ padding: '16px 0', textAlign: 'center' }}>
              清单为空，粘贴链接或选择文件后点「加入」
            </div>
          ) : (
            <div style={{ maxHeight: 260, overflow: 'auto', border: '1px solid var(--border)', borderRadius: 8 }}>
              {batchQueue.map((x) => (
                <div key={x.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
                  <Checkbox checked={x.selected} disabled={batchRun || x.status !== 'queued'}
                    onChange={() => setBatchQueue((q) => q.map((y) => (y.id === x.id ? { ...y, selected: !y.selected } : y)))} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div title={x.name} style={{ fontSize: 12.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {x.name}
                    </div>
                    {x.error && (
                      <div style={{ fontSize: 11.5, color: 'var(--destructive)', marginTop: 2, wordBreak: 'break-all' }}>
                        {x.error}
                      </div>
                    )}
                    {x.status === 'accepted' && x.progress > 0 && (
                      <div className="vmuted2" style={{ marginTop: 2, fontVariantNumeric: 'tabular-nums' }}>
                        转写进度 {x.progress}%
                      </div>
                    )}
                  </div>
                  <span style={{ fontSize: 11.5, color: BATCH_TONE[x.status], whiteSpace: 'nowrap', lineHeight: 1.8 }}>
                    {BATCH_CN[x.status]}
                  </span>
                  {x.status === 'failed' && (
                    <Button size="small" type="link" style={{ padding: 0, height: 'auto', whiteSpace: 'nowrap' }}
                      onClick={() => retryOne(x.id)}>重试</Button>
                  )}
                  <Button size="small" type="link" danger disabled={batchRun} style={{ padding: 0, height: 'auto' }}
                    onClick={() => setBatchQueue((q) => q.filter((y) => y.id !== x.id))}>移除</Button>
                </div>
              ))}
            </div>
          )}

          {(batchStat.done > 0 || batchStat.failed > 0) && (
            <div className="vmuted2" style={{ fontVariantNumeric: 'tabular-nums' }}>
              已提交 {batchStat.accepted + batchStat.done + batchStat.failed}
              {' · '}已完成 {batchStat.done} · 转写中 {batchStat.accepted} · 失败 {batchStat.failed}
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
