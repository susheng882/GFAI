import React from 'react';
import { Button } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';

/* 统一空状态（v7l 风格）：虚线框容器 + 线图标 + 主文案 + 副文案 + 动作按钮。
   原型语言：rounded-[10px] border-dashed bg-sunken，主文案 11px ink，副文案 10px ink-subtle。
   dashed=true → 大拖拽框（132px 高）；false → 紧凑型列表空态。 */
export default function EmptyState({ title = '', desc = '', sub = '', action, onAction, icon, dashed = false }) {
  const inner = (
    <>
      <span aria-hidden="true" style={{
        width: 40, height: 40, borderRadius: 12, border: '1px solid var(--line)',
        background: 'var(--base-100)', color: 'var(--ink-subtle)', fontSize: 18,
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      }}>{icon || <FileTextOutlined />}</span>
      {title && <div style={{ fontSize: 12.5, fontWeight: 500, color: 'var(--ink)', marginTop: 2 }}>{title}</div>}
      {desc && <div style={{ fontSize: 11, color: 'var(--ink-muted)', marginTop: 2, lineHeight: 1.7 }}>{desc}</div>}
      {sub && <div style={{ fontSize: 10, color: 'var(--ink-faint)', marginTop: 1, lineHeight: 1.6 }}>{sub}</div>}
      {action && <Button size="small" style={{ marginTop: 4 }} onClick={onAction}>{action}</Button>}
    </>
  );
  if (dashed) {
    return (
      <div style={{
        borderRadius: 10, border: '1px dashed var(--input, rgba(0,0,0,.15))',
        background: 'var(--sunken)', minHeight: 132,
        display: 'grid', placeItems: 'center', padding: '20px 16px',
      }}>
        <div style={{ textAlign: 'center' }}>{inner}</div>
      </div>
    );
  }
  return (
    <div style={{
      padding: '28px 16px', display: 'flex', flexDirection: 'column',
      alignItems: 'center', textAlign: 'center', gap: 4,
    }}>
      {inner}
    </div>
  );
}
