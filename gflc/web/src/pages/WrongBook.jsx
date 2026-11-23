import React, { useMemo, useState } from 'react';
import { Button, Select, Tag, Tooltip } from 'antd';
import { ArrowRightOutlined, PrinterOutlined, RedoOutlined } from '@ant-design/icons';
import { esc } from '../utils.js';

const TYPE_CN = { single: '单选题', multiple: '多选题', fill: '填空题', short: '简答题' };
const PAGE_SIZE = 20;

function meta(q) {
  return (
    <div className="wrong-meta">
      <Tag color="error">错 {q.wrong_count || 1} 次</Tag>
      <Tag>{q.chapter || '未分章'}</Tag>
      <Tag>{TYPE_CN[q.qtype] || '题目'}</Tag>
      <span className="wrong-ans">
        你 {esc((q.last_answer || '—').slice(0, 12))} · 答案 {esc((q.answer || '—').slice(0, 12))}
      </span>
    </div>
  );
}

/* 刷题页右栏的错题概览：只读，最多 5 条，全部在「错题」模式里处理。 */
export function WrongPreview({ wrong, onMore }) {
  const list = (wrong || []).slice(0, 5);
  if (!list.length) return <div className="muted" style={{ fontSize: 12.5, padding: '4px 0' }}>暂无错题，继续保持</div>;
  return (
    <div>
      {list.map((q) => (
        <div className="wrong-item" key={q.id}>
          <div className="wrong-main">
            <div className="wrong-stem">{esc(q.stem || '')}</div>
            {meta(q)}
          </div>
        </div>
      ))}
      {wrong.length > list.length && (
        <Button size="small" type="text" onClick={onMore} style={{ marginTop: 8 }}>
          查看全部 {wrong.length} 题
        </Button>
      )}
    </div>
  );
}

/* 错题本：章节 + 题型筛选、单题重做、分页、导出打印。 */
export default function WrongBook({ wrong, onRedo, onRetryChapter }) {
  const [chapter, setChapter] = useState('');
  const [qtype, setQtype] = useState('');
  const [page, setPage] = useState(1);

  const chapters = useMemo(() => {
    const seen = new Set();
    (wrong || []).forEach((q) => { if (q.chapter) seen.add(q.chapter); });
    return [...seen];
  }, [wrong]);
  const types = useMemo(() => {
    const seen = new Set();
    (wrong || []).forEach((q) => { if (q.qtype) seen.add(q.qtype); });
    return [...seen];
  }, [wrong]);

  const filtered = useMemo(() => (wrong || []).filter((q) => (
    (!chapter || (q.chapter || '') === chapter) && (!qtype || q.qtype === qtype)
  )), [wrong, chapter, qtype]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pages);
  const rows = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  const resetPage = (fn) => { fn(); setPage(1); };

  return (
    <div>
      <div className="v3-sh no-print">
        错题本
        <span className="meta">{filtered.length} / {(wrong || []).length} 题</span>
      </div>

      <div className="wrong-filter no-print">
        <Select
          size="small"
          value={chapter}
          onChange={(v) => resetPage(() => setChapter(v))}
          style={{ width: 160 }}
          options={[{ value: '', label: '全部章节' }, ...chapters.map((c) => ({ value: c, label: c }))]}
        />
        <Select
          size="small"
          value={qtype}
          onChange={(v) => resetPage(() => setQtype(v))}
          style={{ width: 120 }}
          options={[{ value: '', label: '全部题型' }, ...types.map((t) => ({ value: t, label: TYPE_CN[t] || t }))]}
        />
        <Tooltip title={chapter ? '只练这一章的错题' : '先在左侧选一个章节'}>
          <Button size="small" icon={<ArrowRightOutlined />} disabled={!chapter}
            onClick={() => onRetryChapter(chapter)}>只此章节</Button>
        </Tooltip>
        <span style={{ flex: 1 }} />
        <Button size="small" icon={<PrinterOutlined />} onClick={() => window.print()}>导出错题</Button>
      </div>

      {!filtered.length ? (
        <div className="muted" style={{ fontSize: 12.5, padding: '20px 0' }}>
          {wrong?.length ? '这个筛选下没有错题' : '暂无错题，继续保持'}
          {wrong?.length ? <Button size="small" type="text" onClick={() => resetPage(() => { setChapter(''); setQtype(''); })}>清除筛选</Button> : null}
        </div>
      ) : (
        <div className="screen-only">
          {rows.map((q) => (
            <div className="wrong-item" key={q.id}>
              <div className="wrong-main">
                <div className="wrong-stem">{esc(q.stem || '')}</div>
                {meta(q)}
              </div>
              <div className="wrong-act">
                <Button size="small" icon={<RedoOutlined />} onClick={() => onRedo(q)}>重做</Button>
              </div>
            </div>
          ))}
          {filtered.length > PAGE_SIZE && (
            <div className="wrong-pager">
              <span>第 {safePage} / {pages} 页</span>
              <span className="row" style={{ gap: 8 }}>
                <Button size="small" disabled={safePage <= 1} onClick={() => setPage(safePage - 1)}>上一页</Button>
                <Button size="small" disabled={safePage >= pages} onClick={() => setPage(safePage + 1)}>下一页</Button>
              </span>
            </div>
          )}
        </div>
      )}

      <div className="print-only wrong-print">
        <div className="print-title">错题本</div>
        <div className="print-sub">
          共 {filtered.length} 题 · {new Date().toLocaleDateString('zh-CN')}
          {chapter ? ` · ${chapter}` : ''}{qtype ? ` · ${TYPE_CN[qtype] || qtype}` : ''}
        </div>
        {filtered.map((q, i) => (
          <div className="wrong-item" key={q.id}>
            <div className="wrong-main">
              <div className="wrong-stem">{i + 1}. {esc(q.stem || '')}</div>
              <div className="wrong-meta">
                <span className="wrong-ans">你 {esc(q.last_answer || '—')} · 答案 {esc(q.answer || '—')}</span>
                <span className="wrong-ans">错 {q.wrong_count || 1} 次 · {q.chapter || '未分章'}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
