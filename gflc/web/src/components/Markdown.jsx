import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

/* 答案/笔记正文渲染：GFM 表格 + LaTeX 公式 + GFLC 自定块锚与双链。 */
const ANCHOR_AT_END = /\s\^([A-Za-z0-9_-]{1,40})\s*$/;

/* 把段落/列表项末尾的 ^id 提取成稳定块锚，正文里不再显示这个标记。
   纯 AST 处理，不引入新依赖，也不抄竞品专有符号。 */
function remarkGflcBlock() {
  const walk = (node) => {
    if (!node || !Array.isArray(node.children)) return;
    node.children.forEach((child) => {
      if ((child.type === 'paragraph' || child.type === 'listItem') && Array.isArray(child.children)) {
        const last = child.children[child.children.length - 1];
        if (last && last.type === 'text') {
          const m = last.value.match(ANCHOR_AT_END);
          if (m) {
            last.value = last.value.replace(ANCHOR_AT_END, '');
            child.data = child.data || {};
            child.data.hProperties = {
              ...(child.data.hProperties || {}),
              id: 'blk-' + m[1], 'data-block-id': m[1],
            };
          }
        }
      }
      walk(child);
    });
  };
  return (tree) => walk(tree);
}

/* [[标题]] / [[笔记#^块锚]] → 可点链接；跳转由 NotesPage 监听事件处理 */
const WIKI_LINK = /\[\[([^\]\n]{1,80})\]\]/g;
function preprocess(md) {
  return String(md || '').replace(WIKI_LINK, (_, raw) => {
    const m = raw.match(/^(.+)#\^([A-Za-z0-9_-]{1,40})$/);
    return m
      ? `[${raw}](#block:${encodeURIComponent(m[1])}--${encodeURIComponent(m[2])})`
      : `[${raw}](#wiki:${encodeURIComponent(raw)})`;
  });
}

function jumpLink(href, children, props) {
  let detail;
  if (href.startsWith('#wiki:')) {
    detail = { title: decodeURIComponent(href.slice(6)) };
  } else {
    const [rawTitle, rawAnchor] = href.slice(7).split('--');
    detail = { title: decodeURIComponent(rawTitle || ''), anchor: decodeURIComponent(rawAnchor || '') };
  }
  return (
    <a href={href} {...props} className="md-wikilink"
      onClick={(e) => {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent('gflc:note-jump', { detail }));
      }}>
      {children}
    </a>
  );
}

export default function Markdown({ text = '', className = '' }) {
  return (
    <div className={'mdview ' + className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath, remarkGflcBlock]}
        rehypePlugins={[rehypeKatex]}
        components={{
          a: ({ href = '', children, node, ...props }) => (
            href.startsWith('#wiki:') || href.startsWith('#block:')
              ? jumpLink(href, children, props)
              : <a href={href} target="_blank" rel="noopener noreferrer" {...props}>{children}</a>
          ),
          p: ({ node, children, ...props }) => <p {...props}>{children}</p>,
          li: ({ node, children, ...props }) => <li {...props}>{children}</li>,
        }}
      >
        {preprocess(text)}
      </ReactMarkdown>
    </div>
  );
}
