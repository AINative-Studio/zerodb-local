/**
 * Per-browser conveniences set on the Settings page. Never load-bearing:
 * every read falls back to a default when storage is empty or blocked.
 */

export type FormMode = 'guided' | 'advanced'

const KEYS = {
  formMode: 'zerolocal-form-mode',
  namespace: 'zerolocal-default-namespace',
} as const

function read(key: string): string | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // storage blocked: the setting applies until reload
  }
}

export function getFormMode(): FormMode {
  return read(KEYS.formMode) === 'advanced' ? 'advanced' : 'guided'
}

export function setFormMode(mode: FormMode) {
  write(KEYS.formMode, mode)
}

export function getDefaultNamespace(): string {
  return read(KEYS.namespace)?.trim() || 'default'
}

export function setDefaultNamespace(ns: string) {
  write(KEYS.namespace, ns.trim() || 'default')
}
