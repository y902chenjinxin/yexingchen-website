/**
 * Token管理工具 - 解析JWT payload检查过期时间
 */

// 解码JWT（不验证签名，仅解析payload）
export function parseJwtPayload(token) {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch {
    return null
  }
}

// 检查Token是否即将过期（返回距过期的秒数，<0表示已过期）
export function getTokenExpiresIn(token) {
  const payload = parseJwtPayload(token)
  if (!payload || !payload.exp) return -1
  const now = Math.floor(Date.now() / 1000)
  return payload.exp - now
}

// Token是否有效（未过期）
export function isTokenValid(token) {
  return getTokenExpiresIn(token) > 0
}