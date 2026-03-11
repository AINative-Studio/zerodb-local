import { useState } from 'react'
import { Table } from '@/types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Table as TableIcon,
  FileJson,
  MoreVertical,
  Edit,
  Trash2,
  Download,
  Eye,
  Clock,
  Database,
} from 'lucide-react'
import { formatRelativeTime, formatNumber, formatBytes } from '@/lib/utils'

interface EnhancedTableCardProps {
  table: Table
  onViewData?: (table: Table) => void
  onEdit?: (table: Table) => void
  onDelete?: (table: Table) => void
  onExport?: (table: Table) => void
}

export function EnhancedTableCard({
  table,
  onViewData,
  onEdit,
  onDelete,
  onExport,
}: EnhancedTableCardProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  const getFieldCount = () => {
    if (!table.schema || !table.schema.fields) return 0
    return Object.keys(table.schema.fields).length
  }

  const getStatusBadge = () => {
    const rowCount = table.row_count ?? 0
    if (rowCount === 0) {
      return <Badge variant="outline" className="text-gray-500">Empty</Badge>
    } else if (rowCount < 100) {
      return <Badge variant="outline" className="text-blue-600 border-blue-300">Small</Badge>
    } else if (rowCount < 10000) {
      return <Badge variant="outline" className="text-green-600 border-green-300">Active</Badge>
    } else {
      return <Badge variant="outline" className="text-purple-600 border-purple-300">Large</Badge>
    }
  }

  const getStorageSize = () => {
    if (table.schema?.storage_bytes) {
      return formatBytes(table.schema.storage_bytes)
    }
    const estimatedSize = (table.row_count ?? 0) * 1024
    return formatBytes(estimatedSize)
  }

  return (
    <Card className="hover:shadow-lg transition-shadow group">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <CardTitle className="text-xl">{table.name}</CardTitle>
              {getStatusBadge()}
            </div>
            <CardDescription>NoSQL collection</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <TableIcon className="h-5 w-5 text-gray-400" />
            <DropdownMenu open={isMenuOpen} onOpenChange={setIsMenuOpen}>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onViewData?.(table)}>
                  <Eye className="h-4 w-4 mr-2" />
                  View Data
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onEdit?.(table)}>
                  <Edit className="h-4 w-4 mr-2" />
                  Edit Schema
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => onExport?.(table)}>
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => onDelete?.(table)}
                  className="text-red-600 focus:text-red-600"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 flex items-center gap-1">
                <Database className="h-3 w-3" />
                Rows
              </span>
              <span className="font-medium">{formatNumber(table.row_count ?? 0)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 flex items-center gap-1">
                <FileJson className="h-3 w-3" />
                Fields
              </span>
              <span className="font-medium">{getFieldCount()} fields</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Size</span>
              <span className="font-medium">{getStorageSize()}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Modified
              </span>
              <span className="font-medium">{formatRelativeTime(table.updated_at)}</span>
            </div>
          </div>

          {table.schema?.fields && (
            <div className="pt-3 border-t">
              <p className="text-xs text-gray-500 mb-2">Schema Preview</p>
              <div className="flex flex-wrap gap-1">
                {Object.keys(table.schema.fields).slice(0, 3).map((fieldName) => (
                  <Badge key={fieldName} variant="outline" className="text-xs">
                    {fieldName}
                  </Badge>
                ))}
                {Object.keys(table.schema.fields).length > 3 && (
                  <Badge variant="outline" className="text-xs text-gray-500">
                    +{Object.keys(table.schema.fields).length - 3} more
                  </Badge>
                )}
              </div>
            </div>
          )}

          <Button
            variant="outline"
            className="w-full mt-2"
            size="sm"
            onClick={() => onViewData?.(table)}
          >
            <Eye className="h-3 w-3 mr-2" />
            Browse Data
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
