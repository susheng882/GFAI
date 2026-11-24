import React, { useCallback, useEffect, useRef, useState } from 'react';
import { App as AntdApp, Button, Table, Tooltip, Popconfirm, Tag, Empty } from 'antd';
import { FileAddOutlined, DeleteOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { api, runTask } from '../api.js';
import { esc, fmtTs } from '../utils.js';
import EmptyState from '../components/EmptyState.jsx';

/* 题库：独立入口，与「资料（教材解析）」分开。
   职责单一——只做题库文件的上传 → 视觉抽题 → 成题库，列表管理，去刷题。 */

const EXT_HINT = '支持 PDF（试卷）/ xlsx / docx / txt / md';

export default function QuestionBanksPage() {
  const { message } = AntdApp.useApp();
  const navigate = useNavigate();
  const [banks, setBanks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState('');
  const fileRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { setBanks(await api('/questions/banks') || []); }
    catch (e) { message.error(e.message); }
    setLoading(false);
  }, [message]);
  useEffect(() => { load(); }, [load]);

  const importFile = async (file) => {
    if (!file) return;
    setStage('上传中…');
    try {
      const fd = new FormData(); fd.append('file', file);
      const r = await api('/questions/import', { method: 'POST', body: fd });
      setStage('识别题目中…');
      await runTask(`/questions/${r.document_id}/generate`, { method: 'POST' }, '生成题库');
      setStage('');
      message.success(`已生成题库《${file.name}》`);
      await load();
    } catch (e) { setStage(''); message.info(e.message || '导入失败'); }
  };

  const del = async (id) => {
    try {
      await api(`/questions/banks/${id}`, { method: 'DELETE' });
      message.success('已删除题库');
      await load();
    } catch (e) { message.error(e.message); }
  };

  return (
    <div style={{ maxWidth: 980, margin: '0 auto' }}>
      <div className="row between" style={{ marginBottom: 14 }}>
        <div>
          <h1 style={{ fontSize: 20, margin: 0 }}>题库</h1>
          <div className="vmuted2">上传试卷 PDF 自动抽题成题库；教材解析请去「资料」页</div>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <Button onClick={() => navigate('/study')}>去刷题 <ArrowRightOutlined /></Button>
          <Button type="primary" icon={<FileAddOutlined />} onClick={() => fileRef.current?.click()}
            loading={!!stage}>{stage || '导入题库'}</Button>
          <input ref={fileRef} type="file" hidden accept=".pdf,.xlsx,.xlsm,.docx,.txt,.md"
            onChange={(e) => { importFile(e.target.files[0]); e.target.value = ''; }} />
        </div>
      </div>

      <div className="vmuted2" style={{ marginBottom: 12 }}>{EXT_HINT} · 试卷类 PDF 会逐页视觉识别抽题，约 1–5 分钟/份</div>

      {banks.length === 0 && !loading ? (
        <EmptyState
          title="还没有题库"
          desc="上传一份真题试卷 PDF，自动识别题目并生成可练的题库；教材/讲义请去「资料」页解析成卡片。"
          action={<Button type="primary" icon={<FileAddOutlined />} onClick={() => fileRef.current?.click()}>导入题库</Button>}
        />
      ) : (
        <Table rowKey={(r) => String(r.id ?? 'loose')} size="small" loading={loading}
          dataSource={banks}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          columns={[
            { title: '题库', dataIndex: 'name', ellipsis: true,
              render: (v, r) => <span>{esc(v)}</span> },
            { title: '科目', dataIndex: 'subject', width: 140,
              render: (v) => (v ? <Tag>{esc(v)}</Tag> : <span className="vmuted2">—</span>) },
            { title: '题数', dataIndex: 'total', width: 80,
              render: (v) => <b>{v}</b> },
            { title: '章节', dataIndex: 'chapters', width: 90,
              render: (chs) => <span className="vmuted2">{(chs || []).length} 章</span> },
            { title: '导入时间', dataIndex: 'created_at', width: 160,
              render: (v) => <span className="vmuted2">{v ? fmtTs(v) : '—'}</span> },
            { title: '', key: 'act', width: 130,
              render: (_, r) => (
                <div className="row" style={{ gap: 4, justifyContent: 'flex-end' }}>
                  <Button size="small" type="link" onClick={() => navigate('/study?bank=' + r.id)}>去刷</Button>
                  {r.id != null && (
                    <Popconfirm title="删除这个题库？题目一并删除" onConfirm={() => del(r.id)}>
                      <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  )}
                </div>
              ) },
          ]} />
      )}
    </div>
  );
}
