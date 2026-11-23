import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * Native <select> and <textarea> styled to match Input. Native controls keep
 * keyboard, screen-reader and mobile behaviour for free, which matters more
 * here than a custom listbox.
 */

const fieldBase =
  'w-full rounded-lg border border-input bg-card text-sm text-foreground ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-destructive'

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => <select ref={ref} className={cn(fieldBase, 'h-11 px-3', className)} {...props} />
)
Select.displayName = 'Select'

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Dark monospace editor surface for JSON. */
  code?: boolean
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({ className, code, ...props }, ref) => (
  <textarea
    ref={ref}
    spellCheck={code ? false : props.spellCheck}
    className={cn(
      fieldBase,
      'min-h-[88px] resize-y px-3 py-2.5',
      code && 'border-terminal bg-terminal font-mono text-[12.5px] leading-relaxed text-terminal-foreground',
      className
    )}
    {...props}
  />
))
Textarea.displayName = 'Textarea'

/** Label + control + hint/error, wired up with ids for accessibility. */
export function Field({
  label,
  htmlFor,
  required,
  optional,
  hint,
  error,
  children,
  className,
}: {
  label: React.ReactNode
  htmlFor: string
  required?: boolean
  optional?: boolean
  hint?: React.ReactNode
  error?: string | null
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label htmlFor={htmlFor} className="text-sm font-semibold">
        {label}
        {required && <span className="text-destructive"> *</span>}
        {optional && <span className="font-normal text-muted-foreground"> (optional)</span>}
      </label>
      {children}
      {error ? (
        <p id={`${htmlFor}-error`} role="alert" className="text-xs font-medium text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p id={`${htmlFor}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  )
}
