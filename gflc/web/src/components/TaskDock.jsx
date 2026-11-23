import React, { useSyncExternalStore } from 'react';
import { taskStore, STATUS_CN } from '../api.js';

/* 后台任务悬浮进度坞：对应旧版 TASKS + renderDock()。 */
export default function TaskDock() {
  const tasks = useSyncExternalStore(taskStore.subscribe, taskStore.getSnapshot, taskStore.getSnapshot);
  if (!tasks.length) return null;
  return (
    <div className="taskdock" aria-live="polite">
      {tasks.map((t) => (
        <div className="tk" key={t.id}>
          <div className="tt"><span>{t.label}</span><span>{t.progress}%</span></div>
          <div className="tp"><i style={{ width: `${t.progress}%` }} /></div>
          <div className="ts">
            {t.status === 'failed'
              ? `失败：${t.error || ''}`
              : t.status === 'ready' ? '完成' : t.status === 'pending' ? '排队中…' : '处理中…'}
          </div>
        </div>
      ))}
    </div>
  );
}
