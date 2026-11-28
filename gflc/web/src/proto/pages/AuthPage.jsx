import React, { useMemo, useState } from 'react';
import { CheckIcon, SparkIcon } from '../NavIcons.jsx';
import { Badge, Btn, cx } from '../ui.jsx';
import { authBrand, authDemo, profile } from '../mock/index.js';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * 登录 / 注册（/auth）
 * 沿用旧版 renderAuth() + doAuth() 的语义：邮箱 + 密码校验，成功后进入应用；
 * mock 环境不发请求，「凭据走 HttpOnly Cookie」仅作为文案与后续接线的约定。
 */
export default function AuthPage({ onLogin }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ email: '', password: '', nickname: '' });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const isRegister = mode === 'register';
  const submitLabel = useMemo(() => (isRegister ? '注册并进入' : '登录'), [isRegister]);

  const setField = (key) => (e) => {
    const { value } = e.target;
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => (prev[key] || prev.form ? { ...prev, [key]: undefined, form: undefined } : prev));
  };

  const validate = () => {
    const next = {};
    if (!form.email.trim()) next.email = '请输入邮箱';
    else if (!EMAIL_RE.test(form.email.trim())) next.email = '邮箱格式不正确';
    if (!form.password) next.password = '请输入密码';
    else if (form.password.length < 6) next.password = '密码至少 6 位';
    if (isRegister && !form.nickname.trim()) next.nickname = '请输入昵称';
    return next;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const next = validate();
    if (Object.keys(next).length) {
      setErrors(next);
      return;
    }
    setErrors({});
    setSubmitting(true);
    // mock 登录：不请求后端，200ms 后直接进入应用
    window.setTimeout(() => {
      setSubmitting(false);
      onLogin({
        ...profile,
        email: form.email.trim(),
        name: isRegister ? form.nickname.trim() : authDemo.name,
        initial: (isRegister ? form.nickname.trim() : authDemo.name).slice(0, 1).toUpperCase(),
      });
    }, 200);
  };

  const switchMode = () => {
    setMode((m) => (m === 'login' ? 'register' : 'login'));
    setErrors({});
  };

  return (
    <div className="flex min-h-full w-full items-center justify-center bg-page px-6 py-8">
      <div className="grid w-full max-w-[980px] overflow-hidden rounded-[16px] border border-line bg-card lg:grid-cols-[1.05fr_1fr]">
        {/* 左：品牌介绍 + 学习数据概览三宫格 */}
        <div className="hidden flex-col justify-between border-r border-line bg-sider p-10 lg:flex">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-[9px] bg-ink text-[12px] font-medium text-white">
                GF
              </span>
              <div>
                <p className="text-[14px] font-medium leading-[18px] text-ink">
                  {authBrand.product} · {authBrand.productCn}
                </p>
                <p className="text-[10px] leading-[14px] text-ink3">考研学习伴侣 · 本地部署</p>
              </div>
            </div>

            <h1 className="mt-8 text-[22px] font-medium leading-[30px] text-ink">{authBrand.tagline}</h1>

            <ul className="mt-5 flex flex-col gap-3">
              {authBrand.highlights.map((text) => (
                <li key={text} className="flex items-start gap-2.5">
                  <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-brandSoft text-brand">
                    <CheckIcon size={10} strokeWidth={2} />
                  </span>
                  <span className="text-[12px] leading-[19px] text-ink2">{text}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-8">
            <div className="grid grid-cols-3 divide-x divide-line overflow-hidden rounded-[10px] border border-line bg-card">
              {authBrand.stats.map((s) => (
                <div key={s.label} className="px-3 py-3">
                  <p className="gf-num text-[16px] font-medium leading-[22px] text-ink">{s.value}</p>
                  <p className="mt-0.5 text-[10px] leading-[14px] text-ink3">{s.label}</p>
                </div>
              ))}
            </div>
            <p className="mt-3 flex items-center gap-1.5 text-[10px] leading-[14px] text-ink3">
              <SparkIcon size={12} className="shrink-0" />
              {authBrand.footer}
            </p>
          </div>
        </div>

        {/* 右：登录卡 */}
        <div className="flex flex-col justify-center p-8 sm:p-10">
          <div className="mb-6 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-[19px] font-medium leading-[26px] text-ink">
                {isRegister ? '创建账号' : '登录 GFLC'}
              </h2>
              <p className="mt-1 text-[12px] leading-[18px] text-ink3">
                {isRegister ? '注册后本地生成学习工作区，数据只存本机' : '用你的邮箱继续今天的学习'}
              </p>
            </div>
            <Badge tone="line">v8</Badge>
          </div>

          <form className="flex flex-col gap-3.5" onSubmit={handleSubmit} noValidate>
            {isRegister ? (
              <label className="flex flex-col gap-1.5">
                <span className="text-[12px] leading-[16px] text-ink2">昵称</span>
                <input
                  className={cx('gf-input', errors.nickname && 'border-bad')}
                  value={form.nickname}
                  onChange={setField('nickname')}
                  placeholder="怎么称呼你"
                  autoComplete="nickname"
                />
                {errors.nickname ? (
                  <span className="text-[11px] leading-[15px] text-[#C4322B]">{errors.nickname}</span>
                ) : null}
              </label>
            ) : null}

            <label className="flex flex-col gap-1.5">
              <span className="text-[12px] leading-[16px] text-ink2">邮箱</span>
              <input
                className={cx('gf-input', errors.email && 'border-bad')}
                value={form.email}
                onChange={setField('email')}
                placeholder="you@example.com"
                type="email"
                autoComplete="email"
                inputMode="email"
              />
              {errors.email ? (
                <span className="text-[11px] leading-[15px] text-[#C4322B]">{errors.email}</span>
              ) : null}
            </label>

            <label className="flex flex-col gap-1.5">
              <span className="text-[12px] leading-[16px] text-ink2">密码</span>
              <input
                className={cx('gf-input', errors.password && 'border-bad')}
                value={form.password}
                onChange={setField('password')}
                placeholder="至少 6 位"
                type="password"
                autoComplete={isRegister ? 'new-password' : 'current-password'}
              />
              {errors.password ? (
                <span className="text-[11px] leading-[15px] text-[#C4322B]">{errors.password}</span>
              ) : null}
            </label>

            {errors.form ? (
              <p role="alert" className="rounded-[10px] bg-[#FDECEC] px-3 py-2 text-[11px] leading-[15px] text-[#C4322B]">
                {errors.form}
              </p>
            ) : null}

            <Btn type="submit" variant="solid" size="md" className="mt-1 w-full" disabled={submitting}>
              {submitting ? '请稍候…' : submitLabel}
            </Btn>
          </form>

          <div className="mt-4 flex items-center justify-between gap-3">
            <p className="text-[11px] leading-[16px] text-ink3">
              {isRegister ? '已有账号？' : '还没有账号？'}
              <button
                type="button"
                onClick={switchMode}
                className="ml-1 text-[11px] font-medium text-brand hover:underline"
              >
                {isRegister ? '返回登录' : '立即注册'}
              </button>
            </p>
            <button type="button" className="text-[11px] text-ink3 hover:text-ink">
              忘记密码
            </button>
          </div>

          <div className="mt-6 rounded-[10px] border border-line bg-page px-3 py-2.5">
            <p className="text-[10px] leading-[15px] text-ink3">
              演示环境（mock）：{authDemo.email} / {authDemo.password}；任意格式合法的邮箱与 6 位以上密码也可进入。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
