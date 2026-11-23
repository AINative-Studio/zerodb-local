/**
 * Optional API key for servers that require sign-in (full/Docker mode
 * defaults to ZERODB_AUTH_MODE=cloud). Lite mode never needs one.
 * Kept in this browser only and sent as a Bearer token to the local API.
 */

const KEY = 'zerolocal-api-key'

export function getApiKey(): string | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage.getItem(KEY) || null
  } catch {
    return null
  }
}

export function setApiKey(key: string | null): void {
  try {
    if (key && key.trim()) window.localStorage.setItem(KEY, key.trim())
    else window.localStorage.removeItem(KEY)
  } catch {
    // storage blocked: the key can't be remembered in this browser
  }
}
