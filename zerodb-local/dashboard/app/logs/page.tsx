'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import {
  Activity,
  Search,
  Filter,
  Download,
  RefreshCw,
  AlertCircle,
  Info,
  AlertTriangle,
  XCircle,
  Bug,
  Database,
  Server,
  HardDrive,
  Cpu,
  Code,
  Layout,
} from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { formatRelativeTime } from '@/lib/utils'
import type { LogEntry } from '@/types'

// Service icons mapping
const SERVICE_ICONS = {
  postgres: Database,
  qdrant: Server,
  minio: HardDrive,
  redpanda: Cpu,
  embeddings: Code,
  api: Server,
  dashboard: Layout,
}

// Log level colors
const LOG_LEVEL_COLORS = {
  DEBUG: 'bg-gray-100 text-gray-700 border-gray-300',
  INFO: 'bg-blue-100 text-blue-700 border-blue-300',
  WARNING: 'bg-yellow-100 text-yellow-700 border-yellow-300',
  ERROR: 'bg-red-100 text-red-700 border-red-300',
  CRITICAL: 'bg-red-200 text-red-900 border-red-400 font-bold',
}

// Log level icons
const LOG_LEVEL_ICONS = {
  DEBUG: Bug,
  INFO: Info,
  WARNING: AlertTriangle,
  ERROR: XCircle,
  CRITICAL: AlertCircle,
}

export default function LogsPage(): JSX.Element {
  // State
  const [selectedService, setSelectedService] = useState<string>('')
  const [selectedLevel, setSelectedLevel] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [autoScroll, setAutoScroll] = useState(true)
  const [sinceMinutes, setSinceMinutes] = useState(60)
  const [limit, setLimit] = useState(100)
  const logsEndRef = useRef<HTMLDivElement>(null)

  // Fetch available services
  const { data: services } = useQuery({
    queryKey: ['log-services'],
    queryFn: () => apiClient.getAvailableServices(),
  })

  // Fetch available log levels
  const { data: levels } = useQuery({
    queryKey: ['log-levels'],
    queryFn: () => apiClient.getLogLevels(),
  })

  // Fetch logs with auto-refresh
  const {
    data: logsData,
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['logs', selectedService, selectedLevel, limit, sinceMinutes],
    queryFn: () =>
      apiClient.getLogs(
        selectedService || undefined,
        selectedLevel || undefined,
        limit,
        sinceMinutes
      ),
    refetchInterval: autoScroll ? 5000 : false, // Auto-refresh every 5 seconds if enabled
  })

  // Filter logs by search query
  const filteredLogs = logsData?.logs.filter((log) =>
    log.message.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [filteredLogs, autoScroll])

  // Calculate log level counts
  const logLevelCounts = logsData?.logs.reduce(
    (acc, log) => {
      acc[log.level] = (acc[log.level] || 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  // Calculate service counts
  const serviceCounts = logsData?.logs.reduce(
    (acc, log) => {
      acc[log.service] = (acc[log.service] || 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  // Export logs as JSON
  const handleExportLogs = () => {
    if (!logsData) return

    const dataStr = JSON.stringify(logsData.logs, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `zerodb-logs-${new Date().toISOString()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  // Format log entry for display
  const formatLogEntry = (log: LogEntry) => {
    const ServiceIcon = SERVICE_ICONS[log.service] || Server
    const LevelIcon = LOG_LEVEL_ICONS[log.level] || Info
    const levelColor = LOG_LEVEL_COLORS[log.level] || LOG_LEVEL_COLORS.INFO

    return (
      <div
        key={`${log.timestamp}-${log.service}-${log.message.substring(0, 20)}`}
        className="border-b border-gray-200 py-3 px-4 hover:bg-gray-50 transition-colors font-mono text-sm"
      >
        <div className="flex items-start gap-3">
          {/* Timestamp */}
          <div className="text-gray-500 text-xs whitespace-nowrap min-w-[140px] mt-0.5">
            {new Date(log.timestamp).toLocaleTimeString('en-US', {
              hour12: false,
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })}
          </div>

          {/* Service Badge */}
          <div className="flex items-center gap-1 min-w-[100px]">
            <ServiceIcon className="h-3 w-3 text-gray-600" />
            <Badge variant="outline" className="text-xs">
              {log.service}
            </Badge>
          </div>

          {/* Level Badge */}
          <div className="flex items-center gap-1 min-w-[90px]">
            <LevelIcon className="h-3 w-3" />
            <Badge className={`text-xs ${levelColor}`}>{log.level}</Badge>
          </div>

          {/* Message */}
          <div className="flex-1 text-gray-800 break-words">{log.message}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2 flex items-center gap-2">
          <Activity className="h-8 w-8" />
          System Logs
        </h1>
        <p className="text-gray-600">
          Real-time log streaming from all ZeroDB services
        </p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-6">
        {/* Total Logs */}
        <Card>
          <CardHeader className="pb-3">
            <CardDescription className="flex items-center gap-1">
              <Activity className="h-3 w-3" />
              Total
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{logsData?.total_count || 0}</div>
            <p className="text-xs text-gray-500 mt-1">Log entries</p>
          </CardContent>
        </Card>

        {/* Log Level Counts */}
        {levels?.map((level) => {
          const LevelIcon = LOG_LEVEL_ICONS[level as keyof typeof LOG_LEVEL_ICONS] || Info
          const count = logLevelCounts?.[level] || 0
          const colorClass = LOG_LEVEL_COLORS[level as keyof typeof LOG_LEVEL_COLORS]

          return (
            <Card key={level} className={count > 0 ? 'border-2' : ''}>
              <CardHeader className="pb-3">
                <CardDescription className="flex items-center gap-1">
                  <LevelIcon className="h-3 w-3" />
                  {level}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${count > 0 ? 'text-gray-900' : 'text-gray-400'}`}>
                  {count}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {count === 0 ? 'None' : 'entries'}
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters & Controls
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Service Filter */}
            <div>
              <Label htmlFor="service-filter" className="text-sm font-medium mb-2 block">
                Service
              </Label>
              <select
                id="service-filter"
                className="w-full px-3 py-2 border rounded-md text-sm"
                value={selectedService}
                onChange={(e) => setSelectedService(e.target.value)}
              >
                <option value="">All Services</option>
                {services?.map((service) => {
                  const count = serviceCounts?.[service] || 0
                  return (
                    <option key={service} value={service}>
                      {service} ({count})
                    </option>
                  )
                })}
              </select>
            </div>

            {/* Level Filter */}
            <div>
              <Label htmlFor="level-filter" className="text-sm font-medium mb-2 block">
                Log Level
              </Label>
              <select
                id="level-filter"
                className="w-full px-3 py-2 border rounded-md text-sm"
                value={selectedLevel}
                onChange={(e) => setSelectedLevel(e.target.value)}
              >
                <option value="">All Levels</option>
                {levels?.map((level) => {
                  const count = logLevelCounts?.[level] || 0
                  return (
                    <option key={level} value={level}>
                      {level} ({count})
                    </option>
                  )
                })}
              </select>
            </div>

            {/* Time Range */}
            <div>
              <Label htmlFor="time-range" className="text-sm font-medium mb-2 block">
                Time Range
              </Label>
              <select
                id="time-range"
                className="w-full px-3 py-2 border rounded-md text-sm"
                value={sinceMinutes}
                onChange={(e) => setSinceMinutes(Number(e.target.value))}
              >
                <option value={5}>Last 5 minutes</option>
                <option value={15}>Last 15 minutes</option>
                <option value={30}>Last 30 minutes</option>
                <option value={60}>Last hour</option>
                <option value={360}>Last 6 hours</option>
                <option value={1440}>Last 24 hours</option>
              </select>
            </div>

            {/* Limit */}
            <div>
              <Label htmlFor="limit" className="text-sm font-medium mb-2 block">
                Max Entries
              </Label>
              <select
                id="limit"
                className="w-full px-3 py-2 border rounded-md text-sm"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
              >
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={250}>250</option>
                <option value={500}>500</option>
                <option value={1000}>1000</option>
              </select>
            </div>
          </div>

          {/* Search and Actions Row */}
          <div className="mt-4 flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search log messages..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Auto-scroll Toggle */}
            <div className="flex items-center gap-2 border rounded-lg px-4 py-2 bg-gray-50">
              <Switch
                id="auto-scroll"
                checked={autoScroll}
                onCheckedChange={setAutoScroll}
              />
              <Label htmlFor="auto-scroll" className="cursor-pointer text-sm">
                Auto-scroll
              </Label>
            </div>

            {/* Refresh Button */}
            <Button
              variant="outline"
              onClick={() => refetch()}
              disabled={isFetching}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
              Refresh
            </Button>

            {/* Export Button */}
            <Button variant="outline" onClick={handleExportLogs}>
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Logs Display */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">
              Log Stream
              {searchQuery && (
                <span className="text-sm text-gray-500 ml-2">
                  ({filteredLogs?.length || 0} of {logsData?.logs.length || 0} shown)
                </span>
              )}
            </CardTitle>
            {autoScroll && (
              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                <Activity className="h-3 w-3 mr-1 animate-pulse" />
                Live
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="max-h-[600px] overflow-y-auto bg-gray-50">
            {isLoading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
              </div>
            ) : filteredLogs && filteredLogs.length > 0 ? (
              <div>
                {filteredLogs.map((log) => formatLogEntry(log))}
                <div ref={logsEndRef} />
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                <Activity className="h-12 w-12 mb-4 opacity-50" />
                <p className="text-sm">
                  {searchQuery
                    ? 'No logs match your search criteria'
                    : 'No logs available for the selected filters'}
                </p>
                <p className="text-xs mt-2">
                  Try adjusting your filters or time range
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Footer Info */}
      <div className="mt-4 text-xs text-gray-500 text-center">
        Showing logs from {new Date(logsData?.time_range_start || '').toLocaleString()} to{' '}
        {new Date(logsData?.time_range_end || '').toLocaleString()}
        {autoScroll && ' • Auto-refreshing every 5 seconds'}
      </div>
    </div>
  )
}
