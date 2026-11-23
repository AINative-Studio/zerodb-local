/** The files API takes and returns base64 content in JSON bodies. */

// The API has no server-side upload size limit (checked: api/routers/files.py),
// and each file is base64-encoded in full in the browser before being posted
// in one JSON body -- a large file can hang the tab during encoding or time
// out the request, with no progress to show while it does. 10MB raw (~13.3MB
// once base64-encoded) is a conservative client-side guard, not a real
// capability ceiling; raise it if the real limit turns out to be higher.
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024

export function exceedsUploadLimit(sizeBytes: number): boolean {
  return sizeBytes > MAX_UPLOAD_BYTES
}

const CHUNK = 0x8000

export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i += CHUNK) {
    binary += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + CHUNK)))
  }
  return btoa(binary)
}

export function base64ToBytes(b64: string): Uint8Array {
  const binary = atob(b64)
  const out = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i)
  return out
}

export async function fileToBase64(file: Blob): Promise<string> {
  return arrayBufferToBase64(await file.arrayBuffer())
}

/** Triggers a browser download of base64 content. */
export function saveBase64(b64: string, fileName: string, contentType: string): void {
  const blob = new Blob([base64ToBytes(b64) as BlobPart], { type: contentType || 'application/octet-stream' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

const NAMES: Record<string, string> = {
  'application/pdf': 'PDF',
  'application/json': 'JSON',
  'text/csv': 'CSV',
  'text/plain': 'Text',
  'text/markdown': 'Markdown',
  'application/zip': 'ZIP archive',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word document',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel sheet',
}

export function describeContentType(type: string): string {
  if (NAMES[type]) return NAMES[type]
  const m = /^image\/([a-z0-9+.-]+)$/i.exec(type)
  if (m) return `${m[1].toUpperCase()} image`
  return type
}
