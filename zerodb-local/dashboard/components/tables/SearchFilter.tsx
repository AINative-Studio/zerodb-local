import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Search, X, Filter, ArrowUpDown } from 'lucide-react'

export type FilterStatus = 'all' | 'has-data' | 'empty'
export type SortBy = 'name' | 'created' | 'rows' | 'updated'

interface SearchFilterProps {
  onSearchChange: (query: string) => void
  onFilterChange: (status: FilterStatus) => void
  onSortChange: (sortBy: SortBy) => void
  defaultSort?: SortBy
}

export function SearchFilter({
  onSearchChange,
  onFilterChange,
  onSortChange,
  defaultSort = 'name',
}: SearchFilterProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [activeFilter, setActiveFilter] = useState<FilterStatus>('all')
  const [sortBy, setSortBy] = useState<SortBy>(defaultSort)

  const handleSearchChange = (value: string) => {
    setSearchQuery(value)
    onSearchChange(value)
  }

  const handleFilterChange = (status: FilterStatus) => {
    setActiveFilter(status)
    onFilterChange(status)
  }

  const handleSortChange = (value: SortBy) => {
    setSortBy(value)
    onSortChange(value)
  }

  const clearFilters = () => {
    setSearchQuery('')
    setActiveFilter('all')
    setSortBy('name')
    onSearchChange('')
    onFilterChange('all')
    onSortChange('name')
  }

  const hasActiveFilters = searchQuery !== '' || activeFilter !== 'all' || sortBy !== 'name'

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            type="text"
            placeholder="Search tables..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9 pr-9"
          />
          {searchQuery && (
            <button
              onClick={() => handleSearchChange('')}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        <div className="flex gap-2">
          <Select value={sortBy} onValueChange={handleSortChange}>
            <SelectTrigger className="w-[180px]">
              <div className="flex items-center gap-2">
                <ArrowUpDown className="h-4 w-4" />
                <SelectValue placeholder="Sort by" />
              </div>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="name">Name</SelectItem>
              <SelectItem value="created">Created Date</SelectItem>
              <SelectItem value="updated">Last Updated</SelectItem>
              <SelectItem value="rows">Row Count</SelectItem>
            </SelectContent>
          </Select>

          {hasActiveFilters && (
            <Button variant="outline" size="sm" onClick={clearFilters}>
              <X className="h-4 w-4 mr-1" />
              Clear
            </Button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-gray-500" />
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={activeFilter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleFilterChange('all')}
          >
            All Tables
          </Button>
          <Button
            variant={activeFilter === 'has-data' ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleFilterChange('has-data')}
          >
            Has Data
          </Button>
          <Button
            variant={activeFilter === 'empty' ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleFilterChange('empty')}
          >
            Empty
          </Button>
        </div>
      </div>
    </div>
  )
}
