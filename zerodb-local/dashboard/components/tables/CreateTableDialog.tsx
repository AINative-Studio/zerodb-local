import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Plus, Trash2, Type, Hash, ToggleLeft, FileJson, List } from 'lucide-react'

interface Field {
  id: string
  name: string
  type: 'string' | 'number' | 'boolean' | 'object' | 'array'
  required: boolean
}

interface CreateTableDialogProps {
  projectId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

const FIELD_TYPES = [
  { value: 'string', label: 'String', icon: Type },
  { value: 'number', label: 'Number', icon: Hash },
  { value: 'boolean', label: 'Boolean', icon: ToggleLeft },
  { value: 'object', label: 'Object', icon: FileJson },
  { value: 'array', label: 'Array', icon: List },
] as const

export function CreateTableDialog({ projectId, open, onOpenChange }: CreateTableDialogProps) {
  const queryClient = useQueryClient()
  const [tableName, setTableName] = useState('')
  const [description, setDescription] = useState('')
  const [fields, setFields] = useState<Field[]>([
    { id: '1', name: 'id', type: 'string', required: true },
  ])
  const [errors, setErrors] = useState<Record<string, string>>({})

  const createTableMutation = useMutation({
    mutationFn: async (data: { name: string; description?: string; schema: any }) => {
      return apiClient.createTable(projectId, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tables', projectId] })
      resetForm()
      onOpenChange(false)
    },
  })

  const resetForm = () => {
    setTableName('')
    setDescription('')
    setFields([{ id: '1', name: 'id', type: 'string', required: true }])
    setErrors({})
  }

  const addField = () => {
    const newField: Field = {
      id: Date.now().toString(),
      name: '',
      type: 'string',
      required: false,
    }
    setFields([...fields, newField])
  }

  const removeField = (id: string) => {
    if (fields.length > 1) {
      setFields(fields.filter((field) => field.id !== id))
    }
  }

  const updateField = (id: string, updates: Partial<Field>) => {
    setFields(
      fields.map((field) => (field.id === id ? { ...field, ...updates } : field))
    )
  }

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!tableName.trim()) {
      newErrors.tableName = 'Table name is required'
    } else if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(tableName)) {
      newErrors.tableName = 'Table name must start with a letter and contain only letters, numbers, and underscores'
    }

    const fieldNames = new Set<string>()
    fields.forEach((field, index) => {
      if (!field.name.trim()) {
        newErrors[`field_${field.id}`] = 'Field name is required'
      } else if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(field.name)) {
        newErrors[`field_${field.id}`] = 'Field name must start with a letter'
      } else if (fieldNames.has(field.name)) {
        newErrors[`field_${field.id}`] = 'Duplicate field name'
      }
      fieldNames.add(field.name)
    })

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    const schema = {
      fields: fields.reduce((acc, field) => {
        acc[field.name] = {
          type: field.type,
          required: field.required,
        }
        return acc
      }, {} as Record<string, any>),
    }

    createTableMutation.mutate({
      name: tableName,
      description: description || undefined,
      schema,
    })
  }

  const getFieldIcon = (type: string) => {
    const fieldType = FIELD_TYPES.find((ft) => ft.value === type)
    return fieldType ? fieldType.icon : Type
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Table</DialogTitle>
          <DialogDescription>
            Define a new NoSQL table with custom schema fields
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <div>
              <Label htmlFor="tableName">Table Name</Label>
              <Input
                id="tableName"
                value={tableName}
                onChange={(e) => setTableName(e.target.value)}
                placeholder="users"
                className={errors.tableName ? 'border-red-500' : ''}
              />
              {errors.tableName && (
                <p className="text-sm text-red-500 mt-1">{errors.tableName}</p>
              )}
            </div>

            <div>
              <Label htmlFor="description">Description (Optional)</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this table stores..."
                rows={2}
              />
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Schema Fields</Label>
              <Button type="button" variant="outline" size="sm" onClick={addField}>
                <Plus className="h-4 w-4 mr-1" />
                Add Field
              </Button>
            </div>

            <div className="space-y-3 max-h-[300px] overflow-y-auto border rounded-lg p-4">
              {fields.map((field, index) => {
                const FieldIcon = getFieldIcon(field.type)
                return (
                  <div key={field.id} className="flex items-start gap-2">
                    <div className="flex-1 grid grid-cols-12 gap-2 items-start">
                      <div className="col-span-5">
                        <Input
                          value={field.name}
                          onChange={(e) =>
                            updateField(field.id, { name: e.target.value })
                          }
                          placeholder="field_name"
                          className={
                            errors[`field_${field.id}`] ? 'border-red-500' : ''
                          }
                        />
                        {errors[`field_${field.id}`] && (
                          <p className="text-xs text-red-500 mt-1">
                            {errors[`field_${field.id}`]}
                          </p>
                        )}
                      </div>

                      <div className="col-span-4">
                        <Select
                          value={field.type}
                          onValueChange={(value: any) =>
                            updateField(field.id, { type: value })
                          }
                        >
                          <SelectTrigger>
                            <div className="flex items-center gap-2">
                              <FieldIcon className="h-4 w-4" />
                              <SelectValue />
                            </div>
                          </SelectTrigger>
                          <SelectContent>
                            {FIELD_TYPES.map((type) => {
                              const Icon = type.icon
                              return (
                                <SelectItem key={type.value} value={type.value}>
                                  <div className="flex items-center gap-2">
                                    <Icon className="h-4 w-4" />
                                    {type.label}
                                  </div>
                                </SelectItem>
                              )
                            })}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="col-span-2 flex items-center">
                        <label className="flex items-center gap-1 cursor-pointer text-sm">
                          <input
                            type="checkbox"
                            checked={field.required}
                            onChange={(e) =>
                              updateField(field.id, { required: e.target.checked })
                            }
                            className="rounded border-gray-300"
                          />
                          Required
                        </label>
                      </div>

                      <div className="col-span-1 flex justify-end">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeField(field.id)}
                          disabled={fields.length === 1}
                          className="h-8 w-8 p-0"
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createTableMutation.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createTableMutation.isPending}>
              {createTableMutation.isPending ? 'Creating...' : 'Create Table'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
