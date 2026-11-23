/* 纯函数工具集（旧前端同名函数的等价实现）。 */
export const esc = (v) => String(v ?? '');

export function fmtTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  if (isNaN(d.getTime())) return '—';
  const diff = (Date.now() - d.getTime()) / 86400000;
  if (diff < 1) return '今天';
  if (diff < 2) return '昨天';
  if (diff < 7) return Math.floor(diff) + ' 天前';
  return d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' });
}

export function fmtTs(sec) {
  const s = Math.max(0, Math.round(sec || 0));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return String(m).padStart(2, '0') + ':' + String(r).padStart(2, '0');
}

export function summarize(result) {
  if (!result) return '';
  const parts = [];
  if (result.cards != null) parts.push(result.cards + ' 张卡片');
  if (result.chunks != null) parts.push(result.chunks + ' 块');
  if (result.questions != null) parts.push(result.questions + ' 题');
  if (result.plan_id != null) parts.push('计划#' + result.plan_id);
  if (result.layout_id != null) parts.push('布局#' + result.layout_id);
  if (result.segments != null) parts.push(result.segments + ' 段');
  return parts.join(' · ') || JSON.stringify(result).slice(0, 60);
}

export function reviewsText(reviewed, total) {
  const t = +total || 0;
  if (!t) return '还没有卡片';
  return `已复习 ${Math.min(100, Math.round((+reviewed || 0) / t * 100))}%`;
}

export const pct = (x) => Math.round((+x || 0) * 100);
export const stCn = (s) => ({ pending: '待解析', parsing: '解析中', ready: '就绪', failed: '失败' }[s] || s);
export const sourceCn = (s) => ({ manual: '手记', ai: 'AI', video: '视频', import: '导入' }[s] || '笔记');
export const noteKindCn = (k) => ({ summary: '摘要', outline: '大纲', qa: '问答', frames: '图文', markdown: '笔记', transcript: '文稿' }[k] || k || '笔记');

/* 追问建议：按策略给三条，与旧前端 genFollowups 一致。 */
export function genFollowups(mode) {
  const base = mode === 'web'
    ? ['这个结论有最新数据吗？', '能给出官方网站出处吗？', '换一个观点对比一下']
    : mode === 'knowledge'
      ? ['能标出具体页码吗？', '这部分怎么用在题目里？', '还有相关的其他考点吗？']
      : ['能举一个具体的例子吗？', '能再简化一点吗？', '展开讲讲推导过程'];
  return base.slice(0, 3);
}

/* 来源文本：用于「检索依据」展开区，不伪造推理过程。 */
export function sourceTrace(items) {
  return (items || []).map((s) => {
    if (s.url) return `联网：${s.title || s.url}`;
    if (s.page) return `资料第 ${s.page} 页` + (s.title ? ` · ${s.title}` : '');
    return s.title || '资料片段';
  }).slice(0, 5);
}

/* Markdown 转简单树（视频大纲用），与旧前端 mdToTree 一致。 */
export function mdToTree(md) {
  const root = { children: [] };
  const stack = [{ level: 0, node: root }];
  (md || '').split('\n').forEach((line) => {
    if (!line.trim()) return;
    let m, level, text;
    if ((m = line.match(/^(#{1,4})\s+(.*)$/))) { level = m[1].length; text = m[2]; }
    else if ((m = line.match(/^\s*[-*]\s+(.*)$/))) { level = 6; text = m[1]; }
    else { level = 7; text = line; }
    text = text.replace(/\*\*/g, '').trim();
    if (!text) return;
    const node = { text, level, children: [] };
    while (stack.length > 1 && stack[stack.length - 1].level >= level) stack.pop();
    stack[stack.length - 1].node.children.push(node);
    stack.push({ level, node });
  });
  return root.children;
}

/* PlanTask 的「今天」判定：优先用后端新增的 due 字段，缺省回退 day_index===1。 */
export function isTodayTask(task) {
  if (!task || task.done) return false;
  if (task.due) {
    const d = new Date(task.due);
    if (!isNaN(d.getTime())) return d.toDateString() === new Date().toDateString();
    return String(task.due).slice(0, 10) === new Date().toISOString().slice(0, 10);
  }
  return +task.day_index === 1 || +task.day === 1;
}
