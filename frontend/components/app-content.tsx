import type { ReactNode } from 'react'

type AppContentProps = {
  children: ReactNode
}

export function AppContent({ children }: AppContentProps) {
  return <div className="app-content">{children}</div>
}
