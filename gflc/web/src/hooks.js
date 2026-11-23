/* 通用交互 hook：侧栏折叠状态记忆（写在 localStorage，刷新后保持）。 */

import { useState, useCallback, useEffect } from 'react';
import { api } from './api.js';

/* 读取布尔型 localStorage 开关。
   - 已写入 '1'/'0' 时按写入值；
   - 未写入时回落到 defaultCollapsed。 */
function readFlag(key, defaultCollapsed) {
  const raw = localStorage.getItem(key);
  if (raw === '1') return true;
  if (raw === '0') return false;
  return !!defaultCollapsed;
}

/* 返回一个 [collapsed, toggle] 二元组；toggle 同时落盘。 */
export function useCollapsible(key, defaultCollapsed = false) {
  const [collapsed, setCollapsed] = useState(() => readFlag(key, defaultCollapsed));
  const toggle = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(key, next ? '1' : '0');
      return next;
    });
  }, [key]);
  return [collapsed, toggle];
}

/* 键盘快捷键守卫：焦点在输入框 / 下拉 / 富文本时不触发评分、翻面等快捷键。 */
export function isTypingTarget(el) {
  if (!el) return false;
  const tag = el.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (el.isContentEditable) return true;
  return !!(el.closest && el.closest('[contenteditable="true"], .ant-select, .ant-input-number'));
}

/* 今日队列聚合（B5）：复习 Y + 新学 Z = 今日 W。
   - 复习 Y：到期卡中已复习过的（reps > 0），来自 GET /review/due；
   - 新学 Z：到期卡中从未复习的（reps === 0），即立即可学的新卡；
   - W = Y + Z，与当前到期卡片流一一对应，不重复计数；
   - /review/due 失败时用 GET /dashboard/loop 的卡片步兜底（count=已复习、total=总数），
     两个接口都失败则全 0，页面显示 0 数据形态而非白屏。 */
export function useTodayQueue() {
  const [state, setState] = useState({ review: 0, fresh: 0, total: 0, loading: true });
  useEffect(() => {
    let alive = true;
    (async () => {
      const [dueRes, loopRes] = await Promise.allSettled([
        api('/review/due?limit=500'),
        api('/dashboard/loop'),
      ]);
      if (!alive) return;
      const cards = dueRes.status === 'fulfilled' && Array.isArray(dueRes.value?.cards)
        ? dueRes.value.cards : null;
      if (cards) {
        const review = cards.filter((c) => (c.reps || 0) > 0).length;
        const fresh = cards.length - review;
        setState({ review, fresh, total: review + fresh, loading: false });
        return;
      }
      // 降级：due 不可用时从闭环状态条的卡片步取近似值
      const steps = loopRes.status === 'fulfilled' && Array.isArray(loopRes.value?.steps)
        ? loopRes.value.steps : [];
      const cardStep = steps.find((s) => /card|卡片/i.test(`${s.key || ''} ${s.label || ''}`));
      if (cardStep) {
        const totalCards = Number(cardStep.total) || 0;
        const reviewed = Number(cardStep.count) || 0;
        const review = Math.min(reviewed, totalCards);
        setState({ review, fresh: Math.max(0, totalCards - review), total: totalCards, loading: false });
        return;
      }
      setState({ review: 0, fresh: 0, total: 0, loading: false });
    })();
    return () => { alive = false; };
  }, []);
  return state;
}
