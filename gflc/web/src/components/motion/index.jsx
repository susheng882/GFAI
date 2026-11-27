/* framer-motion 动效封装（v7l 对齐）。
   统一 240ms 指数缓出；尊重 prefers-reduced-motion（framer 内置）。 */
import { motion, useReducedMotion } from 'framer-motion';
import React from 'react';

export const EASE_OUT_EXPO = [0.16, 1, 0.3, 1];
export const EASE_SLIDE = [0.32, 0.72, 0, 1];

/* 卡片入场：rcCardIn 240ms 指数缓出（translateY 6px + fade） */
export function FadeIn({ children, delay = 0, y = 6, className = '', ...rest }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: EASE_OUT_EXPO, delay }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

/* 右抽屉滑入：slideIn 260ms 弹性缓出 */
export function SlideIn({ children, className = '', from = 'right', ...rest }) {
  const reduce = useReducedMotion();
  const x = from === 'right' ? '100%' : '-100%';
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ x }}
      animate={{ x: 0 }}
      exit={{ x }}
      transition={{ duration: 0.26, ease: EASE_SLIDE }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

/* 弹窗入场：rcBoxIn（translateY 10px + scale .965 → 1） */
export function PopIn({ children, className = '', ...rest }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 10, scale: 0.965 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 6, scale: 0.985 }}
      transition={{ duration: 0.24, ease: EASE_OUT_EXPO }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

/* 翻转卡 3D：460ms cubic-bezier(.32,.72,0,1)，preserve-3d + backface-hidden */
export function FlipCard({ front, back, flipped, onFlip, height = 320, className = '' }) {
  const reduce = useReducedMotion();
  return (
    <div
      onClick={onFlip}
      className={className}
      style={{ perspective: 1200, height, cursor: 'pointer', position: 'relative', width: '100%' }}
    >
      <motion.div
        style={{ position: 'absolute', inset: 0, transformStyle: 'preserve-3d' }}
        animate={{ rotateY: flipped ? 180 : 0 }}
        transition={reduce ? { duration: 0 } : { duration: 0.46, ease: EASE_SLIDE }}
      >
        <div style={{ position: 'absolute', inset: 0, backfaceVisibility: 'hidden', WebkitBackfaceVisibility: 'hidden' }}>
          {front}
        </div>
        <div style={{
          position: 'absolute', inset: 0, backfaceVisibility: 'hidden',
          WebkitBackfaceVisibility: 'hidden', transform: 'rotateY(180deg)',
        }}>
          {back}
        </div>
      </motion.div>
    </div>
  );
}

/* 数字滚动：numPop */
export function NumPop({ value, className = '' }) {
  const reduce = useReducedMotion();
  if (reduce) return <span className={className}>{value}</span>;
  return (
    <motion.span
      key={value}
      className={className}
      initial={{ opacity: 0, y: 6, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.24, ease: EASE_OUT_EXPO }}
    >
      {value}
    </motion.span>
  );
}
