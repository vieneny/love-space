import { spawnSync } from 'node:child_process'
import { chmodSync, existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function git(args, allowedStatus = [0]) {
  const result = spawnSync('git', args, { cwd: root, encoding: 'utf8' })
  if (result.error || !allowedStatus.includes(result.status)) throw new Error('无法读取或更新当前仓库的本地 Git hook 配置。')
  return result.stdout.trim()
}

export function main() {
  if (resolve(git(['rev-parse', '--show-toplevel'])) !== root) throw new Error('此脚本必须位于当前仓库的 scripts 目录。')
  const hook = resolve(root, '.githooks/commit-msg')
  if (!existsSync(hook)) throw new Error('缺少 .githooks/commit-msg，未修改 Git 配置。')
  const existing = git(['config', '--get', 'core.hooksPath'], [0, 1])
  if (existing && existing !== '.githooks') throw new Error('检测到其他 Git hook 路径，未覆盖；请先合并现有检查。')
  if (process.platform !== 'win32') chmodSync(hook, 0o755)
  git(['config', '--local', 'core.hooksPath', '.githooks'])
  console.log('已启用中文提交检查；core.hooksPath 仅设置于当前仓库，未修改全局配置。')
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try { main() } catch (error) {
    console.error(error instanceof Error ? error.message : '本地 Git hook 配置未完成。')
    process.exitCode = 1
  }
}
