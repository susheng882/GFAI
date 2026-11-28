import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Badge, Btn, Card, Divider, Progress, SectionTitle, cx } from '../ui.jsx';
import { CheckIcon, PlusIcon, SparkIcon, UploadIcon } from '../NavIcons.jsx';
import {
  accountDevices,
  accountProfile,
  accountStats,
  settingsAbout,
  settingsAccount,
  settingsAppearance,
  settingsBackup,
  settingsCookie,
  settingsDiag,
  settingsGroups,
  settingsModels,
  settingsNotify,
  settingsProviders,
  settingsTranscriber,
} from '../mock/index.js';

const STATUS_TONE = { ok: 'ok', warn: 'warn', bad: 'bad' };
const STATUS_TEXT = { ok: '正常', warn: '受限', bad: '异常' };
const DIAG_TONE = { ok: 'bg-ok', warn: 'bg-warn', bad: 'bg-bad' };

/** 表单字段：11px 标签 + 输入框 */
function Field({ label, children, className = '' }) {
  return (
    <label className={cx('flex min-w-0 flex-col gap-1', className)}>
      <span className="text-[11px] text-ink3">{label}</span>
      {children}
    </label>
  );
}

/** 开关 */
function Toggle({ on, onChange, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={() => onChange(!on)}
      className={cx(
        'relative h-5 w-9 shrink-0 rounded-full border transition-colors duration-150',
        on ? 'border-brand bg-brand' : 'border-line2 bg-line',
      )}
    >
      <span
        className={cx(
          'absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all duration-150',
          on ? 'left-[18px]' : 'left-0.5',
        )}
      />
    </button>
  );
}

/** 分段选择 */
function Segmented({ options, value, onChange }) {
  return (
    <div className="inline-flex rounded-[10px] border border-line bg-card p-0.5">
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          onClick={() => onChange(o.id)}
          className={cx(
            'h-6 rounded-[8px] px-2.5 text-[11px] transition-colors',
            value === o.id ? 'bg-brandSoft text-brand' : 'text-ink2 hover:bg-sel',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function SettingRow({ title, desc, children, last = false }) {
  return (
    <div className={cx('flex items-center justify-between gap-4 py-2.5', !last && 'border-b border-line')}>
      <div className="min-w-0">
        <p className="text-[12px] text-ink">{title}</p>
        {desc ? <p className="mt-0.5 text-[11px] text-ink3">{desc}</p> : null}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

const PROV_COLS = 'grid-cols-[minmax(0,1.1fr)_minmax(0,1.7fr)_minmax(0,1fr)_52px_64px_60px_104px]';
const MODEL_COLS = 'grid-cols-[minmax(0,1.2fr)_minmax(0,0.9fr)_minmax(0,1.1fr)_64px_136px_56px_56px]';

export default function SettingsPage({ onLogout }) {
  const navigate = useNavigate();
  const [group, setGroup] = useState('account');
  const [note, setNote] = useState('');

  /* 账号与工作区 */
  const [account, setAccount] = useState(() => ({
    name: settingsAccount.user.name,
    email: settingsAccount.user.email,
    school: settingsAccount.user.school,
    major: settingsAccount.user.major,
  }));
  const [pending, setPending] = useState('');

  /* 供应商 */
  const [providers, setProviders] = useState(() => settingsProviders.map((p) => ({ ...p })));
  const [edit, setEdit] = useState(null);

  /* 模型 */
  const [models, setModels] = useState(() => settingsModels.map((m) => ({ ...m })));

  /* 转录器 */
  const [transcriber, setTranscriber] = useState(settingsTranscriber.current);

  /* Cookie */
  const [cookie, setCookie] = useState(settingsCookie.masked);

  /* 通知 */
  const [notify, setNotify] = useState(() => settingsNotify.map((n) => ({ ...n })));

  /* 外观 */
  const [theme, setTheme] = useState(settingsAppearance.theme.current);
  const [density, setDensity] = useState(settingsAppearance.density.current);
  const [sidebar, setSidebar] = useState(settingsAppearance.sidebar.current);
  const [motion, setMotion] = useState(settingsAppearance.motion.current);
  const [fontScale, setFontScale] = useState(settingsAppearance.fontScale.current);

  /* 备份 */
  const [lastBackup, setLastBackup] = useState('');

  const current = useMemo(() => settingsGroups.find((g) => g.id === group) || settingsGroups[0], [group]);
  const activeCount = notify.filter((n) => n.on).length;

  const startAdd = () =>
    setEdit({
      id: 'new',
      draft: { id: 'new', name: '', kind: 'OpenAI 兼容', baseUrl: '', key: '', models: 0, status: 'ok', latency: '—', weight: 0 },
    });

  const startEdit = (p) => setEdit({ id: p.id, draft: { ...p } });

  const patchDraft = (patch) => setEdit((prev) => (prev ? { ...prev, draft: { ...prev.draft, ...patch } } : prev));

  const saveDraft = () => {
    if (!edit) return;
    const name = (edit.draft.name || '').trim();
    if (!name) {
      setNote('供应商名称不能为空');
      return;
    }
    setProviders((prev) => {
      const exists = prev.some((p) => p.id === edit.id);
      const row = { ...edit.draft, name };
      return exists ? prev.map((p) => (p.id === edit.id ? row : p)) : [...prev, { ...row, id: `p${Date.now()}` }];
    });
    setNote(edit.id === 'new' ? `已新增供应商「${name}」` : `已保存供应商「${name}」`);
    setEdit(null);
  };

  const removeProvider = (p) => {
    setProviders((prev) => prev.filter((x) => x.id !== p.id));
    setNote(`已删除供应商「${p.name}」`);
  };

  const patchNotify = (id, on) => setNotify((prev) => prev.map((n) => (n.id === id ? { ...n, on } : n)));
  const toggleModel = (id) => setModels((prev) => prev.map((m) => (m.id === id ? { ...m, enabled: !m.enabled } : m)));
  const setDefaultModel = (id) =>
    setModels((prev) => prev.map((m) => ({ ...m, isDefault: m.id === id ? true : false, enabled: m.id === id ? true : m.enabled })));

  const doLogout = () => {
    if (onLogout) onLogout();
    navigate('/auth', { replace: true });
  };

  const renderPanel = () => {
    if (group === 'account') {
      return (
        <>
          <div className="flex items-center gap-3 rounded-[10px] border border-line px-3 py-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-sel text-[14px] font-medium text-ink">
              {settingsAccount.user.initial}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] text-ink">
                {account.name}
                <span className="ml-2 align-middle">
                  <Badge tone="brand">{settingsAccount.user.role}</Badge>
                </span>
              </p>
              <p className="mt-0.5 truncate text-[11px] text-ink3">
                {account.email} · {settingsAccount.security.lastLogin}
              </p>
            </div>
            <Badge tone="ok" dot>
              {settingsAccount.security.devices}
            </Badge>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2.5">
            <Field label="姓名">
              <input
                className="gf-input h-8"
                value={account.name}
                onChange={(e) => setAccount({ ...account, name: e.target.value })}
              />
            </Field>
            <Field label="邮箱">
              <input
                className="gf-input h-8"
                value={account.email}
                onChange={(e) => setAccount({ ...account, email: e.target.value })}
              />
            </Field>
            <Field label="学校">
              <input
                className="gf-input h-8"
                value={account.school}
                onChange={(e) => setAccount({ ...account, school: e.target.value })}
              />
            </Field>
            <Field label="专业">
              <input
                className="gf-input h-8"
                value={account.major}
                onChange={(e) => setAccount({ ...account, major: e.target.value })}
              />
            </Field>
          </div>

          <div className="mt-3 rounded-[10px] border border-line px-3 py-2">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[12px] text-ink">{settingsAccount.workspace.name}</p>
              <div className="flex items-center gap-1.5">
                <Badge tone="neutral">{settingsAccount.workspace.plan}</Badge>
                <Badge tone="neutral">席位 {settingsAccount.workspace.seats}</Badge>
              </div>
            </div>
            <p className="mt-1 text-[11px] text-ink3">
              {settingsAccount.workspace.storage} · 创建于 {settingsAccount.workspace.createdAt}
            </p>
            <Progress value={settingsAccount.workspace.usedPercent} className="mt-1.5" />
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2.5">
            <Card className="rounded-[10px]">
              <SectionTitle title="学习档案" sub="备考目标与进度" />
              <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
                {accountProfile.map((p) => (
                  <div key={p.key} className="min-w-0">
                    <p className="text-[11px] text-ink3">{p.label}</p>
                    <p className="mt-0.5 truncate text-[12px] text-ink">{p.value}</p>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="rounded-[10px]">
              <SectionTitle title="数据统计" sub="本地累计数据" />
              <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
                {accountStats.map((s) => (
                  <div key={s.key} className="min-w-0">
                    <p className="text-[11px] text-ink3">{s.label}</p>
                    <p className="gf-num mt-0.5 text-[18px] font-medium leading-[22px] text-ink">
                      {s.value}
                      <span className="ml-1 text-[11px] font-normal text-ink3">{s.unit}</span>
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <div className="mt-2.5">
            <SectionTitle title="登录设备" sub="当前账号已登录的设备" action={<Badge tone="ok" dot>{settingsAccount.security.devices}</Badge>} />
            <div className="rounded-[10px] border border-line">
              {accountDevices.map((d, i) => (
                <div
                  key={d.id}
                  className={cx('flex items-center gap-3 px-3 py-2.5', i !== accountDevices.length - 1 && 'border-b border-line')}
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] bg-sel text-[12px] font-medium text-ink">
                    {d.name.slice(0, 1)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="flex items-center gap-1.5 text-[12px] text-ink">
                      <span className="truncate">{d.name}</span>
                      {d.current ? <Badge tone="brand">当前</Badge> : null}
                    </p>
                    <p className="mt-0.5 truncate text-[11px] text-ink3">{d.detail}</p>
                  </div>
                  <span className="gf-num shrink-0 text-[11px] text-ink3">{d.time}</span>
                </div>
              ))}
            </div>
          </div>

          <Divider className="my-3" />

          <p className="mb-1.5 text-[11px] text-ink3">危险区</p>
          <div className="rounded-[10px] border border-line">
            {settingsAccount.danger.map((d, i) => (
              <div
                key={d.id}
                className={cx('flex items-center justify-between gap-4 px-3 py-2.5', i === 0 && 'border-b border-line')}
              >
                <div className="min-w-0">
                  <p className="text-[12px] text-ink">{d.title}</p>
                  <p className="mt-0.5 text-[11px] text-ink3">{d.desc}</p>
                </div>
                {pending === d.id ? (
                  <div className="flex shrink-0 items-center gap-1.5">
                    <Btn
                      size="xs"
                      variant="line"
                      className="text-bad"
                      onClick={() => {
                        if (d.id === 'logout') doLogout();
                        else setNote('注销账号为破坏性操作，原型中未执行');
                        setPending('');
                      }}
                    >
                      确认{d.action}
                    </Btn>
                    <Btn size="xs" variant="ghost" onClick={() => setPending('')}>
                      取消
                    </Btn>
                  </div>
                ) : (
                  <Btn size="xs" variant="line" className={cx(d.id === 'delete' && 'text-bad')} onClick={() => setPending(d.id)}>
                    {d.action}
                  </Btn>
                )}
              </div>
            ))}
          </div>
        </>
      );
    }

    if (group === 'providers') {
      return (
        <>
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="text-[11px] text-ink3">共 {providers.length} 个供应商 · 调用权重合计 {providers.reduce((s, p) => s + (Number(p.weight) || 0), 0)}%</p>
            <Btn size="xs" variant="line" icon={<PlusIcon size={12} />} onClick={startAdd}>
              新增供应商
            </Btn>
          </div>
          <div className={cx('grid items-center gap-2 rounded-[8px] bg-page px-2 py-1.5 text-[10px] text-ink3', PROV_COLS)}>
            <span>供应商</span>
            <span>接口地址</span>
            <span>密钥</span>
            <span>模型</span>
            <span>延迟</span>
            <span>状态</span>
            <span className="text-right">操作</span>
          </div>
          {[...providers, ...(edit && edit.id === 'new' ? [{ ...edit.draft, id: 'new' }] : [])].map((p) => {
            const isEdit = edit && edit.id === p.id;
            if (isEdit) {
              return (
                <div key={p.id} className={cx('grid items-center gap-2 border-b border-line px-2 py-1.5', PROV_COLS)}>
                  <input className="gf-input h-7 text-[11px]" value={edit.draft.name} onChange={(e) => patchDraft({ name: e.target.value })} placeholder="名称" />
                  <input className="gf-input h-7 text-[11px]" value={edit.draft.baseUrl} onChange={(e) => patchDraft({ baseUrl: e.target.value })} placeholder="https://…" />
                  <input className="gf-input h-7 text-[11px]" value={edit.draft.key} onChange={(e) => patchDraft({ key: e.target.value })} placeholder="sk-…" />
                  <input
                    className="gf-input gf-num h-7 text-[11px]"
                    value={edit.draft.weight}
                    onChange={(e) => patchDraft({ weight: e.target.value })}
                  />
                  <span className="text-[11px] text-ink3">{edit.draft.latency || '—'}</span>
                  <Badge tone="neutral">待保存</Badge>
                  <div className="flex items-center justify-end gap-1">
                    <Btn size="xs" variant="solid" onClick={saveDraft}>
                      保存
                    </Btn>
                    <Btn size="xs" variant="ghost" onClick={() => setEdit(null)}>
                      取消
                    </Btn>
                  </div>
                </div>
              );
            }
            return (
              <div key={p.id} className={cx('grid items-center gap-2 border-b border-line px-2 py-2 last:border-0', PROV_COLS)}>
                <div className="min-w-0">
                  <p className="truncate text-[12px] text-ink">{p.name}</p>
                  <p className="mt-0.5 text-[10px] text-ink3">
                    {p.kind} · 权重 {p.weight}%
                  </p>
                </div>
                <span className="truncate text-[11px] text-ink2">{p.baseUrl || '—'}</span>
                <span className="truncate text-[11px] text-ink3">{p.key || '—'}</span>
                <span className="gf-num text-[11px] text-ink2">{p.models}</span>
                <span className="gf-num text-[11px] text-ink2">{p.latency}</span>
                <Badge tone={STATUS_TONE[p.status] || 'neutral'}>{STATUS_TEXT[p.status] || p.status}</Badge>
                <div className="flex items-center justify-end gap-1">
                  <Btn size="xs" variant="line" onClick={() => startEdit(p)}>
                    编辑
                  </Btn>
                  <Btn size="xs" variant="ghost" className="text-bad" onClick={() => removeProvider(p)}>
                    删除
                  </Btn>
                </div>
              </div>
            );
          })}
          <p className="mt-2 text-[11px] text-ink3">密钥在界面只回显掩码；供应商全部走 OpenAI 兼容协议，失败时按权重降级到下一个。</p>
        </>
      );
    }

    if (group === 'models') {
      return (
        <>
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="text-[11px] text-ink3">
              共 {models.length} 个模型 · 已启用 {models.filter((m) => m.enabled).length} 个 · 用途标签决定路由
            </p>
            <Badge tone="brand">默认：{models.find((m) => m.isDefault)?.name || '未设置'}</Badge>
          </div>
          <div className={cx('grid items-center gap-2 rounded-[8px] bg-page px-2 py-1.5 text-[10px] text-ink3', MODEL_COLS)}>
            <span>模型</span>
            <span>供应商</span>
            <span>用途</span>
            <span>上下文</span>
            <span>价格</span>
            <span>启用</span>
            <span className="text-right">默认</span>
          </div>
          {models.map((m) => (
            <div key={m.id} className={cx('grid items-center gap-2 border-b border-line px-2 py-2 last:border-0', MODEL_COLS)}>
              <span className="truncate text-[12px] text-ink">{m.name}</span>
              <span className="truncate text-[11px] text-ink2">{m.vendor}</span>
              <span className="flex flex-wrap items-center gap-1">
                {m.purposes.map((t) => (
                  <Badge key={t} tone={t === '嵌入' || t === '重排' ? 'neutral' : 'brand'}>
                    {t}
                  </Badge>
                ))}
              </span>
              <span className="gf-num text-[11px] text-ink2">{m.context}</span>
              <span className="truncate text-[11px] text-ink3">{m.price}</span>
              <span>
                <Toggle on={m.enabled} onChange={() => toggleModel(m.id)} label={`${m.name} 启用`} />
              </span>
              <span className="flex justify-end">
                {m.isDefault ? (
                  <Badge tone="ok" dot>
                    默认
                  </Badge>
                ) : (
                  <Btn size="xs" variant="ghost" onClick={() => setDefaultModel(m.id)}>
                    设为默认
                  </Btn>
                )}
              </span>
            </div>
          ))}
        </>
      );
    }

    if (group === 'transcriber') {
      return (
        <>
          <div className="flex flex-col gap-2">
            {settingsTranscriber.options.map((o) => {
              const on = transcriber === o.id;
              return (
                <button
                  key={o.id}
                  type="button"
                  onClick={() => {
                    setTranscriber(o.id);
                    setNote(`转录器已切换为 ${o.name}`);
                  }}
                  className={cx(
                    'flex items-center gap-3 rounded-[10px] border px-3 py-2.5 text-left transition-colors',
                    on ? 'border-brand bg-brandSoft' : 'border-line bg-card hover:bg-page',
                  )}
                >
                  <span
                    className={cx(
                      'flex h-4 w-4 shrink-0 items-center justify-center rounded-full border',
                      on ? 'border-brand bg-brand text-white' : 'border-line2 bg-card',
                    )}
                  >
                    {on ? <CheckIcon size={10} /> : null}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="flex items-center gap-1.5 text-[12px] text-ink">
                      {o.name}
                      <span className="text-[11px] text-ink3">{o.vendor}</span>
                      {o.tag ? <Badge tone={o.tag === '推荐' ? 'brand' : 'ok'}>{o.tag}</Badge> : null}
                    </p>
                    <p className="mt-0.5 text-[11px] text-ink3">{o.note}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="gf-num text-[11px] text-ink2">速度 {o.speed}</p>
                    <p className="gf-num mt-0.5 text-[11px] text-ink3">准确率 {o.accuracy}</p>
                  </div>
                </button>
              );
            })}
          </div>
          <div className="mt-2.5 grid grid-cols-3 gap-2">
            {[
              ['运行设备', settingsTranscriber.runtime.device],
              ['当前队列', settingsTranscriber.runtime.queue],
              ['实测耗时', settingsTranscriber.runtime.sample],
            ].map(([k, v]) => (
              <div key={k} className="rounded-[10px] border border-line px-2.5 py-2">
                <p className="text-[11px] text-ink3">{k}</p>
                <p className="mt-0.5 truncate text-[11px] text-ink2">{v}</p>
              </div>
            ))}
          </div>
        </>
      );
    }

    if (group === 'cookie') {
      return (
        <>
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[12px] text-ink">{settingsCookie.platform}</p>
              <p className="mt-0.5 text-[11px] text-ink3">采集范围：{settingsCookie.scope}</p>
            </div>
            <div className="flex shrink-0 items-center gap-1.5">
              <Badge tone="ok" dot>
                {settingsCookie.status}
              </Badge>
              <Badge tone="neutral">更新于 {settingsCookie.updatedAt}</Badge>
            </div>
          </div>
          <div className="mt-2.5">
            <Field label="Cookie 字符串（保存后仅回显掩码）">
              <input className="gf-input h-8" value={cookie} onChange={(e) => setCookie(e.target.value)} />
            </Field>
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            <Btn size="xs" variant="solid" onClick={() => setNote('B 站 Cookie 已保存（仅本地）')}>
              保存 Cookie
            </Btn>
            <Btn size="xs" variant="line" icon={<UploadIcon size={12} />} onClick={() => setNote('Cookie 校验通过，有效期约 30 天')}>
              校验有效性
            </Btn>
            <span className="text-[11px] text-ink3">{settingsCookie.lastSync}</span>
          </div>
          <Divider className="my-2.5" />
          <p className="mb-1 text-[11px] text-ink3">注意事项</p>
          <ul className="flex flex-col gap-1">
            {settingsCookie.tips.map((t) => (
              <li key={t} className="flex gap-1.5 text-[11px] text-ink2">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-line2" />
                <span className="min-w-0">{t}</span>
              </li>
            ))}
          </ul>
        </>
      );
    }

    if (group === 'notify') {
      return (
        <>
          <div className="mb-1 flex items-center justify-between">
            <p className="text-[11px] text-ink3">已开启 {activeCount} / {notify.length} 项</p>
            <Badge tone="neutral">免打扰 23:30 – 07:30</Badge>
          </div>
          {notify.map((n) => (
            <div key={n.id} className="flex items-center justify-between gap-4 border-b border-line py-2 last:border-0">
              <div className="min-w-0">
                <p className="text-[12px] text-ink">
                  {n.label}
                  <span className="ml-1.5 text-[10px] text-ink3">{n.channel}</span>
                </p>
                <p className="mt-0.5 text-[11px] text-ink3">{n.desc}</p>
              </div>
              <Toggle on={n.on} onChange={(v) => patchNotify(n.id, v)} label={n.label} />
            </div>
          ))}
        </>
      );
    }

    if (group === 'appearance') {
      return (
        <>
          <SettingRow title="主题" desc="深色与跟随系统在原型中只记录偏好">
            <Segmented options={settingsAppearance.theme.options} value={theme} onChange={setTheme} />
          </SettingRow>
          <SettingRow title="信息密度" desc="紧凑：行高 32px；标准：行高 40px" >
            <Segmented options={settingsAppearance.density.options} value={density} onChange={setDensity} />
          </SettingRow>
          <SettingRow title="侧栏默认状态" desc="下次加载时侧栏的展开/收起">
            <Segmented options={settingsAppearance.sidebar.options} value={sidebar} onChange={setSidebar} />
          </SettingRow>
          <SettingRow title="界面动效" desc="关闭后列表与卡片不做淡入位移">
            <Segmented options={settingsAppearance.motion.options} value={motion} onChange={setMotion} />
          </SettingRow>
          <SettingRow title="正文字号" desc="仅影响阅读区，标题与数字不变" last>
            <Segmented options={settingsAppearance.fontScale.options} value={fontScale} onChange={setFontScale} />
          </SettingRow>
          <div className="mt-2 rounded-[10px] border border-line bg-page px-3 py-2">
            <p className="text-[11px] text-ink3">预览</p>
            <p className={cx('mt-1 text-ink', fontScale === '12' && 'text-[12px]', fontScale === '13' && 'text-[13px]', fontScale === '14' && 'text-[14px]')}>
              操作系统中的页面置换算法：最佳置换 OPT、先进先出 FIFO、最近最久未使用 LRU。
            </p>
          </div>
        </>
      );
    }

    if (group === 'backup') {
      return (
        <>
          <p className="mb-2 text-[11px] text-ink3">{settingsBackup.summary}</p>
          <div className="grid grid-cols-2 gap-2">
            {settingsBackup.actions.map((a) => (
              <div key={a.id} className="rounded-[10px] border border-line px-3 py-2.5">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[12px] text-ink">{a.label}</p>
                  <Btn
                    size="xs"
                    variant={a.tone === 'solid' ? 'solid' : 'line'}
                    onClick={() => {
                      setLastBackup(a.label);
                      setNote(`已触发「${a.label}」`);
                    }}
                  >
                    执行
                  </Btn>
                </div>
                <p className="mt-1 text-[11px] text-ink2">{a.desc}</p>
                <p className="mt-0.5 text-[11px] text-ink3">{a.meta}</p>
              </div>
            ))}
          </div>
          <p className="mb-1 mt-2.5 text-[11px] text-ink3">最近快照</p>
          <div className="rounded-[8px] bg-page px-2 py-1 text-[10px] text-ink3">
            <div className="grid grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)_minmax(0,1fr)_64px] gap-2">
              <span>时间</span>
              <span>体积</span>
              <span>类型</span>
              <span className="text-right">状态</span>
            </div>
          </div>
          {settingsBackup.snapshots.map((s) => (
            <div key={s.id} className="grid grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)_minmax(0,1fr)_64px] items-center gap-2 border-b border-line px-2 py-2 last:border-0">
              <span className="gf-num truncate text-[11px] text-ink2">{s.time}</span>
              <span className="gf-num text-[11px] text-ink2">{s.size}</span>
              <span className="truncate text-[11px] text-ink3">{s.kind}</span>
              <span className="flex justify-end">
                <Badge tone={s.id === 's1' ? 'ok' : 'neutral'}>{s.id === 's1' ? '当前' : '可回滚'}</Badge>
              </span>
            </div>
          ))}
          {lastBackup ? <p className="mt-1.5 text-[11px] text-ink3">本次操作：{lastBackup} · 原型不写真实文件</p> : null}
        </>
      );
    }

    if (group === 'diag') {
      return (
        <>
          <div className="mb-1 flex items-center justify-between">
            <p className="text-[11px] text-ink3">采样时间 2026-11-27 09:42 · 每 30 秒刷新一次</p>
            <Badge tone="ok" dot>
              全部检查已执行
            </Badge>
          </div>
          {settingsDiag.map((d) => (
            <div key={d.id} className="flex items-center justify-between gap-4 border-b border-line py-2.5 last:border-0">
              <div className="flex min-w-0 items-center gap-2">
                <span className={cx('h-1.5 w-1.5 shrink-0 rounded-full', DIAG_TONE[d.tone] || 'bg-line2')} />
                <div className="min-w-0">
                  <p className="text-[12px] text-ink">{d.name}</p>
                  <p className="mt-0.5 truncate text-[11px] text-ink3">{d.hint}</p>
                </div>
              </div>
              <span className="gf-num shrink-0 text-[12px] text-ink2">{d.value}</span>
            </div>
          ))}
          <div className="mt-2 flex items-center gap-1.5">
            <Btn size="xs" variant="line" onClick={() => setNote('诊断已重新执行，5 项检查全部完成')}>
              重新诊断
            </Btn>
            <Btn size="xs" variant="ghost" icon={<SparkIcon size={12} />} onClick={() => setNote('诊断日志已复制到剪贴板（原型未真实复制）')}>
              导出诊断日志
            </Btn>
          </div>
        </>
      );
    }

    return (
      <>
        <div className="flex items-center gap-3 rounded-[10px] border border-line px-3 py-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-brandSoft text-[13px] font-medium text-brand">GF</span>
          <div className="min-w-0 flex-1">
            <p className="text-[12px] text-ink">GFLC 成长向前 · 考研学习伴侣</p>
            <p className="mt-0.5 text-[11px] text-ink3">{settingsAbout.stack}</p>
          </div>
          <Badge tone="brand">{settingsAbout.version}</Badge>
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2">
          {[
            ['构建信息', settingsAbout.build],
            ['发布渠道', settingsAbout.channel],
            ['数据来源', '本地 mock（无后端请求）'],
            ['运行形态', 'Vite 预览构建产物'],
          ].map(([k, v]) => (
            <div key={k} className="rounded-[10px] border border-line px-2.5 py-2">
              <p className="text-[11px] text-ink3">{k}</p>
              <p className="mt-0.5 truncate text-[11px] text-ink2">{v}</p>
            </div>
          ))}
        </div>
        <p className="mb-1 mt-2.5 text-[11px] text-ink3">更新日志</p>
        {settingsAbout.changelog.map((c) => (
          <div key={c.id} className="flex gap-3 border-b border-line py-1.5 last:border-0">
            <span className="gf-num shrink-0 text-[11px] text-ink3">{c.date}</span>
            <span className="min-w-0 text-[11px] text-ink2">{c.text}</span>
          </div>
        ))}
      </>
    );
  };

  return (
    <div className="flex animate-fade-up items-start gap-2.5">
      <Card pad={false} className="w-[188px] shrink-0 p-2">
        <p className="px-2 pb-1 pt-1 text-[11px] text-ink3">设置分组</p>
        <div className="flex flex-col gap-0.5">
          {settingsGroups.map((g) => {
            const on = group === g.id;
            return (
              <button
                key={g.id}
                type="button"
                onClick={() => {
                  setGroup(g.id);
                  setNote('');
                  setEdit(null);
                }}
                aria-current={on ? 'page' : undefined}
                className={cx(
                  'gf-nav h-7 w-full justify-start px-2 text-left text-[12px]',
                  on ? 'gf-nav-on text-ink' : 'text-ink2',
                )}
              >
                <span className="truncate">{g.label}</span>
              </button>
            );
          })}
        </div>
        <div className="mt-2 border-t border-line px-2 pt-2">
          <p className="gf-num text-[10px] text-ink3">{settingsAbout.version}</p>
          <p className="mt-0.5 text-[10px] text-ink3">数据源：本地 mock</p>
        </div>
      </Card>

      <Card className="min-w-0 flex-1">
        <SectionTitle
          title={current.label}
          sub={current.desc}
          action={
            <>
              {note ? <Badge tone="brand">{note}</Badge> : <Badge tone="neutral">本地 mock</Badge>}
              <Btn size="xs" variant="line" icon={<CheckIcon size={12} />} onClick={() => setNote('设置已保存到本地')}>
                保存设置
              </Btn>
            </>
          }
        />
        {renderPanel()}
      </Card>
    </div>
  );
}
