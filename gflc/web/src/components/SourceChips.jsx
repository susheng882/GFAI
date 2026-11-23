import React from 'react';
import { useNavigate } from 'react-router-dom';
import { LinkOutlined, ClockCircleOutlined, FileTextOutlined } from '@ant-design/icons';
import { fmtTs } from '../utils.js';

/* ============================================================
   S4 来源跳转（前端）
   后端 QA 事件 sources 每项含 kind/chunk_id/page/ts_start/title，
   可能附带 document_id / file_url（字段只增不改，缺省时容错）。
   点击规则：
     · kind=web / 有 url        → 新标签打开原文链接
     · ts_start > 0             → 视频类：跳 /video?doc=..&ts=..，
                                  VideoPage 调用 <video>.currentTime = ts 实现 ≤2s 定位
     · page > 0（默认）          → 文档类：跳 /docs?doc=..&page=..，
                                  DocumentsPage 打开定位抽屉显示对应页
   解析文档 id 优先用 source.document_id，其次当前问答限定文档，最后按标题匹配资料列表。
   ============================================================ */
export function resolveSourceDocument(source, documents = [], currentDocumentId) {
  if (source?.document_id) return source.document_id;
  if (currentDocumentId) return currentDocumentId;
  const title = String(source?.title || '').trim();
  if (!title) return null;
  const docs = documents || [];
  const exact = docs.find((d) => d.title === title);
  if (exact) return exact.id;
  const fuzzy = docs.find((d) => {
    const t = String(d.title || '');
    return (t && title.includes(t)) || (t && t.includes(title));
  });
  return fuzzy ? fuzzy.id : null;
}

const MODE_BADGE = {
  knowledge: { text: '知识库', cls: 'blue' },
  web: { text: '联网检索', cls: 'warn' },
  model: { text: '学科知识', cls: '' },
  hybrid: { text: '资料+联网', cls: 'blue' },
  none: { text: '未找到依据', cls: '' },
  note: { text: '我的笔记', cls: 'blue' },
};

export default function SourceChips({ sources = [], mode, documents = [], currentDocumentId }) {
  const navigate = useNavigate();
  if (!sources.length && !mode) return null;
  const badge = MODE_BADGE[mode];
  const jump = (s) => {
    if (s.url) {
      window.open(s.url, '_blank', 'noopener,noreferrer');
      return;
    }
    const docId = resolveSourceDocument(s, documents, currentDocumentId);
    const ts = Number(s.ts_start);
    if (s.source_type === 'note') {
      navigate('/notes');
    } else if (ts > 0 || s.source_type === 'video') {
      navigate(`/video?doc=${docId || ''}&ts=${ts}`);
    } else {
      navigate(`/docs?doc=${docId || ''}&page=${Number(s.page) || 1}`);
    }
  };
  return (
    <div className="src">
      {badge && <span className={`badge ${badge.cls}`}>{badge.text}</span>}
      {sources.map((s, i) => {
        const ts = Number(s.ts_start);
        const isVideo = ts > 0 || s.source_type === 'video';
        const label = s.url
          ? (s.title || s.url)
          : s.source_type === 'note'
            ? (s.title || '我的笔记')
            : isVideo
              ? <><ClockCircleOutlined /> {ts > 0 ? fmtTs(ts) : '视频'}</>
              : s.page
                ? <><FileTextOutlined /> 第 {s.page} 页</>
                : (s.title || '资料片段');
        const tip = [
          s.chunk_id != null && `chunk_id=${s.chunk_id}`,
          s.page != null && `page=${s.page}`,
          ts > 0 && `ts_start=${ts}`,
        ].filter(Boolean).join(' · ');
        return (
          <span
            key={i}
            className={'s' + (ts > 0 ? ' ts' : '')}
            title={tip ? `点击跳转 · ${tip}` : '点击跳转原文'}
            onClick={() => jump(s)}
            role="link"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter') jump(s); }}
            style={{ cursor: 'pointer' }}
          >
            {s.url && <LinkOutlined />}{label}
          </span>
        );
      })}
    </div>
  );
}
