import React, { useEffect, useRef, useState } from 'react';
import { Transformer } from 'markmap-lib';
import { Markmap } from 'markmap-view';

/* 大纲 → 思维导图（markmap）。用户明确要求「大纲是思维导图，不是残缺列表」。
   markdown 里 ## / ### 层级直接映射成节点树；支持缩放/全屏。 */
const transformer = new Transformer();

export default function MindMap({ markdown, height = 460 }) {
  const svgRef = useRef(null);
  const mmRef = useRef(null);
  const wrapRef = useRef(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    if (!svgRef.current || !markdown.trim()) return undefined;
    const { root } = transformer.transform(markdown);
    if (mmRef.current) { mmRef.current.destroy(); mmRef.current = null; }
    mmRef.current = Markmap.create(svgRef.current, {
      duration: 200, spacingVertical: 8, spacingHorizontal: 90,
      paddingX: 12, initialExpandLevel: 3, maxWidth: 260,
    }, root);
    setTimeout(() => mmRef.current && mmRef.current.fit(), 60);
    return () => {
      if (mmRef.current) { mmRef.current.destroy(); mmRef.current = null; }
    };
  }, [markdown]);

  const zoom = (delta) => {
    const next = Math.min(2.2, Math.max(0.45, Number((scale + delta).toFixed(2))));
    setScale(next);
    if (mmRef.current) mmRef.current.rescale(next);
  };

  return (
    <div className="mmwrap" ref={wrapRef}>
      <div className="mmtools">
        <button type="button" onClick={() => zoom(0.2)} title="放大">＋</button>
        <button type="button" onClick={() => zoom(-0.2)} title="缩小">－</button>
        <button type="button" onClick={() => mmRef.current && mmRef.current.fit()} title="适应窗口">适应</button>
      </div>
      <svg ref={svgRef} className="mmsvg" style={{ height }} />
    </div>
  );
}
