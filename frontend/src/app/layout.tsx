import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PRISM Analytics',
  description: 'Cross-platform RAG content intelligence — YouTube vs Instagram',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
