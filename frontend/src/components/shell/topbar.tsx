"use client"

import * as React from "react"
import { Activity, Clock } from "lucide-react"

export function Topbar({ title }: { title: string }) {
  const [time, setTime] = React.useState("")

  React.useEffect(() => {
    const tick = () => {
      setTime(new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }))
    }
    tick()
    const id = setInterval(tick, 60000)
    return () => clearInterval(id)
  }, [])

  return (
    <header className="fixed left-0 right-0 top-0 z-30 flex h-12 items-center justify-between border-b border-[#21262d] bg-[#0d1117]/95 px-4 pl-64 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-[#c9d1d9]">{title}</h1>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Activity className="h-3.5 w-3.5 text-green-500" />
          <span className="text-xs text-[#8b949e]">Backend Online</span>
        </div>
        <div className="flex items-center gap-1.5 text-[#8b949e]">
          <Clock className="h-3.5 w-3.5" />
          <span className="text-xs font-mono">{time}</span>
        </div>
      </div>
    </header>
  )
}
