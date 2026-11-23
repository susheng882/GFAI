import React from 'react';
import { Button, Empty } from 'antd';
import { InboxOutlined } from '@ant-design/icons';

/* 统一空状态：旧版 emptyState() 的 React 版。 */
export default function EmptyState({ title = '', desc = '', action, onAction }) {
  return (
    <div style={{ padding: '32px 16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <span>
            <span style={{ display: 'block', fontSize: 14, color: 'var(--foreground)' }}>{title}</span>
            {desc && <span style={{ fontSize: 12.5, color: 'var(--muted-foreground)' }}>{desc}</span>}
          </span>
        }
      >
        {action && <Button size="small" onClick={onAction}>{action}</Button>}
      </Empty>
    </div>
  );
}
