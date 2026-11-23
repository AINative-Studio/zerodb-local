'use client'

import * as React from 'react'
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

/** In-page confirmation for destructive actions (no browser confirm()). */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  children,
  confirmLabel,
  onConfirm,
  pending,
  error,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  title: string
  children: React.ReactNode
  confirmLabel: string
  onConfirm: () => void
  pending?: boolean
  error?: unknown
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription asChild>
            <div>{children}</div>
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="py-3">
          {error ? (
            <p role="alert" className="text-sm font-medium text-destructive">
              {error instanceof Error ? error.message : String(error)}
            </p>
          ) : null}
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirm} disabled={pending}>
            {pending ? 'Working…' : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
