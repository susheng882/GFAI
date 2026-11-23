/* 统一 API 层：base=/api、HttpOnly Cookie（credentials:'include'）、错误集中处理。
   契约与旧前端 index.html:845 保持一致：成功返回 data 字段，失败抛 Error。 */
const BASE = '/api';

export class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

export async function api(path, opts = {}) {
  const isForm = opts.body instanceof FormData;
  let res;
  try {
    res = await fetch(BASE + path, {
      credentials: 'include',
      ...opts,
      headers: isForm
        ? { ...(opts.headers || {}) }
        : { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    });
  } catch (e) {
    throw new ApiError('网络异常，无法连接服务：' + (e.message || e), 0);
  }
  let data = null;
  try { data = await res.json(); } catch { /* 空响应体允许 */ }
  if (!res.ok || (data && data.ok === false)) {
    const err = data && (data.error || data.detail);
    const message = (typeof err === 'string' ? err : err && err.message)
      || (data && data.message) || ('请求失败 ' + res.status);
    throw new ApiError(message, res.status, typeof err === 'object' && err && err.code);
  }
  return data ? data.data : null;
}

/* NDJSON 流式问答：逐行回调 onEvent；与后端 qa.py:568 的事件协议一致。
   status → sources → delta* →（notice）→ done / error。 */
export async function streamQA({ question, strategy = 'auto', documentId, onEvent, signal }) {
  const body = { question, strategy };
  if (documentId) body.document_id = documentId;
  const res = await fetch(BASE + '/qa/stream', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new ApiError('问答请求失败 ' + res.status, res.status);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let nl;
    while ((nl = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, nl);
      buffer = buffer.slice(nl + 1);
      if (!line.trim()) continue;
      try { onEvent(JSON.parse(line)); } catch { /* 忽略半行/坏行，不中断流 */ }
    }
  }
  if (buffer.trim()) {
    try { onEvent(JSON.parse(buffer)); } catch { /* 忽略尾行 */ }
  }
}

/* ---------- 后台任务坞（旧版 TASKS/renderDock 的 React 版） ---------- */
const taskState = new Map();
const listeners = new Set();
// useSyncExternalStore 要求 getSnapshot 在无变化时返回同一引用，否则每帧都判定"变了"
// 而无限重渲染（React #185 白屏）。这里在 emit 时重建一次并缓存。
let taskSnapshot = Object.freeze([]);
function rebuildSnapshot() {
  taskSnapshot = Object.freeze(Array.from(taskState.entries()).map(([id, t]) => Object.freeze({ id, ...t })));
}
function emit() { rebuildSnapshot(); listeners.forEach((fn) => fn()); }
export const taskStore = {
  subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
  getSnapshot() { return taskSnapshot; },
};

export const TYPE_CN = {
  pdf_parse: '解析 PDF', card_generate: '生成卡片', question_import: '导入题库',
  plan_generate: '生成计划', video_upload: '视频转写', video_url: '链接视频',
  dashboard_generate: '生成仪表盘', question_generate: '生成题库',
};
export const STATUS_CN = { pending: '排队中', running: '进行中', ready: '已完成', failed: '失败' };

/* 错误信息脱敏：去掉本机绝对路径（旧前端 shortErr 等价实现）。 */
export function shortErr(msg) {
  if (!msg) return '';
  return String(msg)
    .replace(/[A-Za-z]:\\[^\s;，、]*/g, '（本地临时文件）')
    .replace(/\s+/g, ' ').trim().slice(0, 70);
}

/* 提交后台任务并轮询到 ready；进度写入 taskStore 供 TaskDock 展示。 */
export async function runTask(path, opts, label) {
  const created = await api(path, opts);
  if (!created || !created.task_id) return created;
  const id = created.task_id;
  taskState.set(id, { label, progress: 0, status: 'running', error: '' });
  emit();
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  for (let i = 0; i < 900; i++) {
    await sleep(700);
    let task;
    try { task = await api('/tasks/' + id); } catch (e) {
      taskState.delete(id); emit(); throw e;
    }
    taskState.set(id, {
      label, progress: task.progress || 0, status: task.status,
      error: shortErr(task.error_message || ''),
    });
    emit();
    if (task.status === 'failed') {
      setTimeout(() => { taskState.delete(id); emit(); }, 5000);
      throw new ApiError(task.error_message || '任务失败');
    }
    if (task.status === 'ready') {
      setTimeout(() => { taskState.delete(id); emit(); }, 1400);
      return task.result || {};
    }
  }
  taskState.delete(id); emit();
  throw new ApiError('任务超时');
}

/* 浏览器侧下载文本：vault 导出用，避免把文件流当 JSON 解析 */
export function downloadText(filename, text) {
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
