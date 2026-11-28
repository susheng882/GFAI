import React, { useCallback, useEffect, useState } from 'react';
import { App as AntdApp, Button, Progress, Table, Tag } from 'antd';
import { api, shortErr, STATUS_CN, TYPE_CN } from '../api.js';
import { summarize } from '../utils.js';

/* 后台任务列表：进度、错误脱敏、放弃、重试、清理旧失败。 */
export default function TasksPage() {
  const { message, modal } = AntdApp.useApp();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setTasks(await api('/tasks?limit=30') || []); } catch { setTasks([]); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  // B3：清理历史任务必须二次确认，避免误删仍在排查的失败记录
  const cleanup = () => modal.confirm({
    title: '清理历史任务？',
    content: '将删除 3 天前失败的任务记录，已完成的记录会保留，此操作不可撤销。',
    okText: '清理', okButtonProps: { danger: true }, cancelText: '取消',
    onOk: async () => {
      try {
        const r = await api('/tasks/cleanup', { method: 'POST' });
        message.success(`已清理 ${r?.deleted || 0} 条`); await load();
      } catch (e) { message.error(e.message); }
    },
  });
  const abort = (t) => modal.confirm({
    title: '放弃这个任务？', content: '已产生的中间结果会丢弃。',
    okText: '放弃', okButtonProps: { danger: true }, cancelText: '取消',
    onOk: async () => {
      try { await api(`/tasks/${t.id}/abort`, { method: 'POST' }); message.success('已放弃该任务'); await load(); }
      catch (e) { message.error(e.message); }
    },
  });
  const retry = async (t) => {
    try { const r = await api(`/tasks/${t.id}/retry`, { method: 'POST' }); message.success('已重新入队 #' + (r.task_id || '')); await load(); }
    catch (e) { message.error(e.message); }
  };

  const columns = [
    { title: '类型', dataIndex: 'type', width: 120, render: (v) => TYPE_CN[v] || v },
    { title: '状态', dataIndex: 'status', width: 90, render: (v) => (
      <Tag color={v === 'ready' ? 'success' : v === 'failed' ? 'error' : 'processing'}>{STATUS_CN[v] || v}</Tag>
    ) },
    { title: '进度', dataIndex: 'progress', width: 160, render: (v, t) => t.status === 'failed'
      ? <span className="muted">未完成</span>
      : <><Progress percent={Math.round(v || 0)} size="small" style={{ width: 110 }} />
          {t.elapsed && <span className="muted mono" style={{ fontSize: 10.5 }}>{Math.round(t.elapsed)}s</span>}</> },
    { title: '结果 / 错误', dataIndex: 'error_message', render: (v, t) => (
      <span className="muted" style={{ fontSize: 12.5 }}>{shortErr(v) || summarize(t.result)}</span>
    ) },
    { title: '', width: 110, render: (_, t) => (
      <span className="row" style={{ gap: 4, flexWrap: 'nowrap' }}>
        {t.can_abort && <Button size="small" type="text" onClick={() => abort(t)}>放弃</Button>}
        {t.can_retry && <Button size="small" type="text" onClick={() => retry(t)}>重试</Button>}
      </span>
    ) },
  ];

  return (
    <div>
      <div className="row between" style={{ marginBottom: 12 }}>
        <span className="muted" style={{ fontSize: 12.5 }}>最近 30 条后台任务 · 卡住会被看门狗判失败，可一键重试</span>
        <span className="row"><Button size="small" type="text" onClick={cleanup}>清理历史任务</Button>
          <Button size="small" onClick={load} loading={loading}>刷新</Button></span>
      </div>
      <div className="card" style={{ padding: '6px 14px' }}>
        <Table rowKey="id" columns={columns} dataSource={tasks} size="small" pagination={false} loading={loading}
          locale={{ emptyText: '还没有后台任务。上传 PDF、导入题库、生成视频笔记都会在这里留下记录。' }} />
      </div>
    </div>
  );
}
