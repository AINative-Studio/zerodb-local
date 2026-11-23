'use client'

import * as React from 'react'
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ApiRequestError } from '@/services/api-client'

/**
 * True once any request came back 401/403 -- the server is in cloud auth
 * mode and wants an API key. Drives the sign-in banner in the layout.
 */
const AuthRequiredContext = React.createContext<{ required: boolean; clear: () => void }>({
  required: false,
  clear: () => {},
})

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [required, setRequired] = React.useState(false)

  const [queryClient] = React.useState(() => {
    const onError = (error: unknown) => {
      if (error instanceof ApiRequestError && error.isAuthError) setRequired(true)
    }
    return new QueryClient({
      queryCache: new QueryCache({ onError }),
      mutationCache: new MutationCache({ onError }),
      defaultOptions: {
        queries: {
          staleTime: 60 * 1000,
          refetchOnWindowFocus: false,
          // Retrying a 401 just repeats the same refusal.
          retry: (count, error) => !(error instanceof ApiRequestError && error.isAuthError) && count < 1,
        },
      },
    })
  })

  const clear = React.useCallback(() => {
    setRequired(false)
    queryClient.invalidateQueries()
  }, [queryClient])

  return (
    <AuthRequiredContext.Provider value={{ required, clear }}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </AuthRequiredContext.Provider>
  )
}

export function useAuthRequired() {
  return React.useContext(AuthRequiredContext)
}
