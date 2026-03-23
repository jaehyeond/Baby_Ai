'use client'

import { SSEProvider } from '@/hooks/SSEContext'
import type { ReactNode } from 'react'

export function Providers({ children }: { children: ReactNode }) {
  return <SSEProvider>{children}</SSEProvider>
}
