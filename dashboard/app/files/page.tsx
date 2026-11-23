'use client'

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Check, Download, FileText, Loader2, Trash2, Upload } from 'lucide-react'
import { apiClient } from '@/services/api-client'
import { PageHeader, PageShell } from '@/components/layout/page-header'
import { EmptyState, ErrorState, LoadingState, RequireProject } from '@/components/layout/states'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Button } from '@/components/ui/button'
import { describeContentType, fileToBase64, saveBase64 } from '@/lib/files'
import { cn, formatBytes, formatRelativeTime } from '@/lib/utils'
import type { StoredFile } from '@/types'

interface UploadItem {
  key: string
  name: string
  size: number
  state: 'uploading' | 'done' | 'error'
  error?: string
}

export default function FilesPage() {
  return (
    <PageShell>
      <PageHeader scoped title="Files" description="Stored on this machine, alongside your project's data." />
      <RequireProject>{(projectId) => <FileManager projectId={projectId} />}</RequireProject>
    </PageShell>
  )
}

function FileManager({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const inputRef = React.useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = React.useState(false)
  const [uploads, setUploads] = React.useState<UploadItem[]>([])
  const [toDelete, setToDelete] = React.useState<StoredFile | null>(null)
  const [downloading, setDownloading] = React.useState<string | null>(null)
  const [downloadError, setDownloadError] = React.useState<string | null>(null)

  const files = useQuery({
    queryKey: ['files', projectId],
    queryFn: () => apiClient.listFiles(projectId),
  })

  const remove = useMutation({
    mutationFn: (id: string) => apiClient.deleteFile(projectId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['files', projectId] })
      qc.invalidateQueries({ queryKey: ['projects'] })
      setToDelete(null)
    },
  })

  const patch = (key: string, p: Partial<UploadItem>) =>
    setUploads((us) => us.map((u) => (u.key === key ? { ...u, ...p } : u)))

  const upload = async (list: FileList | File[]) => {
    const picked = Array.from(list)
    const items = picked.map((f, i) => ({ key: `${Date.now()}-${i}-${f.name}`, name: f.name, size: f.size, state: 'uploading' as const }))
    setUploads((us) => [...items, ...us])
    // One at a time keeps memory flat: each file is base64-encoded in full.
    for (let i = 0; i < picked.length; i++) {
      const f = picked[i]
      try {
        await apiClient.uploadFile(projectId, {
          file_name: f.name,
          file_content: await fileToBase64(f),
          content_type: f.type || 'application/octet-stream',
        })
        patch(items[i].key, { state: 'done' })
      } catch (e) {
        patch(items[i].key, { state: 'error', error: (e as Error).message })
      }
    }
    qc.invalidateQueries({ queryKey: ['files', projectId] })
    qc.invalidateQueries({ queryKey: ['projects'] })
  }

  const download = async (f: StoredFile) => {
    setDownloading(f.id)
    setDownloadError(null)
    try {
      const res = await apiClient.downloadFile(projectId, f.id)
      saveBase64(res.content, res.file_name || f.file_name, res.content_type || f.content_type)
    } catch (e) {
      setDownloadError(`${f.file_name}: ${(e as Error).message}`)
    } finally {
      setDownloading(null)
    }
  }

  const list = files.data ?? []
  const total = list.reduce((n, f) => n + (f.file_size ?? 0), 0)

  return (
    <>
      <label
        htmlFor="file-upload"
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          if (e.dataTransfer.files.length) void upload(e.dataTransfer.files)
        }}
        className={cn(
          'flex cursor-pointer flex-wrap items-center justify-center gap-4 rounded-xl border-2 border-dashed p-7 text-center transition-colors',
          dragging ? 'border-primary bg-accent' : 'border-input bg-muted/50 hover:border-primary'
        )}
      >
        <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-accent-foreground">
          <Upload aria-hidden="true" className="h-[22px] w-[22px]" />
        </span>
        <span className="flex flex-col gap-0.5 text-left">
          <strong className="text-[15px] font-semibold">
            Drop files here, or <span className="text-link">browse</span>
          </strong>
          <span className="text-[13px] text-muted-foreground">Any type. Uploads go straight to this project’s local storage.</span>
        </span>
        <input
          ref={inputRef}
          id="file-upload"
          type="file"
          multiple
          className="sr-only"
          onChange={(e) => {
            if (e.target.files?.length) void upload(e.target.files)
            e.target.value = ''
          }}
        />
      </label>

      {uploads.length > 0 && (
        <ul aria-label="Uploads" className="flex flex-col gap-2">
          {uploads.slice(0, 5).map((u) => (
            <li key={u.key} className="flex items-center gap-3 rounded-[10px] border bg-card px-4 py-3">
              {u.state === 'uploading' && <Loader2 aria-hidden="true" className="h-[18px] w-[18px] shrink-0 animate-spin text-muted-foreground" />}
              {u.state === 'done' && <Check aria-hidden="true" className="h-[18px] w-[18px] shrink-0 text-success" />}
              {u.state === 'error' && <AlertCircle aria-hidden="true" className="h-[18px] w-[18px] shrink-0 text-destructive" />}
              <span className="min-w-0 flex-1 truncate font-mono text-[13px]">{u.name}</span>
              <span className={cn('text-[13px]', u.state === 'error' ? 'text-destructive' : 'text-muted-foreground')}>
                {u.state === 'uploading' ? `Uploading · ${formatBytes(u.size, 1)}` : u.state === 'done' ? 'Uploaded' : u.error}
              </span>
            </li>
          ))}
        </ul>
      )}

      {files.isLoading && <LoadingState label="Loading files" />}
      {files.error && <ErrorState error={files.error} what="files" />}
      {files.data && list.length === 0 && uploads.length === 0 && (
        <EmptyState icon={FileText} title="No files yet">Drop a PDF, CSV, image or anything else above.</EmptyState>
      )}

      {list.length > 0 && (
        <>
          <p className="text-[13px] text-muted-foreground">
            {list.length} {list.length === 1 ? 'file' : 'files'} · <span className="font-mono text-foreground">{formatBytes(total, 1)}</span>
          </p>
          <div className="relative overflow-x-auto rounded-xl border bg-card">
            <table className="w-full min-w-[700px] border-collapse text-left">
              <thead>
                <tr className="bg-muted text-xs text-muted-foreground">
                  <th scope="col" className="px-4 py-3 font-semibold">Name</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Type</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Size</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Uploaded</th>
                  <th scope="col" className="px-4 py-3"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {list.map((f) => (
                  <tr key={f.id} className="border-t">
                    <td className="px-4 py-3 font-mono text-[13px]">
                      {f.folder && <span className="text-muted-foreground">{f.folder}/</span>}
                      {f.file_name}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{describeContentType(f.content_type)}</td>
                    <td className="px-4 py-3 font-mono text-[13px]">{formatBytes(f.file_size, 1)}</td>
                    <td className="px-4 py-3 text-muted-foreground">{f.created_at ? formatRelativeTime(f.created_at) : '–'}</td>
                    <td className="whitespace-nowrap px-3 py-1.5 text-right">
                      <Button variant="ghost" size="icon-sm" aria-label={`Download ${f.file_name}`} onClick={() => download(f)} disabled={downloading === f.id}>
                        {downloading === f.id ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : <Download aria-hidden="true" className="h-4 w-4" />}
                      </Button>
                      <Button variant="ghost" size="icon-sm" aria-label={`Delete ${f.file_name}`} onClick={() => setToDelete(f)}>
                        <Trash2 aria-hidden="true" className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {downloadError && <p role="alert" className="text-sm text-destructive">Couldn’t download {downloadError}</p>}

      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        title={`Delete ${toDelete?.file_name ?? 'file'}?`}
        confirmLabel="Delete file"
        onConfirm={() => toDelete && remove.mutate(toDelete.id)}
        pending={remove.isPending}
        error={remove.error}
      >
        The file is removed from local storage. This can’t be undone.
      </ConfirmDialog>
    </>
  )
}
