import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, openSync, closeSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const cliPath = 'C:\\Program Files (x86)\\Tencent\\微信web开发者工具\\cli.bat'
const help = `微信同 WiFi 开发预览（不会上传正式体验版）

用法：
  pnpm preview:wechat --api-base-url http://192.168.1.100:18101
  pnpm preview:wechat --api-base-url http://192.168.1.100:18101 --check

参数：
  --api-base-url  必填，仅允许 RFC1918 私网 IPv4 的 HTTP 源地址
  --check         仅校验参数与本地工具路径，不构建、不调用微信 CLI
  --help          显示说明

AppID 由小程序已有的 ignored 环境配置读取；开发身份登录强制关闭。
输出：artifacts/wechat-phone-preview.png 和 wechat-phone-preview-info.json
`

export function validateApiBaseUrl(value) {
  // Validate the original spelling before URL parsing: URL normalizes octal,
  // shortened IPs and escaped input that must never reach a Windows shell.
  const match = typeof value === 'string' && value.match(/^http:\/\/((?:0|[1-9]\d{0,2})(?:\.(?:0|[1-9]\d{0,2})){3})(?::([1-9]\d{0,4}))?\/?$/)
  if (!match) throw new Error('--api-base-url 必须是 http://私网IPv4:端口，不带账号、路径、查询参数或片段。')
  const octets = match[1].split('.').map(Number)
  const privateAddress = octets[0] === 10 || (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31) || (octets[0] === 192 && octets[1] === 168)
  if (octets.some(part => part > 255) || !privateAddress || (match[2] && Number(match[2]) > 65535)) {
    throw new Error('--api-base-url 仅允许 10/8、172.16/12、192.168/16 私网 IPv4 及有效端口。')
  }
  return `http://${match[1]}${match[2] ? `:${match[2]}` : ''}`
}

export function parseArgs(args) {
  const options = { help: false, check: false, apiBaseUrl: undefined }
  for (let i = 0; i < args.length; i++) {
    const arg = args[i]
    if (i === 0 && arg === '--') continue
    if (arg === '--help' || arg === '-h') options.help = true
    else if (arg === '--check') options.check = true
    else if (arg === '--api-base-url' || arg.startsWith('--api-base-url=')) {
      if (options.apiBaseUrl !== undefined) throw new Error('--api-base-url 只能指定一次。')
      options.apiBaseUrl = arg === '--api-base-url' ? args[++i] : arg.slice('--api-base-url='.length)
      if (!options.apiBaseUrl) throw new Error('--api-base-url 后缺少地址。')
    } else throw new Error('参数不受支持，请运行 pnpm preview:wechat --help。')
  }
  if (!options.help) options.apiBaseUrl = validateApiBaseUrl(options.apiBaseUrl)
  return options
}

export function quoteWindowsArgument(value) {
  // .bat files require cmd.exe. Quote every argument and reject characters
  // that cmd can expand or interpret even in a quoted batch invocation.
  if (/[&|<>^%!"\r\n\0]/.test(value)) throw new Error('命令路径包含不支持的 Windows shell 字符。')
  return `"${value}"`
}

function run(command, args, env) {
  return new Promise((resolveRun, reject) => {
    const commandLine = `"${[command, ...args].map(quoteWindowsArgument).join(' ')}"`
    const child = spawn(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', commandLine], {
      cwd: root, env, stdio: 'inherit', windowsVerbatimArguments: true,
    })
    child.once('error', reject)
    child.once('exit', (code, signal) => {
      if (code === 0) resolveRun()
      else reject(new Error(`子命令未完成（${signal || `exit ${code ?? 'unknown'}`}）。`))
    })
  })
}

function verifyFreshPng(file, startedAt) {
  if (!existsSync(file)) throw new Error('微信 CLI 未生成本次二维码；即使退出码为 0 也不能视为预览成功，请检查上方 CLI 错误。')
  const stat = statSync(file)
  const bytes = readFileSync(file)
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])
  if (!stat.isFile() || stat.mtimeMs < startedAt - 2000 || bytes.length < 45 || !bytes.subarray(0, 8).equals(signature)
      || bytes.toString('ascii', 12, 16) !== 'IHDR' || bytes.readUInt32BE(16) === 0 || bytes.readUInt32BE(20) === 0
      || bytes.toString('ascii', bytes.length - 8, bytes.length - 4) !== 'IEND') {
    throw new Error('本次二维码文件不是有效的新 PNG，不能视为预览成功。')
  }
}

export async function main(args = process.argv.slice(2)) {
  const options = parseArgs(args)
  if (options.help) { console.log(help); return }
  if (process.platform !== 'win32') throw new Error('此命令使用 Windows 微信开发者工具，请在 Windows 中运行。')
  if (!existsSync(cliPath)) throw new Error('未找到微信开发者工具 cli.bat，请安装到文档所列路径。')
  const project = resolve(root, 'apps/miniapp/dist/build/mp-weixin')
  const qr = resolve(root, 'artifacts/wechat-phone-preview.png')
  const info = resolve(root, 'artifacts/wechat-phone-preview-info.json')
  for (const value of [root, cliPath, project, qr, info]) quoteWindowsArgument(value)
  if (options.check) { console.log(`参数校验通过：${options.apiBaseUrl}；未构建、未调用微信 CLI。`); return }

  mkdirSync(dirname(qr), { recursive: true })
  const lock = resolve(root, 'artifacts/wechat-phone-preview.lock')
  let lockFd
  try { lockFd = openSync(lock, 'wx') } catch (error) {
    if (error.code === 'EEXIST') throw new Error('已有开发预览命令运行；若上次被强制中断，请先确认进程已停止，再删除 artifacts/wechat-phone-preview.lock。')
    throw error
  }
  try {
    // Remove previous results before any work so a failed run cannot reuse them.
    rmSync(qr, { force: true })
    rmSync(info, { force: true })
    const env = { ...process.env, VITE_API_BASE_URL: options.apiBaseUrl, VITE_API_BASE: options.apiBaseUrl, VITE_ENABLE_DEV_LOGIN: 'false' }
    console.log(`构建同 WiFi 开发预览：${options.apiBaseUrl}（开发身份登录关闭）`)
    await run('pnpm', ['--dir', 'apps/miniapp', 'run', 'build:mp-weixin:preview', '--mode', 'development'], env)
    const configFile = resolve(project, 'project.config.json')
    if (!existsSync(configFile)) throw new Error('构建未生成 project.config.json。')
    const config = JSON.parse(readFileSync(configFile, 'utf8'))
    if (!/^wx[0-9a-f]{16}$/i.test(config.appid || '')) throw new Error('预览需要正式 AppID，请在小程序 ignored 环境文件中配置 VITE_WX_APPID。')
    config.setting = { ...config.setting, urlCheck: false }
    writeFileSync(configFile, JSON.stringify(config, null, 2) + '\n')

    const startedAt = Date.now()
    await run(cliPath, ['preview', '--project', project, '--qr-format', 'image', '--qr-output', qr, '--info-output', info], env)
    verifyFreshPng(qr, startedAt)
    console.log(`本次开发预览二维码已生成：${qr}`)
    console.log('手机与电脑连接同一 WiFi；扫码后在小程序开发调试中关闭域名校验，并保持局域网后端运行。')
    console.log('这是开发预览，不是正式体验版。二维码成功不代表手机登录、请求或地图已验证。')
  } finally {
    closeSync(lockFd)
    rmSync(lock, { force: true })
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(error => { console.error(`开发预览失败：${error.message}`); process.exitCode = 1 })
}
