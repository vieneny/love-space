import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const cwd = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(import.meta.url)
const entry = require.resolve('@dcloudio/vite-plugin-uni/bin/uni.js')
const rawArgs = process.argv.slice(2)
const localPreview = rawArgs.includes('--local-preview')
const args = rawArgs.filter(arg => arg !== '--local-preview')
const { loadEnv } = await import('vite')
const env = { ...loadEnv(args.includes('build') ? 'production' : 'development', cwd, ''), ...process.env }
const appid = env.VITE_WX_APPID || ''
if (appid && !/^wx[0-9a-f]{16}$/i.test(appid)) throw new Error('VITE_WX_APPID must be a formal wx + 16 hexadecimal characters AppID.')
const isWechat = args.includes('mp-weixin')
if (isWechat && args.includes('build') && !localPreview) {
  Object.assign(process.env, env)
  await import(pathToFileURL(resolve(cwd, '../../scripts/check-release.mjs')).href)
  if (process.exitCode) process.exit(process.exitCode)
}
function configure() {
  if (!isWechat) return
  const outputDirectory = env.UNI_OUTPUT_DIR || resolve(cwd, 'dist', args.includes('build') ? 'build' : 'dev', 'mp-weixin')
  const output = resolve(outputDirectory, 'project.config.json')
  if (!existsSync(output)) return
  const value = JSON.parse(readFileSync(output, 'utf8'))
  value.appid = appid
  value.projectname = '共赴山海手记'
  value.setting = { ...value.setting, urlCheck: true }
  writeFileSync(output, JSON.stringify(value, null, 2))
}
const child = spawn(process.execPath, [entry, ...args], { cwd, stdio: 'inherit', env })
// Development compiler is long-running. Keep its generated project AppID in sync.
const timer = isWechat && !args.includes('build') ? setInterval(configure, 2000) : null
child.on('exit', code => { if (timer) clearInterval(timer); configure(); process.exit(code ?? 1) })
child.on('error', error => { if (timer) clearInterval(timer); console.error(error); process.exit(1) })
process.on('SIGINT', () => child.kill('SIGINT'))
