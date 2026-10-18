import { isIP } from 'node:net'

export function validatePublicApiOrigin(value) {
  // Check the original spelling: URL() otherwise accepts backslashes,
  // shortened/octal IPs and escaped hostnames by normalizing them.
  if (typeof value !== 'string' || /[\s\\]/.test(value) || !/^https:\/\/[a-z0-9.-]+(?::[1-9]\d{0,4})?\/?$/i.test(value)) {
    throw new Error('VITE_API_BASE_URL 必须是公网 HTTPS 源地址，不带账号、路径、查询参数或片段。')
  }
  let endpoint
  try { endpoint = new URL(value) } catch { throw new Error('VITE_API_BASE_URL 不是有效的 HTTPS 源地址。') }
  const host = endpoint.hostname.toLowerCase()
  const labels = host.split('.')
  const invalidLabel = labels.some(label => !/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label))
  const reserved = ['localhost', 'local', 'internal', 'lan', 'test', 'invalid', 'example', 'onion', 'home.arpa', 'example.com', 'example.net', 'example.org']
  if (endpoint.protocol !== 'https:' || isIP(host) || /^[\d.]+$/.test(host) || labels.length < 2 || host.length > 253 || invalidLabel
      || reserved.some(name => host === name || host.endsWith(`.${name}`))) {
    throw new Error('正式体验包必须使用实际公网域名，不能指向 IP、本机、局域网或示例地址。')
  }
  return endpoint.origin
}

export function validateReleaseConfig(config) {
  const errors = []
  if (!/^wx[0-9a-f]{16}$/i.test(config.VITE_WX_APPID || '')) errors.push('缺少正式 VITE_WX_APPID；请完成微信小程序注册并提供 AppID。')
  if (config.VITE_WX_APPID === 'wxcc265253aee612a7') errors.push('旧项目测试号不能作为此项目正式 AppID。')
  try { validatePublicApiOrigin(config.VITE_API_BASE_URL) } catch (error) { errors.push(error.message) }
  if (config.VITE_ENABLE_DEV_LOGIN !== 'false') errors.push('正式构建必须显式设置 VITE_ENABLE_DEV_LOGIN=false。')
  return errors
}

export function isPublicAddress(address) {
  if (isIP(address) === 4) {
    const [a, b, c] = address.split('.').map(Number)
    return !(a === 0 || a === 10 || a === 127 || a >= 224 || (a === 100 && b >= 64 && b <= 127)
      || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31)
      || (a === 192 && (b === 168 || (b === 0 && (c === 0 || c === 2)) || (b === 88 && c === 99)))
      || (a === 198 && (b === 18 || b === 19 || (b === 51 && c === 100))) || (a === 203 && b === 0 && c === 113))
  }
  // Only native global-unicast IPv6. Exclude documentation, deprecated 6to4
  // and Teredo; mapped IPv4, loopback, ULA and link-local are not in 2000::/3.
  if (isIP(address) !== 6) return false
  const normalized = new URL(`http://[${address}]`).hostname.slice(1, -1)
  return /^[23]/i.test(normalized) && !/^2001:db8:/i.test(normalized)
    && !/^2002:/i.test(normalized) && !/^2001:(?:0:|:)/i.test(normalized)
}
