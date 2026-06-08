"use client"

import { Inter } from "next/font/google"
import { usePathname } from "next/navigation"
import "./globals.css"
import { Sidebar } from "@/components/shell/sidebar"
import { Topbar } from "@/components/shell/topbar"

const inter = Inter({ subsets: ["latin"] })

function getTitle(path: string): string {
  if (path === "/") return "Upload Estimate"
  if (path === "/audits") return "Audit List"
  if (path.startsWith("/audit/")) return "Audit Detail"
  if (path === "/qc") return "Quality Control"
  if (path.startsWith("/qc/")) return "QC Detail"
  return "PrimoAuditAI"
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const title = getTitle(pathname || "")

  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Sidebar />
        <div className="ml-60 min-h-screen bg-[#0d1117]">
          <Topbar title={title} />
          <main className="pt-12">{children}</main>
        </div>
      </body>
    </html>
  )
}
