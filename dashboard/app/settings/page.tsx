'use client'

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import { useTheme } from '@/components/providers/theme-provider'
import { useProject } from '@/components/providers/project-provider'
import { PageHeader, PageShell } from '@/components/layout/page-header'
import { Segmented } from '@/components/ui/segmented'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Field, Select } from '@/components/ui/form-controls'
import {
  getDefaultNamespace,
  getFormMode,
  setDefaultNamespace,
  setFormMode,
  type FormMode,
} from '@/lib/preferences'
import { formatRelativeTime } from '@/lib/utils'
import { useMounted } from '@/lib/use-mounted'
import { getApiKey, setApiKey } from '@/lib/api-key'
import { useAuthRequired } from '@/components/providers/query-provider'
import type { ThemePreference } from '@/lib/theme'

export default function SettingsPage() {
  const { preference, setPreference } = useTheme()
  const mounted = useMounted()
  const health = useQuery({ queryKey: ['health'], queryFn: () => apiClient.getHealth() })

  const [formMode, setMode] = React.useState<FormMode>('guided')
  const [namespace, setNs] = React.useState('default')
  const [dashboardUrl, setDashboardUrl] = React.useState('')

  React.useEffect(() => {
    setMode(getFormMode())
    setNs(getDefaultNamespace())
    setDashboardUrl(window.location.origin)
  }, [])

  const backend = health.data?.backend
  const server = [
    { label: 'API endpoint', value: mounted ? apiClient.baseURL : '…', src: 'NEXT_PUBLIC_API_URL' },
    { label: 'Dashboard', value: dashboardUrl || '…', src: 'this page' },
    {
      label: 'Backend',
      value: health.error ? 'unreachable' : backend ? (backend === 'lite' ? 'lite (SQLite + FAISS + files)' : 'full (Docker stack)') : '…',
      src: 'GET /health',
    },
  ]

  return (
    <PageShell>
      <div className="flex w-full max-w-[880px] flex-col gap-5">
        <PageHeader title="Settings" description="Values here are read from the running dashboard and API." />

        <Section title="Appearance">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-col">
              <span className="font-semibold">Theme</span>
              <span className="text-[13px] text-muted-foreground">System follows your OS setting.</span>
            </div>
            <Segmented<ThemePreference>
              label="Theme"
              value={preference}
              onChange={setPreference}
              options={[
                { value: 'light', label: 'Light' },
                { value: 'dark', label: 'Dark' },
                { value: 'system', label: 'System' },
              ]}
            />
          </div>
        </Section>

        <Section title="Server">
          <dl className="flex flex-col">
            {server.map((r) => (
              <div key={r.label} className="flex flex-wrap items-center justify-between gap-2 border-t py-2.5 first:border-t-0">
                <dt className="font-medium">{r.label}</dt>
                <dd className="flex items-center gap-2.5">
                  <span className="font-mono text-[13px]">{r.value}</span>
                  <span className="font-mono text-[11px] text-muted-foreground">{r.src}</span>
                </dd>
              </div>
            ))}
          </dl>
        </Section>

        <Connection />

        <Section title="Defaults for new data" description="Pre-fill the create forms. You can still change them each time. Saved in this browser.">
          <div className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-3.5">
            <Field label="Open create forms in" htmlFor="pref-mode">
              <Select
                id="pref-mode"
                value={formMode}
                onChange={(e) => {
                  const m = e.target.value as FormMode
                  setMode(m)
                  setFormMode(m)
                }}
              >
                <option value="guided">Guided</option>
                <option value="advanced">Advanced JSON</option>
              </Select>
            </Field>
            <Field label="Default vector namespace" htmlFor="pref-ns">
              <Input
                id="pref-ns"
                value={namespace}
                onChange={(e) => setNs(e.target.value)}
                onBlur={() => setDefaultNamespace(namespace)}
                className="font-mono"
              />
            </Field>
          </div>
        </Section>

        <CloudSync />
      </div>
    </PageShell>
  )
}

function Connection() {
  const { required, clear } = useAuthRequired()
  const [key, setKey] = React.useState('')
  const [saved, setSaved] = React.useState(false)

  React.useEffect(() => {
    setSaved(!!getApiKey())
  }, [])

  return (
    <Section
      id="connection"
      title="Connection"
      description="Lite mode (zerodb serve) needs no sign-in. Full mode (Docker) defaults to cloud sign-in: paste your ZeroDB API key here and the dashboard sends it with every request. It stays in this browser."
    >
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-medium">API key</span>
        {saved ? <Badge variant="success">Saved in this browser</Badge> : <Badge variant="muted">None</Badge>}
        {required && <Badge variant="warning">Server is asking for one</Badge>}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (!key.trim()) return
          setApiKey(key)
          setKey('')
          setSaved(true)
          clear()
        }}
        className="flex flex-wrap items-end gap-2.5"
      >
        <Field label={saved ? 'Replace API key' : 'ZeroDB API key'} htmlFor="api-key" className="min-w-[260px] flex-1">
          <Input id="api-key" type="password" autoComplete="off" value={key} onChange={(e) => setKey(e.target.value)} className="font-mono" />
        </Field>
        <Button type="submit" variant="outline" disabled={!key.trim()}>Save key</Button>
        {saved && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setApiKey(null)
              setSaved(false)
              clear()
            }}
          >
            Remove
          </Button>
        )}
      </form>
    </Section>
  )
}

function CloudSync() {
  const { project, projectId } = useProject()
  const qc = useQueryClient()
  const [apiKey, setApiKey] = React.useState('')

  const status = useQuery({
    queryKey: ['cloud-status', projectId],
    queryFn: () => apiClient.getCloudSyncStatus(projectId!),
    enabled: !!projectId,
    retry: false,
  })

  const connect = useMutation({
    mutationFn: () => apiClient.authenticateCloud(projectId!, apiKey.trim()),
    onSuccess: () => {
      setApiKey('')
      qc.invalidateQueries({ queryKey: ['cloud-status', projectId] })
    },
  })

  const connected = status.data?.is_authenticated

  return (
    <Section
      title="Cloud sync"
      description="Push a project to ZeroDB Cloud when you're ready to share it or go to production. Nothing leaves this machine until you connect."
    >
      {!projectId ? (
        <p className="text-muted-foreground">Create a project first to connect it to the cloud.</p>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-mono">{project?.name}</span>
            {connected ? (
              <Badge variant="success">Connected</Badge>
            ) : (
              <Badge variant="muted">Not connected</Badge>
            )}
            {status.data?.last_sync_at && (
              <span className="text-muted-foreground">Last sync {formatRelativeTime(status.data.last_sync_at)}</span>
            )}
            {status.data && status.data.pending_changes > 0 && (
              <span className="text-muted-foreground">· {status.data.pending_changes} changes waiting</span>
            )}
          </div>
          {!connected && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (apiKey.trim()) connect.mutate()
              }}
              className="flex flex-wrap items-end gap-2.5"
            >
              <Field label="ZeroDB Cloud API key" htmlFor="cloud-key" className="min-w-[260px] flex-1">
                <Input id="cloud-key" type="password" autoComplete="off" value={apiKey} onChange={(e) => setApiKey(e.target.value)} className="font-mono" />
              </Field>
              <Button type="submit" variant="outline" disabled={connect.isPending || !apiKey.trim()}>
                {connect.isPending ? 'Connecting…' : 'Connect'}
              </Button>
            </form>
          )}
          {connect.error && <p role="alert" className="text-sm text-destructive">{(connect.error as Error).message}</p>}
        </div>
      )}
    </Section>
  )
}

function Section({ id: anchor, title, description, children }: { id?: string; title: string; description?: string; children: React.ReactNode }) {
  const id = `s-${title.toLowerCase().replace(/[^a-z]+/g, '-')}`
  return (
    <section id={anchor} aria-labelledby={id} className="flex flex-col gap-3.5 rounded-xl border bg-card px-6 py-5">
      <div className="flex flex-col gap-0.5">
        <h2 id={id} className="font-display text-[17px] font-semibold">{title}</h2>
        {description && <p className="text-[13px] text-muted-foreground">{description}</p>}
      </div>
      {children}
    </section>
  )
}
