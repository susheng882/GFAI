import React from 'react';
import { Button } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';

/* 统一空状态：40px 圆角容器 + 标题 + 一句说明 + 一个动作。
   图标统一走 Antd 线条图标（18px / currentColor），不引入新图标库、不用字符或 emoji。 */
export default function EmptyState({ title = '', desc = '', action, onAction, icon }) {
  return (
    <div style={{
      padding: '32px 16px', display: 'flex', flexDirection: 'column',
      alignItems: 'center', textAlign: 'center', gap: 12,
    }}>
      <span aria-hidden="true" style={{
        width: 40, height: 40, borderRadius: 12, border: '1px solid var(--border)',
        background: 'var(--secondary)', color: 'var(--muted-foreground)', fontSize: 18,
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      }}>{icon || <FileTextOutlined />}</span>
      <div>
        <div style={{ fontSize: 14.5, fontWeight: 500, color: 'var(--foreground)' }}>{title}</div>
        {desc && (
          <div style={{ fontSize: 12.5, color: 'var(--muted-foreground)', marginTop: 4, lineHeight: 1.7 }}>{desc}</div>
        )}
      </div>
      {action && <Button size="small" onClick={onAction}>{action}</Button>}
    </div>
  );
}
