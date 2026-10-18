export function display(value: unknown): string {
  if (value === undefined || value === null || value === '') return '—'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'number') return Number.isFinite(value) ? value.toLocaleString('zh-CN') : '—'
  if (typeof value === 'object') return '—'
  return String(value)
}

export function formatTime(value: unknown): string {
  if (!value || typeof value !== 'string') return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date)
}

export function formatBytes(value: unknown): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
  if (value < 1024) return `${value} B`
  const unit = Math.min(Math.floor(Math.log(value) / Math.log(1024)), 4)
  return `${(value / 1024 ** unit).toFixed(unit === 1 ? 0 : 1)} ${['B', 'KB', 'MB', 'GB', 'TB'][unit]}`
}
