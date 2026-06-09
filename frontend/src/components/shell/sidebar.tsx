"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Upload,
  List,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
  ClipboardCheck,
} from "lucide-react"
import { cn } from "../../lib/utils"

const navItems = [
  { href: "/", label: "Upload", icon: Upload },
  { href: "/audits", label: "Audits", icon: List },
  { href: "/qc", label: "QC", icon: ClipboardCheck },
  { href: "/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = React.useState(false)
  const pathname = usePathname()
  const isActive = (href: string) => pathname === href || (href !== "/" && pathname.startsWith(href))

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-[#21262d] bg-[#161b22] transition-all duration-300",
        collapsed ? "w-14" : "w-60"
      )}
    >
      {/* Header */}
      <div className="flex h-12 items-center justify-between border-b border-[#21262d] px-3">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-[#f0883e]" />
            <span className="text-sm font-semibold text-[#c9d1d9]">PrimoAudit</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex h-7 w-7 items-center justify-center rounded-md text-[#8b949e] hover:bg-[#21262d] hover:text-[#c9d1d9]"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-[#f0883e]/10 text-[#f0883e]"
                  : "text-[#8b949e] hover:bg-[#21262d] hover:text-[#c9d1d9]"
              )}
            >
              <Icon className={cn("h-4 w-4 shrink-0", active && "text-[#f0883e]")} />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      {!collapsed && (
        <div className="border-t border-[#21262d] p-3">
          <p className="text-xs text-[#484f58]">v2.0.0 — PrimoAuditAI</p>
        </div>
      )}
    </aside>
  )
}
