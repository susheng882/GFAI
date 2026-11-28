import React from 'react';

/**
 * GFLC v8 · 复用件
 * 只用 Tailwind utilities + 少量 gf-* 语义类；不引 antd、不写内联 style。
 */

export function cx(...parts) {
  return parts.filter(Boolean).join(' ');
}

/** 卡片容器：白底 + 1px #E8E8ED 边框 + 16px 圆角 */
export function Card({ className = '', pad = true, as: Tag = 'section', children, ...rest }) {
  return (
    <Tag className={cx('gf-card', pad && 'gf-card-pad', 'min-w-0', className)} {...rest}>
      {children}
    </Tag>
  );
}

/** 区块标题：14px/500 主标题 + 12px 副标题 + 右侧动作区 */
export function SectionTitle({ title, sub, action, className = '' }) {
  return (
    <div className={cx('mb-2 flex items-start justify-between gap-3', className)}>
      <div className="min-w-0">
        <h2 className="gf-title truncate">{title}</h2>
        {sub ? <p className="gf-sub mt-0.5 truncate">{sub}</p> : null}
      </div>
      {action ? <div className="flex shrink-0 items-center gap-1.5">{action}</div> : null}
    </div>
  );
}

const BADGE_TONES = {
  neutral: 'bg-sel text-ink2',
  brand: 'bg-brandSoft text-brand',
  ok: 'bg-[#EAF8EE] text-[#248A3D]',
  warn: 'bg-[#FFF4E5] text-[#B26A00]',
  bad: 'bg-[#FDECEC] text-[#C4322B]',
  line: 'border border-line bg-card text-ink2',
};

/** 状态徽标：10px/500，999px 圆角 */
export function Badge({ tone = 'neutral', dot = false, className = '', children }) {
  const dotTone = {
    neutral: 'bg-ink3',
    brand: 'bg-brand',
    ok: 'bg-ok',
    warn: 'bg-warn',
    bad: 'bg-bad',
    line: 'bg-ink3',
  }[tone];
  return (
    <span className={cx('gf-badge', BADGE_TONES[tone] || BADGE_TONES.neutral, className)}>
      {dot ? <span className={cx('h-1 w-1 rounded-full', dotTone)} /> : null}
      {children}
    </span>
  );
}

const BTN_VARIANTS = {
  solid: 'gf-btn-solid',
  line: 'gf-btn-line',
  ghost: 'text-ink2 hover:bg-sel hover:text-ink',
};

const BTN_SIZES = {
  xs: 'h-7 px-2.5 text-[11px]',
  sm: 'h-8 px-3 text-[12px]',
  md: 'h-9 px-4 text-[13px]',
};

/** 按钮：一屏实心主按钮 ≤ 2 个 */
export function Btn({
  variant = 'line',
  size = 'sm',
  icon = null,
  className = '',
  type = 'button',
  children,
  ...rest
}) {
  return (
    <button
      type={type}
      className={cx('gf-btn', BTN_VARIANTS[variant] || BTN_VARIANTS.line, BTN_SIZES[size], className)}
      {...rest}
    >
      {icon ? <span className="shrink-0">{icon}</span> : null}
      {children}
    </button>
  );
}

const PROGRESS_TONES = {
  brand: 'bg-brand',
  ok: 'bg-ok',
  warn: 'bg-warn',
  bad: 'bg-bad',
  ink: 'bg-ink',
};

/** 进度条：默认 6px 高，999px 圆角 */
export function Progress({ value = 0, tone = 'brand', height = 'h-1.5', className = '' }) {
  const raw = Math.max(0, Math.min(100, Number(value) || 0));
  const step = Math.round(raw / 2) * 2;
  return (
    <div
      className={cx('w-full overflow-hidden rounded-full bg-sel', height, className)}
      role="progressbar"
      aria-valuenow={raw}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={cx(
          'h-full rounded-full transition-[width] duration-200 ease-apple',
          PROGRESS_TONES[tone] || PROGRESS_TONES.brand,
          `w-[${step}%]`,
        )}
      />
    </div>
  );
}

/** 空状态 */
export function Empty({ text = '暂无内容', hint, className = '' }) {
  return (
    <div className={cx('flex flex-col items-center justify-center gap-1 py-8 text-center', className)}>
      <p className="text-[12px] text-ink3">{text}</p>
      {hint ? <p className="text-[11px] text-ink3">{hint}</p> : null}
    </div>
  );
}

/** KPI 指标：数值 22px/500 等宽数字，标签 11px */
export function Kpi({ label, value, unit, hint, tone = 'ink', className = '' }) {
  const valueTone = {
    ink: 'text-ink',
    brand: 'text-brand',
    ok: 'text-[#248A3D]',
    warn: 'text-[#B26A00]',
    bad: 'text-[#C4322B]',
  }[tone];
  return (
    <div className={cx('min-w-0', className)}>
      <p className="text-[11px] leading-[16px] text-ink3">{label}</p>
      <p className={cx('gf-num mt-1 flex items-baseline gap-1 text-[22px] font-medium leading-[26px]', valueTone)}>
        <span>{value}</span>
        {unit ? <span className="text-[11px] font-normal text-ink3">{unit}</span> : null}
      </p>
      {hint ? <p className="mt-1 truncate text-[11px] leading-[16px] text-ink3">{hint}</p> : null}
    </div>
  );
}

/** 标签+数值+细进度的一行，用于分布 / 系统信息 */
export function MeterRow({ label, value, total, tone = 'brand', suffix }) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="w-[64px] shrink-0 truncate text-[12px] text-ink2">{label}</span>
      <Progress value={pct} tone={tone} height="h-1" className="flex-1" />
      <span className="gf-num w-[42px] shrink-0 text-right text-[11px] text-ink3">
        {suffix || value}
      </span>
    </div>
  );
}

/** 键帽：⌘K 等快捷键提示 */
export function KeyCap({ children, className = '' }) {
  return (
    <kbd
      className={cx(
        'inline-flex h-5 min-w-5 items-center justify-center rounded-[6px] border border-line bg-card px-1 text-[10px] font-normal text-ink3',
        className,
      )}
    >
      {children}
    </kbd>
  );
}

/** 细分隔线 */
export function Divider({ className = '' }) {
  return <div className={cx('h-px w-full bg-line', className)} />;
}
