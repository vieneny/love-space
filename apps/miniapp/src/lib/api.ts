import { reactive } from 'vue'
import type { User, Space, Scope, Photo } from './types'

const configuredBase = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE
export const API_ORIGIN = String(configuredBase || (import.meta.env.DEV ? 'http://127.0.0.1:18100' : 'https://api.example.invalid')).replace(/\/$/, '')
export const NEEDS_API_CONFIG = API_ORIGIN.includes('example.invalid')
export const DEV_LOGIN_ENABLED = import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEV_LOGIN !== 'false'
export const state = reactive({
  token: String(uni.getStorageSync('love-space-token') || ''),
  user: null as User | null,
  space: null as Space | null,
  scope: (uni.getStorageSync('love-space-scope') === 'shared' ? 'shared' : 'personal') as Scope
})
export function rememberToken(token: string) { state.token = token; uni.setStorageSync('love-space-token', token) }
export function logout() { state.token = ''; state.user = null; state.space = null; state.scope = 'personal'; uni.removeStorageSync('love-space-token'); uni.removeStorageSync('love-space-scope'); uni.reLaunch({ url: '/pages/login/index' }) }
export function setScope(scope: Scope) { state.scope = scope; uni.setStorageSync('love-space-scope', scope) }
export function ensureAuth() { if (!state.token) { uni.reLaunch({ url: '/pages/login/index' }); return false } return true }
export function message(error: unknown) { return error instanceof Error ? error.message : '请求未完成，请稍后重试' }
export function toast(title: string) { uni.showToast({ title, icon: 'none', duration: 2400 }) }
export function errorMessage(body: unknown, status: number) {
  const detail = (body as { detail?: unknown })?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((v: { msg?: string }) => v.msg || '请检查输入').join('；')
  return status === 401 ? '登录已过期，请重新登录' : `请求未完成（${status}）`
}
export async function api<T>(path: string, method: 'GET' | 'POST' | 'PATCH' | 'DELETE' = 'GET', data?: unknown): Promise<T> {
  if (NEEDS_API_CONFIG) throw new Error('尚未连接服务，请配置正式服务地址后重新构建')
  // WeChat's native request transport does not expose PATCH. The API accepts
  // this narrowly scoped POST override before routing; H5 uses PATCH directly.
  let requestMethod: UniApp.RequestOptions['method'] = method === 'PATCH' ? 'POST' : method
  const extraHeaders: Record<string, string> = {}
  // #ifdef MP-WEIXIN
  if (method === 'PATCH') extraHeaders['X-HTTP-Method-Override'] = 'PATCH'
  // #endif
  // #ifdef H5
  requestMethod = method as UniApp.RequestOptions['method']
  // #endif
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_ORIGIN}/api/v1/app${path}`, method: requestMethod, data: data as Record<string, unknown>,
      header: { 'Content-Type': 'application/json', ...extraHeaders, ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}) }, timeout: 20000,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data as T)
        else { if (res.statusCode === 401) { state.token = ''; state.user = null; state.space = null; uni.removeStorageSync('love-space-token') }; reject(new Error(errorMessage(res.data, res.statusCode))) }
      }, fail() { reject(new Error('暂时连接不上服务，请检查网络后重试')) }
    })
  })
}
export async function refreshContext() {
  state.user = await api<User>('/me')
  state.space = await api<Space | null>('/spaces/current')
  if (!state.space && state.scope === 'shared') setScope('personal')
}
export function query(values: Record<string, string | number | undefined | null>) { const s = Object.entries(values).filter(([, v]) => v !== '' && v !== undefined && v !== null).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join('&'); return s ? `?${s}` : '' }
export function photoUrl(url: string) { return url.startsWith('http') ? url : `${API_ORIGIN}${url.startsWith('/') ? '' : '/'}${url}` }
export async function upload(path: string): Promise<Photo> {
  return new Promise((resolve, reject) => uni.uploadFile({
    url: `${API_ORIGIN}/api/v1/app/media`, filePath: path, name: 'file', header: { Authorization: `Bearer ${state.token}` }, timeout: 60000,
    success(res) { let body: unknown; try { body = JSON.parse(res.data) } catch { reject(new Error('上传未完成，服务返回格式有误')); return }; if (res.statusCode >= 200 && res.statusCode < 300) resolve(body as Photo); else reject(new Error(errorMessage(body, res.statusCode))) },
    fail() { reject(new Error('照片上传未完成，请检查网络后重试')) }
  }))
}
export function confirm(title: string, content: string): Promise<boolean> { return new Promise(resolve => uni.showModal({ title, content, confirmColor: '#24647A', success: r => resolve(r.confirm), fail: () => resolve(false) })) }
export function today() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
export function openMemory(id: string) { uni.navigateTo({ url: `/pages/memory/detail?id=${encodeURIComponent(id)}` }) }
export const kindNames = { travel: '旅行', milestone: '重要时刻', daily: '日常' }
