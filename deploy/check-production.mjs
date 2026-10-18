import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const required = ['PUBLIC_DOMAIN', 'POSTGRES_PASSWORD', 'JWT_SECRET', 'ADMIN_PASSWORD', 'WECHAT_APPID', 'WECHAT_SECRET'];
const placeholder = /replace[-_ ]?with|change[-_ ]?me|your[-_ ]|placeholder|todo|<[^>]*>/i;

export function parseEnv(source) {
  const values = {};
  const errors = [];
  for (const [index, raw] of source.replace(/^\uFEFF/, '').split(/\r?\n/).entries()) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const match = line.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!match) {
      errors.push(`环境文件第 ${index + 1} 行不是单行 KEY=value 配置。`);
      continue;
    }
    const [, key, literal] = match;
    let value;
    if (literal.startsWith('"') || literal.startsWith("'")) {
      const quote = literal[0];
      const quoted = literal.match(quote === '"' ? /^"([^"\\]*)"\s*(?:#.*)?$/ : /^'([^']*)'\s*(?:#.*)?$/);
      if (!quoted) {
        errors.push(`环境文件第 ${index + 1} 行需使用无转义的单行字面值。`);
        continue;
      }
      value = quoted[1];
    } else {
      value = literal.replace(/\s+#.*$/, '').trim();
    }
    if (Object.hasOwn(values, key)) errors.push(`环境文件中的 ${key} 重复定义。`);
    values[key] = value;
  }
  return { values, errors };
}

export function validateProductionValues(values) {
  const errors = [];
  for (const key of required) {
    const value = values[key] || '';
    if (!value || placeholder.test(value)) errors.push(`${key} 缺失或仍是占位值。`);
    if (/[\r\n$]/.test(value)) errors.push(`${key} 必须使用不含换行或 $ 插值的字面值。`);
  }
  const domain = values.PUBLIC_DOMAIN || '';
  const labels = domain.split('.');
  if (domain.length > 253 || labels.length < 2 || labels.some(label => !/^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/.test(label)) ||
      !/^[A-Za-z]{2,63}$/.test(labels.at(-1) || '') ||
      /(?:^|\.)(?:localhost|local|invalid|example|test)$|(?:^|\.)example\.(?:com|net|org)$/i.test(domain)) {
    errors.push('PUBLIC_DOMAIN 必须是实际公网域名，不含协议、端口、路径、IP 或示例后缀。');
  }
  if (!/^[A-Za-z0-9_-]{24,}$/.test(values.POSTGRES_PASSWORD || '')) errors.push('POSTGRES_PASSWORD 需至少 24 位 URL-safe 字符，避免数据库连接串转义问题。');
  if (Buffer.byteLength(values.JWT_SECRET || '', 'utf8') < 32) errors.push('JWT_SECRET 需至少 32 字节。');
  if ((values.ADMIN_PASSWORD || '').length < 12) errors.push('ADMIN_PASSWORD 需至少 12 个字符。');
  if (values.ADMIN_USERNAME !== undefined && !/^[A-Za-z0-9_-]{3,64}$/.test(values.ADMIN_USERNAME)) errors.push('ADMIN_USERNAME 需为 3 至 64 位字母、数字、下划线或短横线。');
  const appid = values.WECHAT_APPID || '';
  if (!/^wx[0-9a-f]{16}$/i.test(appid) || ['wxcc265253aee612a7', 'wx0123456789abcdef', 'wx0000000000000000'].includes(appid.toLowerCase())) errors.push('WECHAT_APPID 需为本小程序正式 AppID，不可使用已知演示值。');
  if (!/^[0-9a-f]{32}$/i.test(values.WECHAT_SECRET || '')) errors.push('WECHAT_SECRET 应是微信平台提供的 32 位十六进制 AppSecret。');
  const secrets = ['POSTGRES_PASSWORD', 'JWT_SECRET', 'ADMIN_PASSWORD', 'WECHAT_SECRET'].map(key => values[key]).filter(Boolean);
  if (secrets.some(value => /^(.)\1{7,}$/u.test(value) || /^(?:test|example|demo|sample|dummy)[-_]/i.test(value))) errors.push('密钥或密码仍是明显测试值，请使用独立生成的随机值。');
  if (new Set(secrets).size !== secrets.length) errors.push('数据库、JWT、后台密码及微信 AppSecret 不可复用同一个值。');
  return errors;
}

export function checkAdminBuild(projectRoot, domain) {
  const dist = path.join(projectRoot, 'apps/admin/dist');
  const assets = path.join(dist, 'assets');
  if (!fs.existsSync(path.join(dist, 'index.html')) || !fs.existsSync(assets)) return ['缺少管理后台构建产物；先设置生产 API 域名并运行 pnpm build:admin。'];
  const bundles = fs.readdirSync(assets).filter(name => name.endsWith('.js')).map(name => fs.readFileSync(path.join(assets, name), 'utf8'));
  const errors = [];
  if (!bundles.some(text => text.includes(`https://${domain}`))) errors.push('管理后台构建产物未包含配置的 HTTPS API 域名，请重新构建。');
  if (bundles.some(text => /https?:\/\/(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?=[:/"'`\s]|$)/i.test(text))) errors.push('管理后台构建产物仍包含本机 API 地址，请检查生产构建。');
  return errors;
}

export function main(args = process.argv.slice(2)) {
  let envFile = path.join(root, 'deploy/.env');
  let configOnly = false;
  for (let index = 0; index < args.length; index++) {
    if (args[index] === '--env-file' && args[index + 1]) envFile = path.resolve(args[++index]);
    else if (args[index] === '--config-only') configOnly = true;
    else if (args[index] === '--help') {
      console.log('node deploy/check-production.mjs [--env-file deploy/.env] [--config-only]\n仅本地检查配置和管理后台产物，不联网、不启动服务，不输出配置值。');
      return 0;
    } else {
      console.error('未知或不完整参数；使用 --help 查看用法。');
      return 1;
    }
  }
  let source;
  try { source = fs.readFileSync(envFile, 'utf8'); }
  catch { console.error('无法读取生产环境文件；请由部署者准备 deploy/.env，不要提交该文件。'); return 1; }
  const parsed = parseEnv(source);
  const values = { ...parsed.values };
  const overrides = [...required, 'ADMIN_USERNAME'].filter(key => process.env[key] !== undefined);
  for (const key of overrides) values[key] = process.env[key];
  const errors = [...parsed.errors, ...validateProductionValues(values)];
  if (errors.length === 0 && !configOnly) errors.push(...checkAdminBuild(root, values.PUBLIC_DOMAIN));
  if (errors.length) {
    console.error('生产静态检查未通过：\n' + [...new Set(errors)].map(error => `- ${error}`).join('\n'));
    return 1;
  }
  if (overrides.length) console.log('已按 Docker Compose 规则使用当前 shell 的同名变量覆盖环境文件；未显示配置值。');
  console.log(`${configOnly ? '生产配置格式' : '生产配置与管理后台产物'}静态检查通过。尚未验证 DNS、备案、TLS、微信域名授权、服务器容量或备份恢复。`);
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) process.exitCode = main();
