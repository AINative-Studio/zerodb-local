import type { Metadata } from 'next'
import '@fontsource-variable/inter'
import '@fontsource-variable/space-grotesk'
import '@fontsource-variable/jetbrains-mono'
import './globals.css'
import { QueryProvider } from '@/components/providers/query-provider'
import { ThemeProvider } from '@/components/providers/theme-provider'
import { ProjectProvider } from '@/components/providers/project-provider'
import { Sidebar } from '@/components/layout/sidebar'
import { AuthNotice } from '@/components/layout/auth-notice'
import { themeInitScript } from '@/lib/theme'

export const metadata: Metadata = {
  title: 'ZeroDB Local',
  description: 'Your local ZeroDB: vectors, tables, files and events on this machine.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Sets the theme class before first paint (no light flash in dark mode). */}
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-screen">
        <ThemeProvider>
          <QueryProvider>
            <ProjectProvider>
              <div className="flex min-h-screen flex-col md:flex-row">
                <Sidebar />
                <main className="min-w-0 flex-1">
                  <AuthNotice />
                  {children}
                </main>
              </div>
            </ProjectProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
