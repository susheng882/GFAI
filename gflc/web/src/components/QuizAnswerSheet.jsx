import React from 'react';
import { Button, Modal } from 'antd';

/* 答题卡浮层：题号四态（未答 / 已答 / 疑题 / 当前），点格跳题，底部交卷。
   题号与作答状态全部来自测试态的本地 state，不请求后端。 */
export default function QuizAnswerSheet({
  open, questions, answers, flagged, idx, busy, onJump, onClose, onSubmit,
}) {
  const list = questions || [];
  const done = list.filter((q) => (answers?.[q.id] || '').trim()).length;
  const left = list.length - done;

  return (
    <Modal open={open} onCancel={onClose} footer={null} width={432} centered className="sheet-modal">
      <div className="sheet-head">
        <span className="sheet-t">答题卡</span>
        <span className="sheet-meta">已答 {done} / {list.length}</span>
      </div>
      <div className="sheet-legend">
        <span><i className="lg-blank" />未答</span>
        <span><i className="lg-on" />已答</span>
        <span><i className="lg-flag" />疑题</span>
        <span><i className="lg-cur" />当前</span>
      </div>
      <div className="sheet-grid">
        {list.map((q, i) => {
          const filled = !!(answers?.[q.id] || '').trim();
          const cls = [
            'sheet-cell',
            filled ? 'on' : '',
            flagged?.[q.id] ? 'flag' : '',
            i === idx ? 'cur' : '',
          ].filter(Boolean).join(' ');
          return (
            <button
              key={q.id ?? i}
              type="button"
              className={cls}
              onClick={() => onJump(i)}
              aria-label={`第 ${i + 1} 题${filled ? '，已答' : '，未答'}${flagged?.[q.id] ? '，已标记' : ''}`}
            >
              {i + 1}
            </button>
          );
        })}
      </div>
      <div className="sheet-foot">
        <span className="muted" style={{ fontSize: 11.5 }}>
          {left ? `还有 ${left} 题未作答` : '已全部作答'}
        </span>
        <span className="row" style={{ gap: 8 }}>
          <Button size="small" onClick={onClose}>继续作答</Button>
          <Button size="small" type="primary" loading={busy} onClick={onSubmit}>交卷并查看结果</Button>
        </span>
      </div>
    </Modal>
  );
}
