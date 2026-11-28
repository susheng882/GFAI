/* GFLC proto 前端 · API 适配层（58 号 Plan 批3）

   策略：USE_REAL_API 开关（localStorage 'gflc_use_real_api' === '1' 时走真实后端）。
   默认 false → 返回 mock（保持视觉稳定）；连调验收时打开。
   每个 api 调用失败时**自动降级回 mock**，保证页面永不白屏。 */

const BASE = '/api';

/* 判断是否启用真实接口 */
export function useRealApi() {
  try {
    return window.localStorage.getItem('gflc_use_real_api') === '1';
  } catch {
    return false;
  }
}

export function setRealApi(on) {
  try {
    window.localStorage.setItem('gflc_use_real_api', on ? '1' : '0');
  } catch { /* noop */ }
}

/* 通用 GET：真实失败返回 null（调用方降级 mock） */
export async function apiGet(path) {
  if (!useRealApi()) return null;
  try {
    const r = await fetch(BASE + path, { credentials: 'include' });
    if (!r.ok) return null;
    const j = await r.json();
    return j && j.ok ? j.data : null;
  } catch {
    return null;
  }
}

/* 通用 POST：真实失败返回 null */
export async function apiPost(path, body) {
  if (!useRealApi()) return null;
  try {
    const r = await fetch(BASE + path, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    if (!r.ok) return null;
    const j = await r.json();
    return j && j.ok ? j.data : null;
  } catch {
    return null;
  }
}
