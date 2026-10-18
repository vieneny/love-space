import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '..');
const files = ['apps/miniapp/.env.production.local', 'apps/miniapp/.env.production'];
const config = {};
for (const file of files.reverse()) {
  if (!fs.existsSync(path.join(root,file))) continue;
  for (const line of fs.readFileSync(path.join(root,file),'utf8').split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z_]+)\s*=\s*["']?(.*?)["']?\s*$/);
    if (match) config[match[1]] = match[2];
  }
}
Object.assign(config, process.env);
const errors = [];
if (!/^wx[0-9a-f]{16}$/i.test(config.VITE_WX_APPID || '')) errors.push('缺少正式 VITE_WX_APPID；请完成微信小程序注册并提供 AppID。');
if (config.VITE_WX_APPID === 'wxcc265253aee612a7') errors.push('旧项目测试号不能作为此项目正式 AppID。');
try {
  const endpoint = new URL(config.VITE_API_BASE_URL || '');
  if (endpoint.protocol !== 'https:' || endpoint.username || endpoint.password || endpoint.search || endpoint.hash || !['', '/'].includes(endpoint.pathname)) throw new Error();
  const host = endpoint.hostname.toLowerCase();
  // WeChat server domains cannot be IPs, localhost, or local-only host names.
  if (host === 'localhost' || host.endsWith('.localhost') || host.endsWith('.local') || !host.includes('.') || /^[\d.]+$/.test(host) || host.includes(':') || host.endsWith('.invalid') || host === 'example.com' || host.endsWith('.example.com')) {
    errors.push('正式体验包必须使用实际公网域名，不能指向 IP、本机、局域网或示例地址。');
  }
} catch {
  errors.push('VITE_API_BASE_URL 必须是手机可访问的 HTTPS 源地址，不带路径、账号或查询参数。');
}
if (/^(true|1)$/i.test(config.VITE_ENABLE_DEV_LOGIN || '')) errors.push('正式构建不能开启开发身份登录。');
if (errors.length) {
  console.error('尚不能上传正式体验版：\n' + errors.map(x => `- ${x}`).join('\n'));
  process.exitCode = 1;
} else {
  console.log('上传配置预检通过；仍需核验微信授权、真实登录、域名及 HTTPS、隐私声明和真机地图。');
}
