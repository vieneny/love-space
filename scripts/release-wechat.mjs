import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'
import { createHash } from 'node:crypto'
import { lookup } from 'node:dns/promises'
import { existsSync, readFileSync, writeFileSync, readdirSync, statSync, mkdirSync, openSync, closeSync, rmSync } from 'node:fs'
import { dirname, resolve, relative } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { quoteWindowsArgument } from './preview-wechat.mjs'
import { validatePublicApiOrigin, validateReleaseConfig, isPublicAddress } from './release-config.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const miniapp = resolve(root, 'apps/miniapp')
const directory = resolve(root, 'artifacts/wechat-release')
const project = resolve(directory, 'mp-weixin')
const cliPath = 'C:\\Program Files (x86)\\Tencent\\微信web开发者工具\\cli.bat'
const usage = `微信正式构建与代码上传

准备产物（不会上传）：
  pnpm prepare:wechat --api-base-url https://api.your-domain.tld --version 0.1.0 --desc "首版体验"
上传代码（不等同于设为平台体验版）：
  pnpm upload:wechat --api-base-url https://api.your-domain.tld --version 0.1.0 --desc "首版体验"
仅做离线参数与配置校验：在 prepare:wechat 命令末尾加 --check

请将示例域名替换为已部署的真实 HTTPS 后端。AppID 从已有 ignored 环境配置读取。
默认检查 DNS、GET /health 和未登录 GET /api/v1/app/me，然后 production 构建到 artifacts/wechat-release/mp-weixin。
--upload 才调用官方 CLI 上传；--check 不联网、不构建、不上传。
上传后仍需微信后台核对版本、设为体验版、添加体验成员；不能保证任意微信用户都能扫码。
`

export function parseArgs(args) {
  const result = { help: false, check: false, upload: false }
  const values = new Map([['--api-base-url', 'apiBaseUrl'], ['--version', 'version'], ['--desc', 'desc']])
  for (let i = 0; i < args.length; i++) {
    const arg = args[i]
    if (i === 0 && arg === '--') continue
    if (arg === '--help' || arg === '-h') result.help = true
    else if (arg === '--check') result.check = true
    else if (arg === '--upload') result.upload = true
    else {
      const equal = arg.indexOf('=')
      const name = equal < 0 ? arg : arg.slice(0, equal)
      const key = values.get(name)
      if (!key) throw new Error('参数不受支持，请运行 pnpm prepare:wechat --help。')
      if (Object.hasOwn(result, key)) throw new Error(`${name} 只能指定一次。`)
      result[key] = equal < 0 ? args[++i] : arg.slice(equal + 1)
      if (!result[key]) throw new Error(`${name} 缺少值。`)
    }
  }
  if (result.help) return result
  result.apiBaseUrl = validatePublicApiOrigin(result.apiBaseUrl)
  if (!/^[0-9a-z][0-9a-z._-]{0,31}$/i.test(result.version || '')) throw new Error('--version 必须是1至32位字母、数字、点、下划线或短横线。')
  if (typeof result.desc !== 'string' || !result.desc.trim() || result.desc.length > 200) throw new Error('--desc 需要1至200字的版本说明。')
  result.desc = result.desc.trim()
  quoteWindowsArgument(result.desc)
  if (result.upload && result.check) throw new Error('--check 与 --upload 不能同时使用；离线校验不会执行上传。')
  return result
}

function run(command, args, env, capture = false) {
  return new Promise((resolveRun, reject) => {
    const batch = process.platform === 'win32' && (command === 'pnpm' || /\.(?:bat|cmd)$/i.test(command))
    const executable = batch ? process.env.ComSpec || 'cmd.exe' : command
    const parameters = batch ? ['/d', '/s', '/c', `"${[command, ...args].map(quoteWindowsArgument).join(' ')}"`] : args
    const child = spawn(executable, parameters, { cwd: root, env, stdio: capture ? ['ignore', 'pipe', 'pipe'] : 'inherit', windowsVerbatimArguments: batch })
    let stdout = '', stderr = ''
    if (capture) {
      child.stdout.on('data', chunk => { stdout += chunk; process.stdout.write(chunk) })
      child.stderr.on('data', chunk => { stderr += chunk; process.stderr.write(chunk) })
    }
    child.once('error', reject)
    child.once('exit', (code, signal) => code === 0 ? resolveRun(stdout + '\n' + stderr) : reject(new Error(`命令失败（${signal || `exit ${code ?? 'unknown'}`}），请检查上方输出。`)))
  })
}

export async function verifyApi(origin) {
  const addresses = await lookup(new URL(origin).hostname, { all: true, verbatim: true })
  if (!addresses.length || addresses.some(item => !isPublicAddress(item.address))) throw new Error('API 域名未全部解析到公网地址，不能用于可分享的正式包。')
  const health = await fetch(`${origin}/health`, { redirect: 'error', signal: AbortSignal.timeout(10000) })
  if (!health.ok || (await health.json()).status !== 'ok') throw new Error('公网 API 健康检查未通过。')
  const unauthenticated = await fetch(`${origin}/api/v1/app/me`, { redirect: 'error', signal: AbortSignal.timeout(10000) })
  if (unauthenticated.status !== 401) throw new Error('公网 API 的未登录访问检查未返回401，请核对部署地址和认证配置。')
  console.log('公网 DNS、HTTPS 健康检查及未登录401已通过；真实微信登录、数据持久化、图片和权限仍需单独验收。')
}

export function validateUploadEvidence(info, output) {
  const plain = output.replace(/\u001b\[[0-?]*[ -/]*[@-~]/g, '').replace(/\r/g, '\n')
  if (!/^[ \t]*[√✔✓]\s+upload(?:\s+success)?[ \t]*$/m.test(plain)) throw new Error('CLI 未返回明确的 upload 成功标记，不能确认代码已上传。')
  if (!info || !Number.isSafeInteger(info.size?.total) || info.size.total <= 0 || !Array.isArray(info.size.packages) || !info.size.packages.length
      || (info.errcode !== undefined && info.errcode !== 0)) throw new Error('本次上传结果文件缺少有效包体信息，不能确认上传成功。')
  return info.size.total
}

function buildDigest(base) {
  const hash = createHash('sha256')
  function visit(folder) {
    for (const entry of readdirSync(folder, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const file = resolve(folder, entry.name)
      if (entry.isDirectory()) visit(file)
      else if (entry.isFile()) { hash.update(relative(base, file).replaceAll('\\', '/') + '\0'); hash.update(readFileSync(file)); hash.update('\0') }
    }
  }
  visit(base)
  return hash.digest('hex')
}

export async function main(args = process.argv.slice(2)) {
  const options = parseArgs(args)
  if (options.help) { console.log(usage); return }
  if (options.upload && (process.platform !== 'win32' || !existsSync(cliPath))) throw new Error('代码上传需要 Windows 官方微信开发者工具 cli.bat；安装位置见小程序 README。')
  const require = createRequire(resolve(miniapp, 'package.json'))
  const { loadEnv } = await import(pathToFileURL(resolve(dirname(require.resolve('vite/package.json')), 'dist/node/index.js')).href)
  const env = { ...loadEnv('production', miniapp, 'VITE_'), ...process.env, NODE_ENV: 'production',
    VITE_API_BASE_URL: options.apiBaseUrl, VITE_API_BASE: options.apiBaseUrl, VITE_ENABLE_DEV_LOGIN: 'false', UNI_OUTPUT_DIR: project }
  const errors = validateReleaseConfig(env)
  if (errors.length) throw new Error(errors.join('\n'))
  for (const value of [root, project, directory, cliPath]) quoteWindowsArgument(value)
  if (options.check) { console.log('正式参数与AppID配置校验通过；未联网、未构建、未上传。'); return }

  mkdirSync(directory, { recursive: true })
  const lock = resolve(directory, 'release.lock')
  let fd
  try { fd = openSync(lock, 'wx') } catch (error) {
    if (error.code === 'EEXIST') throw new Error('已有正式构建或上传运行；确认旧进程停止后才可删除 artifacts/wechat-release/release.lock。')
    throw error
  }
  try {
    await verifyApi(options.apiBaseUrl)
    if (options.upload) {
      const login = await run(cliPath, ['islogin'], env, true)
      if (!/"login"\s*:\s*true/.test(login)) throw new Error('官方微信开发者工具未确认登录，请先在工具中登录有权限的开发者账号。')
    }
    const receiptFile = resolve(directory, 'upload-receipt.json')
    const infoFile = resolve(directory, 'upload-info.json')
    rmSync(receiptFile, { force: true })
    rmSync(infoFile, { force: true })
    for (const file of ['project.config.json', 'app.js', 'app.json']) rmSync(resolve(project, file), { force: true })
    await run(process.execPath, [resolve(miniapp, 'scripts/uni.mjs'), 'build', '-p', 'mp-weixin', '--mode', 'production'], env)
    const config = JSON.parse(readFileSync(resolve(project, 'project.config.json'), 'utf8'))
    if (config.appid !== env.VITE_WX_APPID || config.setting?.urlCheck !== true || !existsSync(resolve(project, 'app.js')) || !existsSync(resolve(project, 'app.json'))) {
      throw new Error('正式构建产物缺失，或 AppID／域名校验配置不一致。')
    }
    const manifest = { created_at: new Date().toISOString(), version: options.version, description: options.desc,
      api_origin: options.apiBaseUrl, appid: config.appid, build_sha256: buildDigest(project), uploaded: false }
    writeFileSync(resolve(directory, 'build-manifest.json'), JSON.stringify(manifest, null, 2) + '\n')
    if (!options.upload) {
      console.log('正式构建已准备：artifacts/wechat-release/mp-weixin；尚未上传。现有同 WiFi 预览产物未覆盖。')
      return
    }
    const startedAt = Date.now()
    const output = await run(cliPath, ['upload', '--project', project, '--version', options.version, '--desc', options.desc, '--info-output', infoFile], env, true)
    if (!existsSync(infoFile) || statSync(infoFile).mtimeMs < startedAt - 2000) throw new Error('官方 CLI 没有生成本次上传信息，不能确认上传成功。')
    const size = validateUploadEvidence(JSON.parse(readFileSync(infoFile, 'utf8')), output)
    writeFileSync(receiptFile, JSON.stringify({ ...manifest, uploaded: true, uploaded_at: new Date().toISOString(), size_bytes: size, evidence: 'official CLI success marker and fresh upload-info.json' }, null, 2) + '\n')
    console.log('官方 CLI 已确认代码上传；结果已保存到 artifacts/wechat-release/upload-receipt.json。')
    console.log('下一步：微信后台核对开发版本，设为体验版并添加体验成员。尚未替你设置体验版或验证他人手机可用。')
  } finally { closeSync(fd); rmSync(lock, { force: true }) }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(error => { console.error(`正式微信流程未完成：${error.message}`); process.exitCode = 1 })
}
