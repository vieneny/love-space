import fs from 'node:fs';
import path from 'node:path';
import { validateReleaseConfig } from './release-config.mjs';
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
const errors = validateReleaseConfig(config);
if (errors.length) {
  console.error('尚不能上传正式体验版：\n' + errors.map(x => `- ${x}`).join('\n'));
  process.exitCode = 1;
} else {
  console.log('上传配置预检通过；仍需核验微信授权、真实登录、域名及 HTTPS、隐私声明和真机地图。');
}
