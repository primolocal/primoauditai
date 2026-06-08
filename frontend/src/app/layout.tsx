"use client"

import { Inter } from "next/font/google"
import "./globals.css"
import { Sidebar } from "@/components/shell/sidebar"
import { Topbar } from "@/components/shell/topbar"

const inter = Inter({ subsets: ["latin"] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Sidebar />
        <div className="ml-60 min-h-screen bg-[#0d1117]">
          <Topbar title="Upload Estimate" />
          <main className="pt-12">{children}</main>
        </div>
      </body>
    </html>
  )
}
