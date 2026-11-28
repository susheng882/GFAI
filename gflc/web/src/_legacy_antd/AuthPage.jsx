import React, { useState } from 'react';
import { Button, Input } from 'antd';
import { api } from '../api.js';

/* 登录 / 注册：沿用旧版 renderAuth() + doAuth() 的语义，凭据走 HttpOnly Cookie。 */
export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const submit = async () => {
    if (!email.trim() || !password) { setErr('请填写邮箱和密码'); return; }
    setBusy(true); setErr('');
    try {
      await api('/auth/' + mode, { method: 'POST', body: JSON.stringify({ email: email.trim(), password }) });
      const me = await api('/auth/me');
      onAuth(me?.user || { email });
    } catch (e) {
      setErr(e.message);
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="brand"><span className="logo">G</span><span>GrowthForward</span></div>
        <div className="panel">
          <h1 style={{ fontSize: 20, margin: '0 0 4px', letterSpacing: '-.3px' }}>
            {mode === 'login' ? '登录' : '创建账号'}
          </h1>
          <p className="muted" style={{ margin: '0 0 20px', fontSize: 13, lineHeight: 1.65 }}>
            把 PDF、视频和试卷，变成能背的卡片和题库。
          </p>
          <div style={{ marginBottom: 12 }}>
            <label className="lbl">邮箱</label>
            <Input type="email" value={email} placeholder="you@example.com" autoComplete="username"
              onChange={(e) => setEmail(e.target.value)} onPressEnter={submit} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label className="lbl">密码</label>
            <Input.Password value={password} placeholder="至少 8 位" autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)} onPressEnter={submit} />
          </div>
          {err && <div style={{ color: 'var(--destructive)', fontSize: 12.5, marginBottom: 10 }}>{err}</div>}
          <Button type="primary" block loading={busy} onClick={submit}>
            {mode === 'login' ? '登录' : '注册'}
          </Button>
          <div className="row" style={{ justifyContent: 'center', marginTop: 14 }}>
            <span className="muted" style={{ fontSize: 13 }}>{mode === 'login' ? '还没有账号？' : '已有账号？'}</span>
            <a style={{ color: 'var(--primary)', cursor: 'pointer', fontSize: 13 }}
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setErr(''); }}>
              {mode === 'login' ? '去注册' : '去登录'}
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
