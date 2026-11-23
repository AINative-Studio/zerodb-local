'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Activity,
  FileText,
  FolderKanban,
  LayoutDashboard,
  SlidersHorizontal,
  Table2,
  Waypoints,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { BrandLockup } from './brand'
import { ModeBadge } from './mode-badge'

export const navigation = [
  { name: 'Overview', href: '/', icon: LayoutDashboard },
  { name: 'Projects', href: '/projects', icon: FolderKanban },
  { name: 'Vectors', href: '/vectors', icon: Waypoints },
  { name: 'Tables', href: '/tables', icon: Table2 },
  { name: 'Files', href: '/files', icon: FileText },
  { name: 'Events', href: '/events', icon: Zap },
  { name: 'Logs', href: '/logs', icon: Activity },
  { name: 'Settings', href: '/settings', icon: SlidersHorizontal },
] as const

export function isActive(pathname: string, href: string): boolean {
  return href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(`${href}/`)
}

export function Sidebar() {
  const pathname = usePathname()

  return (
    <nav
      aria-label="Main"
      className="flex shrink-0 flex-col gap-1 border-b bg-sidebar px-3.5 py-4 md:sticky md:top-0 md:h-screen md:w-60 md:border-b-0 md:border-r md:py-5"
    >
      <div className="px-2.5 pb-3 md:pb-5">
        <BrandLockup />
      </div>

      {/* Horizontal scroller on phones, a column from md up. */}
      <ul className="flex gap-1 overflow-x-auto md:flex-1 md:flex-col md:overflow-visible">
        {navigation.map((item) => {
          const active = isActive(pathname, item.href)
          return (
            <li key={item.href} className="shrink-0">
              <Link
                href={item.href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'flex min-h-10 items-center gap-2.5 rounded-md px-2.5 text-sm no-underline transition-colors',
                  active
                    ? 'bg-accent font-semibold text-accent-foreground'
                    : 'font-medium text-muted-foreground hover:bg-muted hover:text-foreground'
                )}
              >
                <item.icon aria-hidden="true" className="h-[18px] w-[18px]" />
                {item.name}
              </Link>
            </li>
          )
        })}
      </ul>

      <div className="hidden px-1 pt-4 md:block">
        <ModeBadge compact className="w-full justify-start" />
      </div>
    </nav>
  )
}
