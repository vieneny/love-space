import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';

const script = path.join(import.meta.dirname, 'check-release.mjs');
const valid = { VITE_WX_APPID: 'wx0123456789abcdef', VITE_API_BASE_URL: 'https://api.release-check.cn', VITE_ENABLE_DEV_LOGIN: 'false' };
const cases = [
  ['valid configuration shape', {}, 0],
  ['missing app id', { VITE_WX_APPID: '' }, 1],
  ['old test account', { VITE_WX_APPID: 'wxcc265253aee612a7' }, 1],
  ['plain HTTP', { VITE_API_BASE_URL: 'http://api.release-check.cn' }, 1],
  ['loopback HTTPS', { VITE_API_BASE_URL: 'https://127.0.0.1' }, 1],
  ['private IP HTTPS', { VITE_API_BASE_URL: 'https://172.20.0.1' }, 1],
  ['placeholder', { VITE_API_BASE_URL: 'https://api.example.invalid' }, 1],
  ['credential-bearing URL', { VITE_API_BASE_URL: 'https://user:pass@api.release-check.cn' }, 1],
  ['API path instead of origin', { VITE_API_BASE_URL: 'https://api.release-check.cn/api/v1' }, 1],
  ['enabled dev login', { VITE_ENABLE_DEV_LOGIN: 'true' }, 1],
];
for (const [label, overrides, expected] of cases) {
  const result = spawnSync(process.execPath, [script], { env: { ...process.env, ...valid, ...overrides }, encoding: 'utf8' });
  assert.equal(result.status, expected, `${label}: ${result.stderr}`);
}
console.log(`${cases.length} release configuration checks passed (no network or upload).`);
