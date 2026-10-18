import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const format = /^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert|security)(?:\([^()\s:]+\))?: (\S(?:.*\S)?)$/u

export function validateCommitMessage(message) {
  const subject = String(message).replace(/^\uFEFF/, '').split(/\r?\n/)
    .find(line => line.trim() && !line.trimStart().startsWith('#'))?.trim() || ''
  const match = subject.match(format)
  if (!match) return { ok: false, error: '提交主题须采用 type(scope)?: 中文主题，例如 feat(小程序): 添加旅行筛选。' }
  if (!/\p{Script=Han}/u.test(match[2])) return { ok: false, error: '提交主题必须包含中文，可以保留 API 等技术名称。' }
  return { ok: true }
}

export function main(args = process.argv.slice(2)) {
  if (args.length !== 1) throw new Error('用法：node scripts/check-commit-message.mjs <提交信息文件>')
  const result = validateCommitMessage(readFileSync(args[0], 'utf8'))
  if (!result.ok) throw new Error(result.error)
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try { main() } catch (error) {
    console.error(error instanceof Error ? error.message : '提交信息检查未完成。')
    process.exitCode = 1
  }
}
