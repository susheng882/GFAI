/* @ant-design/charts 图表封装（v7l 对齐）。
   统一：主色 #0071E3、面积渐变、极简轴（无冗余网格线）。 */
import { Area, Bar, Column } from '@ant-design/charts';
import React from 'react';

const BLUE = '#0071E3';
const WARN = '#B25000';
const PALETTE = ['#0071E3', '#9DC3F5', '#D6E6FF', '#1A7F43', '#B25000', '#C8453A'];
const AXIS = { tick: false, label: false, line: false, grid: false };

/* 折线/面积图：data=[{day, cost, tokens}]，双线（tokens 蓝 / cost 橙虚线） */
export function TrendChart({ data = [], height = 160, xField = 'day', series = ['tokens', 'cost'] }) {
  if (!data || data.length < 2) {
    return <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--ink-muted)', fontSize: 12 }}>数据不足，再跑几次就会画出来</div>;
  }
  const cfg = {
    data,
    xField,
    yField: 'value',
    shapeField: 'smooth',
    height,
    axis: { x: { ...AXIS, tick: false }, y: { ...AXIS, label: false } },
    scale: { color: { range: [BLUE, WARN] } },
    style: { lineWidth: 2 },
    legend: false,
  };
  // series 双字段 → 转成长表
  const long = [];
  data.forEach((d) => {
    series.forEach((s) => { if (d[s] != null) long.push({ ...d, series: s, value: +d[s] }); });
  });
  const cfgLong = {
    data: long,
    xField,
    yField: 'value',
    colorField: 'series',
    shapeField: 'smooth',
    height,
    axis: { x: { ...AXIS }, y: { ...AXIS } },
    scale: { color: { range: [BLUE, WARN] } },
    style: { lineWidth: 2 },
    legend: false,
  };
  return <Area {...cfgLong} />;
}

/* 条形图：data=[{label, value}] */
export function BarsChart({ data = [], height = 150 }) {
  if (!data || data.length === 0) {
    return <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--ink-muted)', fontSize: 12 }}>暂无数据</div>;
  }
  return (
    <Bar
      data={data}
      xField="label"
      yField="value"
      height={height}
      axis={{ x: { labelAutoRotate: false, labelFontSize: 10, labelFill: '#86868B' }, y: { ...AXIS, label: false } }}
      style={{ fill: BLUE, radiusTopLeft: 4, radiusTopRight: 4, maxWidth: 28 }}
    />
  );
}

/* 柱状/分布图（多分类）：data=[{label, value, type}] */
export function ColumnChart({ data = [], height = 150, colorField = 'type' }) {
  if (!data || data.length === 0) {
    return <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--ink-muted)', fontSize: 12 }}>暂无数据</div>;
  }
  return (
    <Column
      data={data}
      xField="label"
      yField="value"
      colorField={colorField}
      height={height}
      axis={{ x: { labelAutoRotate: false, labelFontSize: 10, labelFill: '#86868B' }, y: { ...AXIS, label: false } }}
      scale={{ color: { range: PALETTE } }}
      style={{ radiusTopLeft: 4, radiusTopRight: 4, maxWidth: 24 }}
      legend={false}
    />
  );
}

/* 热力图（四阶蓝）：data=[{x, y, v}]，v=0-3 */
export function HeatmapChart({ data = [], height = 120 }) {
  if (!data || data.length === 0) {
    return <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--ink-muted)', fontSize: 12 }}>暂无数据</div>;
  }
  return (
    <div style={{ display: 'grid', gridAutoFlow: 'column', gridTemplateRows: 'repeat(7, 1fr)', gap: 3, height }}>
      {data.map((d, i) => (
        <div key={i} title={`${d.x} ${d.y}: ${d.v}`} style={{
          width: 10, height: 10, borderRadius: 3,
          background: ['#EFF5FF', '#D6E6FF', '#9DC3F5', BLUE][Math.min(3, Math.max(0, +d.v || 0))],
        }} />
      ))}
    </div>
  );
}
