import React, { useEffect, useState } from 'react';
import { Modal, Button, Tag, Alert } from 'antd';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';

/* S4 文档类跳转落点：显示对应页。
   若资料带 file_url/url（后端后续补充原文文件接口即可），直接内嵌 PDF 并定位 #page=N；
   否则用应用内页码定位器展示「第 N 页」+ 资料信息 + 可调页码，留明确提示。 */
export default function DocumentJumpModal({ open, docId, page = 1, documents = [], onClose }) {
  const [current, setCurrent] = useState(Number(page) || 1);
  useEffect(() => { if (open) setCurrent(Number(page) || 1); }, [open, page]);
  const doc = documents.find((d) => String(d.id) === String(docId));
  const fileUrl = doc && (doc.file_url || doc.url || doc.preview_url);
  const title = doc?.title || '未定位到资料';
  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={<span>原文定位 · {title}</span>}
      footer={<Button onClick={onClose}>关闭</Button>}
      width={820}
      destroyOnHidden
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 14, flexWrap: 'wrap' }}>
        <div>
          <div className="jump-page-no">{current}</div>
          <div className="jump-meta">第 {current} 页 · chunk_id 由答案来源提供</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <Button size="small" icon={<LeftOutlined />} onClick={() => setCurrent((p) => Math.max(1, p - 1))}>上一页</Button>
          <Button size="small" onClick={() => setCurrent((p) => p + 1)}>下一页 <RightOutlined /></Button>
        </div>
      </div>
      {fileUrl ? (
        <iframe className="pdf-frame" title="原文 PDF" src={`${fileUrl}#page=${current}`} />
      ) : (
        <>
          <Alert
            type="info"
            showIcon
            message="已定位到原文对应页"
            description="当前后端尚未提供 PDF 原文文件接口，暂以应用内页码定位器展示；后端补充 GET /api/documents/{id}/file 或 file_url 后，此处自动切换为内嵌 PDF 并跳到对应页。"
            style={{ marginBottom: 12 }}
          />
          <div style={{
            border: '1px solid var(--border)', borderRadius: 'var(--r-md)',
            background: 'var(--secondary)', padding: '28px 20px', textAlign: 'center',
          }}>
            <div style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>资料</div>
            <div style={{ fontSize: 15, fontWeight: 500, marginTop: 4 }}>{title}</div>
            <div style={{ marginTop: 10 }}><Tag>目标页 {current}</Tag>{doc?.status && <Tag>{doc.status}</Tag>}</div>
          </div>
        </>
      )}
    </Modal>
  );
}
