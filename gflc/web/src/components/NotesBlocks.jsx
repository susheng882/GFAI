import React, { useState } from 'react';
import { Button, Modal, Segmented, Tabs } from 'antd';
import { DatabaseOutlined, LinkOutlined, ReloadOutlined } from '@ant-design/icons';
import { esc } from '../utils.js';

/* 笔记模块的可复用小块：模板库 / vault 状态条 / 成卡行 / AI 速览 / 右侧栏。
   放在独立文件是为了让 NotesPage 保持单文件不超 600 行。 */

export const AI_MODES = [
  { label: '润色', value: 'improve' }, { label: '扩展', value: 'expand' },
  { label: '提炼', value: 'summarize' }, { label: '出题', value: 'quiz' },
];

/* 模板内容全部走 GFLC 自定结构，不使用任何竞品专有符号 */
export const NOTE_TEMPLATES = [
  {
    key: 'blank', name: '空白笔记', desc: '从零开始写',
    content: '',
  },
  {
    key: 'class', name: '课堂笔记', desc: '概念、重点与待复习',
    content: [
      '# 课堂笔记', '', '## 基本信息', '- 课程：', '- 日期：', '- 章节：', '',
      '## 核心概念', '- ', '', '## 重点与易错点', '- ', '', '## 待复习', '- ',
    ].join('\n'),
  },
  {
    key: 'mistake', name: '错题复盘', desc: '错因、思路与同类题',
    content: [
      '# 错题复盘', '', '## 题目', '- ', '', '## 错因', '- ', '',
      '## 正确思路', '- ', '', '## 同类题成卡',
      '判断这类题的关键特征 :: 对应的解题步骤',
    ].join('\n'),
  },
  {
    key: 'read', name: '读书摘要', desc: '观点、摘录与思考',
    content: [
      '# 读书摘要', '', '## 书目信息', '- ', '', '## 核心观点', '- ', '',
      '## 金句摘录', '- ', '', '## 我的思考', '- ',
    ].join('\n'),
  },
];

/* 简单稳定哈希（FNV-1a 变体），用于成卡行的 hash 校验与块锚 ID */
export function hashText(text) {
  let h = 0x811c9dc5;
  const s = String(text ?? '');
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, '0');
}

/* 解析「正面 :: 背面」行；:: 为 GFLC 自定语法，不抄竞品 == / >> */
export function parseAnchorLines(content) {
  return String(content || '').split('\n').map((line, i) => {
    const m = line.match(/^\s*(?:[-*+]\s+)?(.+?)\s*::\s*(.+?)\s*$/);
    if (!m) return null;
    const front = m[1].trim();
    const back = m[2].trim();
    if (!front || !back) return null;
    return {
      line: i + 1, front, back,
      hash: hashText(front + '\u0000' + back),
      anchor: 'ln' + (i + 1) + '-' + hashText(front).slice(0, 6),
    };
  }).filter(Boolean);
}

const VAULT_LABEL = {
  off: ['未启用', '连接目录'],
  on: ['已连接', ''],
  pending: ['待同步', ''],
  error: ['同步失败', '查看设置'],
};

/* 左栏顶部 vault 状态条：四态都给明确文案与一个动作，0 数据形态也有落点 */
export function VaultStatusBar({ state, pending, onSync, onConnect }) {
  const [label, hint] = VAULT_LABEL[state] || VAULT_LABEL.off;
  const extra = state === 'pending' ? `${pending} 项变更待同步` : hint;
  return (
    <div className={'vault-bar vb-' + state}>
      <DatabaseOutlined className="vb-ic" />
      <span className="vb-label">本地库{label}</span>
      <span className="vb-hint">{extra}</span>
      <Button size="small" type="link" className="vb-act"
        onClick={state === 'off' ? onConnect : onSync}>
        {state === 'off' ? '连接目录' : state === 'error' ? '重试' : '同步'}
      </Button>
    </div>
  );
}

/* 成卡行条：展示条数，hash 变化时提示「源笔记已改」，接口缺失时优雅降级 */
export function AnchorBar({ anchors, syncedHashes, onSync, onInsert, busy }) {
  if (!anchors.length) {
    return (
      <div className="anchor-bar ab-empty">
        <LinkOutlined />
        <span className="ab-text">没有成卡行</span>
        <Button size="small" type="link" onClick={onInsert}>插入示例</Button>
      </div>
    );
  }
  const changed = anchors.some((a) => !syncedHashes[a.hash]);
  return (
    <div className="anchor-bar">
      <LinkOutlined />
      <span className="ab-count">成卡行 {anchors.length} 条</span>
      {changed && <span className="ab-changed">源笔记已改，点此同步</span>}
      <Button size="small" type="link" icon={<ReloadOutlined />} loading={busy} onClick={onSync}>
        同步卡片
      </Button>
    </div>
  );
}

/* 文档级 AI 速览：贴在正文上方，不是独立聊天窗；可刷新、复制、收起 */
export function AiQuickView({ text, busy, onRefresh, onClose, onCopy }) {
  return (
    <div className="ai-quick">
      <div className="ai-quick-head">
        <span>AI 速览</span>
        <span className="row" style={{ gap: 4 }}>
          <Button size="small" type="link" loading={busy} onClick={onRefresh}>刷新</Button>
          <Button size="small" type="link" onClick={onCopy}>复制</Button>
          <Button size="small" type="text" onClick={onClose}>收起</Button>
        </span>
      </div>
      <div className="ai-quick-body">{text || '这次没有生成摘要'}</div>
    </div>
  );
}

/* 新建笔记模板选择：一屏一个实心主按钮，模板卡为次级可点区域 */
export function TemplatePicker({ open, onCancel, onCreate }) {
  const [sel, setSel] = useState('blank');
  return (
    <Modal open={open} title="新建笔记" okText="创建" cancelText="取消"
      onCancel={onCancel} onOk={() => { onCreate(sel); setSel('blank'); }} destroyOnClose>
      <div className="tpl-grid">
        {NOTE_TEMPLATES.map((t) => (
          <button key={t.key} type="button"
            className={'tpl-item' + (sel === t.key ? ' on' : '')}
            onClick={() => setSel(t.key)}>
            <span className="tpl-name">{t.name}</span>
            <span className="tpl-desc">{t.desc}</span>
          </button>
        ))}
      </div>
    </Modal>
  );
}

/* tab 文案：11.5px；计数用等宽数字，0 值走次要色而不是最浅色 */
function tabText(text, count) {
  return (
    <span style={{ fontSize: 11.5 }}>
      {text}
      {count !== undefined && (
        <span style={{
          marginLeft: 4, fontVariantNumeric: 'tabular-nums',
          color: count ? 'var(--foreground)' : 'var(--muted-foreground)',
        }}>{count}</span>
      )}
    </span>
  );
}

/* 右侧栏：反链 / 大纲 / AI 协作。宽屏并排，窄屏由 NotesPage 装进抽屉，内容只有这一份。 */
export function NoteAside({
  note, links, tab, onTabChange, thread, onInsert, onDiscard, onSelectNote,
  aiMode, onAiModeChange, aiText, onAiTextChange, onAiSuggest,
}) {
  const backlinks = links?.backlinks || [];
  const outgoing = links?.outgoing || [];
  const headings = [...String(note?.content || '').matchAll(/^(#{1,3})\s+(.+)$/gm)]
    .map((m) => ({ level: m[1].length, text: m[2].trim() }));
  return (
    <>
      <div className="pane-head" style={{ gap: 8 }}>
        <span title={note?.title || ''} style={{
          minWidth: 0, maxWidth: 92, overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>{note ? (note.title || '未命名') : '未选笔记'}</span>
        <Tabs size="small" activeKey={tab} onChange={onTabChange} tabBarStyle={{ margin: 0 }}
          items={[
            { key: 'links', label: tabText('反链', backlinks.length) },
            { key: 'outline', label: tabText('大纲') },
            { key: 'ai', label: tabText('AI') },
          ]} />
      </div>
      {tab === 'links' && (
        <div className="pane-body" style={{ padding: 12 }}>
          <div className="vmuted2" style={{ marginBottom: 6 }}>反向链接（谁提到了本文）</div>
          {backlinks.length ? backlinks.map((b) => (
            <div className="nitem" key={b.id} onClick={() => onSelectNote({ id: b.id, title: b.title, content: b.snippet })}>
              <div className="nt">{esc(b.title)}</div><div className="ns">{esc(b.snippet)}</div>
            </div>
          )) : <div className="vmuted2">暂无引用</div>}
          <div className="vmuted2" style={{ margin: '12px 0 6px' }}>出链（本文提到的笔记）</div>
          {outgoing.length ? outgoing.map((o, i) => (
            <div className="vkp" key={i} onClick={() => onSelectNote({ id: o.note_id, title: o.title })}>
              <span className="vkp-l">{esc(o.title)}</span>
              {!o.note_id && <span className="vmuted2">未创建</span>}
            </div>
          )) : <div className="vmuted2">暂无出链</div>}
        </div>
      )}
      {tab === 'outline' && (
        <div className="pane-body" style={{ padding: 12 }}>
          {headings.length ? headings.map((h, i) => (
            <div key={i} className="vkp" style={{ paddingLeft: (h.level - 1) * 12 }}>
              <span className="vkp-l">{esc(h.text)}</span>
            </div>
          )) : <div className="vmuted2">暂无大纲</div>}
          <div className="vmuted2" style={{ marginTop: 12, fontVariantNumeric: 'tabular-nums' }}>
            双链总数：{outgoing.length + backlinks.length}
          </div>
        </div>
      )}
      {tab === 'ai' && (<>
        <div className="ai-thread">
          {thread.length ? thread.map((m, i) => (
            <div className={'ai-msg' + (m.role === 'me' ? ' me' : '')} key={i}>
              <div className="mdview" style={{ fontSize: 12.5 }}>{m.text}</div>
              {m.role === 'ai' && (
                <div className="row" style={{ marginTop: 6 }}>
                  <Button size="small" onClick={() => onInsert(i, 'append')}>插入到末尾</Button>
                  <Button size="small" onClick={() => onInsert(i, 'replace')}>替换全文</Button>
                  <Button size="small" type="text" onClick={() => onDiscard(i)}>放弃</Button>
                </div>
              )}
            </div>
          )) : <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.8, padding: 4 }}>
            润色、扩展、提炼要点与出题</div>}
        </div>
        <div className="ai-input">
          <Segmented size="small" value={aiMode} onChange={onAiModeChange} options={AI_MODES} />
          <textarea value={aiText} onChange={(e) => onAiTextChange(e.target.value)} placeholder="补充指令（可空），例如：补上三个易错点" />
          <Button size="small" type="primary" disabled={!note} onClick={onAiSuggest}>生成建议</Button>
        </div>
      </>)}
    </>
  );
}
