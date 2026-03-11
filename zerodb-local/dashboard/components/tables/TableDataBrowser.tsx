import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import { Table } from '@/types'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Edit,
  Trash2,
  Search,
  X,
  Database,
  Loader2,
} from 'lucide-react'

interface TableDataBrowserProps {
  projectId: string
  table: Table
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TableDataBrowser({
  projectId,
  table,
  open,
  onOpenChange,
}: TableDataBrowserProps) {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(10)

  const { data: tableData, isLoading } = useQuery({
    queryKey: ['tableData', projectId, table.name, currentPage, pageSize],
    queryFn: async () => {
      const filters = searchQuery ? { _search: searchQuery } : undefined
      return apiClient.queryTable(projectId, table.name, filters)
    },
    enabled: open,
  })

  const deleteRowMutation = useMutation({
    mutationFn: async (rowId: string) => {
      return apiClient.deleteTableRow(projectId, table.name, rowId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['tableData', projectId, table.name],
      })
      queryClient.invalidateQueries({ queryKey: ['tables', projectId] })
    },
  })

  const columns = table.schema?.fields
    ? Object.keys(table.schema.fields)
    : tableData && tableData.length > 0
    ? Object.keys(tableData[0])
    : []

  const handleSearch = (value: string) => {
    setSearchQuery(value)
    setCurrentPage(1)
  }

  const handleNextPage = () => {
    if (tableData && tableData.length === pageSize) {
      setCurrentPage((prev) => prev + 1)
    }
  }

  const handlePrevPage = () => {
    setCurrentPage((prev) => Math.max(1, prev - 1))
  }

  const formatCellValue = (value: any): string => {
    if (value === null || value === undefined) {
      return '-'
    }
    if (typeof value === 'object') {
      return JSON.stringify(value)
    }
    if (typeof value === 'boolean') {
      return value ? 'true' : 'false'
    }
    return String(value)
  }

  const getTypeColor = (value: any): string => {
    if (value === null || value === undefined) return 'text-gray-400'
    if (typeof value === 'number') return 'text-blue-600'
    if (typeof value === 'boolean') return 'text-purple-600'
    if (typeof value === 'object') return 'text-orange-600'
    return 'text-gray-900'
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            {table.name} - Data Browser
          </DialogTitle>
          <DialogDescription>
            Browse and manage table data ({table.row_count} rows total)
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Search rows..."
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                className="pl-9 pr-9"
              />
              {searchQuery && (
                <button
                  onClick={() => handleSearch('')}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            <Button size="sm" variant="outline">
              <Plus className="h-4 w-4 mr-1" />
              Insert Row
            </Button>
          </div>

          <div className="flex-1 overflow-auto border rounded-lg">
            {isLoading ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
              </div>
            ) : !tableData || tableData.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                <Database className="h-12 w-12 mb-4 text-gray-300" />
                <p className="text-lg font-medium">No data found</p>
                <p className="text-sm">
                  {searchQuery
                    ? 'Try adjusting your search query'
                    : 'This table is empty'}
                </p>
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    {columns.map((column) => (
                      <th
                        key={column}
                        className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b"
                      >
                        <div className="flex items-center gap-2">
                          {column}
                          {table.schema?.fields?.[column]?.required && (
                            <Badge variant="outline" className="text-xs">
                              Required
                            </Badge>
                          )}
                        </div>
                      </th>
                    ))}
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider border-b w-24">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tableData.map((row, rowIndex) => (
                    <tr key={rowIndex} className="hover:bg-gray-50">
                      {columns.map((column) => (
                        <td
                          key={column}
                          className={`px-4 py-3 text-sm ${getTypeColor(
                            row[column]
                          )} max-w-xs truncate`}
                          title={formatCellValue(row[column])}
                        >
                          {formatCellValue(row[column])}
                        </td>
                      ))}
                      <td className="px-4 py-3 text-right text-sm">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0"
                          >
                            <Edit className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0 text-red-600 hover:text-red-700"
                            onClick={() =>
                              row.id && deleteRowMutation.mutate(row.id)
                            }
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="flex items-center justify-between pt-2 border-t">
            <div className="text-sm text-gray-600">
              Page {currentPage}
              {tableData && tableData.length > 0 && (
                <span className="ml-2">
                  Showing {(currentPage - 1) * pageSize + 1} -{' '}
                  {(currentPage - 1) * pageSize + tableData.length}
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handlePrevPage}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleNextPage}
                disabled={!tableData || tableData.length < pageSize}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
