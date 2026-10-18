import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { validatePublicApiOrigin, isPublicAddress } from './release-config.mjs';
import { parseArgs, validateUploadEvidence } from './release-wechat.mjs';
import { validateApiBaseUrl } from './preview-wechat.mjs';

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
  ['missing explicit dev-login disable', { VITE_ENABLE_DEV_LOGIN: '' }, 1],
  ['non-boolean dev-login setting', { VITE_ENABLE_DEV_LOGIN: 'yes' }, 1],
  ['backslash URL normalization', { VITE_API_BASE_URL: 'https://api.release-check.cn\\private' }, 1],
  ['encoded hostname', { VITE_API_BASE_URL: 'https://%61pi.release-check.cn' }, 1],
  ['trailing-dot hostname', { VITE_API_BASE_URL: 'https://api.release-check.cn.' }, 1],
  ['local-only hostname', { VITE_API_BASE_URL: 'https://api.internal' }, 1],
  ['alternate example domain', { VITE_API_BASE_URL: 'https://api.example.net' }, 1],
  ['URL shell injection', { VITE_API_BASE_URL: 'https://api.release-check.cn&whoami' }, 1],
];
for (const [label, overrides, expected] of cases) {
  const result = spawnSync(process.execPath, [script], { env: { ...process.env, ...valid, ...overrides }, encoding: 'utf8' });
  assert.equal(result.status, expected, `${label}: ${result.stderr}`);
}
assert.equal(validatePublicApiOrigin('https://API.Release-check.cn:443/'), 'https://api.release-check.cn');
for (const value of ['https://127.1', 'https://0x7f000001', 'https://2130706433', 'https://0177.0.0.1', 'https://[::1]', 'https://api.release-check.cn:65536', 'https://api.release-check.cn\n', 'https://-api.release-check.cn']) {
  assert.throws(() => validatePublicApiOrigin(value));
}
for (const address of ['8.8.8.8', '1.1.1.1', '2606:4700:4700::1111']) assert.equal(isPublicAddress(address), true, address);
for (const address of ['127.0.0.1', '192.168.1.100', '10.1.2.3', '172.31.0.1', '100.64.1.1', '169.254.169.254', '192.0.2.1', '203.0.113.1', '::1', 'fe80::1', 'fd00::1', '::ffff:127.0.0.1', '2001:0db8::1', '2002:7f00:1::']) assert.equal(isPublicAddress(address), false, address);
const args = ['--api-base-url', valid.VITE_API_BASE_URL, '--version', '0.1.0', '--desc', '旅行与地图体验'];
assert.equal(parseArgs(args).upload, false);
assert.equal(parseArgs([...args, '--upload']).upload, true);
assert.equal(parseArgs([...args, '--check']).check, true);
assert.throws(() => parseArgs([...args, '--upload', '--check']));
assert.throws(() => parseArgs([...args, '--desc', 'duplicate']));
assert.throws(() => parseArgs(args.map(value => value === '旅行与地图体验' ? 'unsafe%PATH%' : value)));
assert.throws(() => parseArgs(args.map(value => value === '0.1.0' ? 'bad&version' : value)));
assert.throws(() => parseArgs(['--api-base-url', valid.VITE_API_BASE_URL]));
const info = {size: {total: 1234, packages: [{name: 'TOTAL', size: 1234}]}};
assert.equal(validateUploadEvidence(info, '\u001b[32m√ upload\u001b[0m\n'), 1234);
assert.throws(() => validateUploadEvidence(info, '✖ upload\nError: service unavailable'));
assert.throws(() => validateUploadEvidence({}, '√ upload\n'));
assert.throws(() => validateUploadEvidence({...info, errcode: 1}, '√ upload\n'));
assert.equal(validateApiBaseUrl('https://safe-tunnel.trycloudflare.com/'), 'https://safe-tunnel.trycloudflare.com');
assert.equal(validateApiBaseUrl('http://192.168.1.100:18101'), 'http://192.168.1.100:18101');
for (const value of ['http://8.8.8.8:18101', 'https://trycloudflare.com', 'https://safe.trycloudflare.com.evil.com', 'https://safe.trycloudflare.com:443', 'https://safe.trycloudflare.com/api', 'https://user:pass@safe.trycloudflare.com', 'https://safe.trycloudflare.com\n', 'http://192.168.1.100:18101\n', 'https://safe.trycloudflare.com&whoami']) assert.throws(() => validateApiBaseUrl(value));
console.log(`${cases.length} release configuration checks plus URL/DNS-address, upload arguments and false-success evidence checks passed (no network or upload).`);
