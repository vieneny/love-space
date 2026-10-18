import { clearSession, session } from './auth'

export const apiOrigin = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:18100').replace(/\/+$/, '')
const adminBase = `${apiOrigin}/api/v1/admin`

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

function errorDetail(value: unknown): string | undefined {
  if (!value || typeof value !== 'object' || !('detail' in value)) return
  const detail = (value as { detail: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((entry: { msg?: string }) => entry?.msg || '输入格式不正确').join('；')
  }
}

export async function request<T>(path: string, init: RequestInit = {}, authenticated = true): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (authenticated && session.token) headers.set('Authorization', `Bearer ${session.token}`)
  let response: Response
  try {
    response = await fetch(`${adminBase}${path}`, { ...init, headers, signal: init.signal || AbortSignal.timeout(20000) })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError('连接服务失败，请检查网络或稍后重试。', 0)
  }
  const body: unknown = response.status === 204 ? undefined : await response.json().catch(() => undefined)
  if (!response.ok) {
    if (response.status === 401 && authenticated) {
      clearSession()
      window.dispatchEvent(new Event('admin-session-expired'))
      throw new ApiError('登录已过期，请重新登录。', 401)
    }
    const fallback = response.status === 403 ? '当前账号没有此操作权限。' : `请求失败（${response.status}），请稍后重试。`
    throw new ApiError(errorDetail(body) || fallback, response.status)
  }
  return body as T
}

export interface ListResult<T> { items: T[]; total: number }
export type MetadataRow = Record<string, unknown>
export interface Overview {
  users: number
  spaces: number
  memories: number
  trips: number
  media_count: number
  storage_bytes: number
  wishes: number
  habits: number
}
export interface Question { id: string; text: string; active: boolean }

export const adminApi = {
  login: (username: string, password: string) => request<{ access_token: string; token_type: string }>('/auth/login', {
    method: 'POST', body: JSON.stringify({ username, password }),
  }, false),
  overview: () => request<Overview>('/overview'),
  list: (resource: string) => request<ListResult<MetadataRow>>(`/${resource}`),
  questions: () => request<ListResult<Question>>('/questions'),
  createQuestion: (text: string, active: boolean) => request<Question>('/questions', { method: 'POST', body: JSON.stringify({ text, active }) }),
  updateQuestion: (id: string, values: { text?: string; active?: boolean }) => request<Question>(`/questions/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(values) }),
  settings: () => request<MetadataRow>('/settings'),
}
