import React, { useRef, useSyncExternalStore } from 'react';
import { taskStore } from '../api.js';

/* 解析类任务（解析资料/重新解析）：扫描件 OCR 单份可达 131s，
   只有百分比会让用户以为卡死，故额外展示「已用时 + 约剩」。 */
const PARSE_LABEL_RE = /解析/;
/* 少于这个秒数不估算：起步阶段的 elapsed/progress 外推噪声太大 */
const ETA_MIN_ELAPSED = 5;

/* 线性外推剩余秒数：remain = elapsed × (100 - progress) / progress，向上取整。
   >120s 统一显示「约剩 2 分钟」，避免 171 秒这种看不动的读数。 */
function fmtEta(elapsedSec, progress) {
  const remain = (elapsedSec * (100 - progress)) / progress;
  if (remain > 120) return '约剩 2 分钟';
  return `约剩 ${Math.max(1, Math.ceil(remain))} 秒`;
}

function fmtElapsed(elapsedSec) {
  const s = Math.floor(elapsedSec);
  return s >= 60 ? `${Math.floor(s / 60)}分${s % 60}秒` : `${s}s`;
}

/* 后台任务悬浮进度坞：对应旧版 TASKS + renderDock()。 */
export default function TaskDock() {
  const tasks = useSyncExternalStore(taskStore.subscribe, taskStore.getSnapshot, taskStore.getSnapshot);
  // 首次看到该任务的时刻（ms）：任务坞随轮询重渲染，所以已用时会自然走动。
  const firstSeen = useRef(new Map());
  if (!tasks.length) return null;

  const now = Date.now();
  const alive = new Set(tasks.map((t) => t.id));
  firstSeen.current.forEach((_, id) => { if (!alive.has(id)) firstSeen.current.delete(id); });

  return (
    <div className="taskdock" aria-live="polite">
      {tasks.map((t) => {
        if (!firstSeen.current.has(t.id)) firstSeen.current.set(t.id, now);
        const elapsed = (now - firstSeen.current.get(t.id)) / 1000;
        // 仅运行中、1–99%、已跑够 5s 的解析类任务才估算：0%（未知）与 100%（收尾）不显示
        const showEta = t.status === 'running' && PARSE_LABEL_RE.test(t.label || '')
          && t.progress > 0 && t.progress < 100 && elapsed > ETA_MIN_ELAPSED;
        return (
          <div className="tk" key={t.id}>
            <div className="tt"><span>{t.label}</span><span>{t.progress}%</span></div>
            <div className="tp"><i style={{ width: `${t.progress}%` }} /></div>
            <div className="ts">
              {t.status === 'failed'
                ? `失败：${t.error || ''}`
                : t.status === 'ready' ? '完成' : t.status === 'pending' ? '排队中…' : (
                  <>
                    <span>{`处理中 ${fmtElapsed(elapsed)}`}</span>
                    {showEta && <span>{` · ${fmtEta(elapsed, t.progress)}`}</span>}
                  </>
                )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
